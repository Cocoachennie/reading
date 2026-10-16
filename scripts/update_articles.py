"""Fetch permitted RSS metadata into a public catalog; never publish local user data."""
import argparse
import copy
import json
import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.licensed_sources import permitted_body, collect, BOOKS, source_name
from server import SOURCES, TOPICS, EXAMS, decorate, demos, fetch, now, valid_url

CATALOG = ROOT / 'static' / 'data' / 'articles.json'
WORKFLOW_URL = 'https://github.com/Cocoachennie/reading/actions/workflows/pages.yml'
ALLOWED_SOURCES = {source['name'] for source in SOURCES} | {source_name(b) for b in BOOKS}
PUBLIC_FIELDS = ('id', 'title', 'summary_en', 'summary_zh', 'source', 'url',
                 'published_at', 'collected_at', 'demo', 'rights', 'license', 'content_scope')


def public_article(article):
    """An allowlist prevents authorized/private full text from reaching Pages."""
    if not isinstance(article, dict):
        raise ValueError('文章必须是对象')
    if not all(isinstance(article.get(k), str) for k in ('id', 'title', 'source', 'summary_zh')):
        raise ValueError('文章缺少必要元数据')
    if not article.get('demo'):
        if article['source'] not in ALLOWED_SOURCES or not valid_url(article.get('url', '')):
            raise ValueError('公共文章必须来自配置的 RSS 来源并具有有效原文链接')
        if article['id'] != article['url']:
            raise ValueError('公共文章 ID 必须等于原文链接')
    safe = {key: article.get(key) for key in PUBLIC_FIELDS}
    safe['summary_en'] = safe.get('summary_en') or ''
    safe['body'] = article.get('body','') if permitted_body(article) else ''
    return decorate(safe)


def validate_catalog(catalog):
    if not isinstance(catalog, dict) or catalog.get('schema_version') != 1:
        raise ValueError('不支持的数据版本；保留原文件，不覆盖')
    if not isinstance(catalog.get('articles'), list) or not isinstance(catalog.get('statuses'), dict):
        raise ValueError('文章或来源状态格式错误')
    ids = set()
    for article in catalog['articles']:
        public_article(article)
        if article.get('body') and not permitted_body(article):
            raise ValueError('公开 JSON 不允许包含未经许可验证的正文')
        if article['id'] in ids:
            raise ValueError('文章 ID 重复')
        ids.add(article['id'])
    if catalog.get('topic_rules') != TOPICS or catalog.get('exam_rules') != EXAMS:
        raise ValueError('主题规则与当前代码不一致')
    return catalog


def initial_catalog():
    return {
        'schema_version': 1,
        'articles': [public_article(a) for a in demos()],
        'statuses': {s['id']: {'name': s['name'], 'state': '未获取', 'last_success': None} for s in SOURCES},
        'last_success': None,
        'generated_at': None,
        'topic_rules': TOPICS,
        'exam_rules': EXAMS,
        'sources': SOURCES,
        'scheduler': {
            'configured': True, 'cron': '23 0,12 * * *', 'timezone': 'UTC',
            'last_scheduled_run': None, 'workflow_url': WORKFLOW_URL,
        },
    }


def update_catalog(previous, fetcher=fetch, event='local'):
    state = copy.deepcopy(previous)
    # Rebuild metadata, including classification, when taxonomy changes.
    state['articles'] = [public_article(a) for a in state['articles']]
    state['topic_rules'], state['exam_rules'], state['sources'] = TOPICS, EXAMS, SOURCES
    succeeded = False
    for source in SOURCES:
        old = state['statuses'].get(source['id'], {})
        checked = now()
        try:
            incoming = [public_article(a) for a in fetcher(source)]
            if not incoming:
                raise ValueError('RSS 没有有效文章')
            articles = {a['id']: a for a in state['articles']}
            for article in incoming:
                existing = articles.get(article['id'])
                if existing:
                    article['collected_at'] = existing.get('collected_at') or article['collected_at']
                articles[article['id']] = article
            state['articles'] = list(articles.values())
            state['statuses'][source['id']] = {
                'name': source['name'], 'state': '成功', 'count': len(incoming),
                'last_success': now(), 'checked_at': checked,
            }
            succeeded = True
        except Exception as exc:
            state['statuses'][source['id']] = {
                **old, 'name': source['name'], 'state': '失败',
                'error': str(exc)[:240], 'checked_at': checked,
            }
    if succeeded:
        state['last_success'] = now()
        # Bounded public archive. Failed-only updates never prune existing data.
        licensed = [a for a in state['articles'] if permitted_body(a)]
        metadata = [a for a in state['articles'] if not permitted_body(a)]
        state['articles'] = licensed + sorted(metadata, key=lambda a: a.get('collected_at') or '')[-max(1,500-len(licensed)):]
    state['generated_at'] = now()
    scheduler = state.setdefault('scheduler', {})
    scheduler.update(configured=True, cron='23 0,12 * * *', timezone='UTC', workflow_url=WORKFLOW_URL)
    if event == 'schedule':
        scheduler['last_scheduled_run'] = now()
    state['collection_event'] = event
    return validate_catalog(state)


def write_catalog(path, catalog):
    validate_catalog(catalog)
    result = subprocess.run(['node', str(ROOT / 'scripts/analyze_catalog.cjs')], input=json.dumps(catalog,ensure_ascii=False),capture_output=True,text=True,check=True)
    catalog=json.loads(result.stdout)
    validate_catalog(catalog)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline', action='store_true', help='仅验证/刷新规则，不访问 RSS 或伪造获取状态')
    args = parser.parse_args()
    previous = json.loads(CATALOG.read_text(encoding='utf-8')) if CATALOG.exists() else initial_catalog()
    if args.offline:
        previous['articles'] = [public_article(a) for a in previous['articles']]
        previous.update(topic_rules=TOPICS, exam_rules=EXAMS, sources=SOURCES)
        state = validate_catalog(previous)
    else:
        state = collect(update_catalog(previous, event=os.environ.get('GITHUB_EVENT_NAME', 'local')))
    state['articles']=[a for a in state['articles'] if not a.get('demo')]
    state['platform_version']='2.0'
    write_catalog(CATALOG, state)
    for status in state['statuses'].values():
        print(f"{status['name']}: {status['state']}" + (f" — {status['error']}" if status.get('error') else ''))
    print(f"Public catalog: {len(state['articles'])} articles; last success: {state['last_success']}")


if __name__ == '__main__':
    main()
