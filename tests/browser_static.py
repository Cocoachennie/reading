"""Optional Playwright smoke test, using only a static HTTP server at /reading/."""
import functools
import json
import shutil
import sys
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_site import build
from playwright.sync_api import sync_playwright, expect


def main():
    with tempfile.TemporaryDirectory(prefix='leaf-pages-') as temp:
        directory = Path(temp)
        build(directory / 'reading')
        handler = functools.partial(SimpleHTTPRequestHandler, directory=str(directory))
        http = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        worker = threading.Thread(target=http.serve_forever, daemon=True)
        worker.start()
        base = f'http://127.0.0.1:{http.server_port}/reading/'
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path=shutil.which('chromium') or None, headless=True, args=['--no-sandbox'])
                context = browser.new_context(viewport={'width': 1440, 'height': 1000})
                page = context.new_page()
                errors, requests = [], []
                page.on('pageerror', lambda e: errors.append(str(e)))
                context.on('request', lambda r: requests.append((r.method, r.url)))
                page.goto(base)
                page.wait_for_selector('.article-card')
                assert page.locator('.article-card').count() > 0
                assert all('/reading/' in url for _, url in requests)
                assert 'The Guardian' in page.locator('#articles').inner_text()
                for exam in ['IELTS', 'TOEFL', '考研英语']:
                    page.locator(f'[data-exam="{exam}"]').click()
                    expect(page.locator(f'[data-exam="{exam}"]')).to_have_class('active')
                    assert page.locator('.article-card').count() > 0
                page.locator('#demo-toggle').uncheck()
                assert page.locator('.demo-label').count() == 0
                page.locator('#search').fill('nothing should match this title qzx')
                expect(page.locator('#empty')).to_be_visible()
                page.locator('#reset').click()
                page.locator('#import-open').click()
                page.locator('[name="title"]').fill('Local static test: climate and environment research')
                page.locator('[name="url"]').fill('https://example.org/leaf-pages-test')
                page.locator('[name="source"]').fill('Local owned source')
                page.locator('[name="summary_zh"]').fill('本地科学测试介绍')
                page.locator('[name="body"]').fill('Scientists study the environment and examine how climate affects community health. ' * 12)
                page.locator('#import-form [type="submit"]').click()
                expect(page.locator('#import-error')).not_to_be_empty()
                page.locator('[name="authorized"]').check()
                page.locator('#import-form [type="submit"]').click()
                expect(page.locator('#import-dialog')).not_to_be_visible()
                page.locator('#search').fill('本地科学测试')
                assert page.locator('.article-card').count() == 1
                expect(page.locator('#articles')).to_contain_text('132 words')
                page.locator('#difficulty').select_option('较难')
                page.locator('#length').select_option('short')
                page.locator('#topic').select_option('环境')
                page.locator('#source').select_option('Local owned source')
                assert page.locator('.article-card').count() == 1
                page.locator('[data-reason]').click()
                expect(page.locator('#detail-content')).to_contain_text('考研高频词覆盖率：暂无法分析')
                expect(page.locator('#detail-content')).to_contain_text('正文仅在当前浏览器计算与保存')
                page.locator('[data-close="detail-dialog"]').click()
                page.locator('[data-save]').click()
                expect(page.locator('#saved-count')).to_have_text('1')
                page.reload()
                page.wait_for_selector('.article-card')
                page.locator('#saved-nav').click()
                assert page.locator('.article-card').count() == 1
                expect(page.locator('#articles')).to_contain_text('132 words')
                context.route('https://example.org/leaf-pages-test', lambda route: route.fulfill(body='Original link test fixture', content_type='text/plain'))
                with page.expect_popup() as popup:
                    page.locator('[data-read]').click()
                popup.value.close()
                page.locator('#history-nav').click()
                assert page.locator('.article-card').count() == 1
                page.locator('#status-toggle').click()
                expect(page.locator('#statuses')).to_contain_text('08:23 / 20:23')
                expect(page.locator('#statuses')).to_contain_text('不会立刻抓取来源')
                page.route('**/data/articles.json*', lambda route: route.fulfill(status=503, body='offline fixture'))
                page.locator('#update').click()
                expect(page.locator('#update')).not_to_be_disabled()
                expect(page.locator('#notice')).to_contain_text('已有文章、本地导入和收藏已保留')
                assert page.locator('.article-card').count() == 1
                page.reload()
                page.wait_for_selector('.article-card')
                expect(page.locator('#notice')).to_contain_text('HTTP 503')
                assert page.locator('.article-card').count() > 1
                expect(page.locator('#saved-count')).to_have_text('1')
                page.unroute('**/data/articles.json*')
                page.locator('#update').click()
                expect(page.locator('#update')).not_to_be_disabled()
                expect(page.locator('#notice')).not_to_contain_text('HTTP 503')
                page.locator('#backup-open').click()
                with page.expect_download() as downloaded:
                    page.locator('#export').click()
                backup_file = directory / 'backup.json'
                downloaded.value.save_as(backup_file)
                backup = json.loads(backup_file.read_text())
                assert len(backup['saved']) == 1 and len(backup['imports']) == 1
                assert all('body' not in a for a in [*backup['saved'].values(), *backup['imports'].values()])
                visitor = browser.new_context()
                other = visitor.new_page()
                other.goto(base)
                other.wait_for_selector('.article-card')
                expect(other.locator('#saved-count')).to_have_text('0')
                expect(other.locator('#articles')).not_to_contain_text('Local static test:')
                other.locator('#backup-open').click()
                other.locator('#backup-file').set_input_files(backup_file)
                expect(other.locator('#backup-message')).to_contain_text('恢复成功')
                other.locator('[data-close="backup-dialog"]').click()
                other.locator('#saved-nav').click()
                expect(other.locator('#articles')).to_contain_text('Local static test:')
                expect(other.locator('#articles')).not_to_contain_text('132 words')
                visitor.close()
                page.locator('[data-close="backup-dialog"]').click()
                page.set_viewport_size({'width': 390, 'height': 844})
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                assert not any('/api/' in url or method != 'GET' for method, url in requests)
                assert not errors, errors
                browser.close()
                print('PASS: /reading/ assets and JSON; exam tabs; text/topic/source/length/difficulty filters; local import and analysis; save/history; offline cache; backup; visitor isolation; mobile width; no API/POST or JS errors.')
        finally:
            http.shutdown()
            http.server_close()
            worker.join()


if __name__ == '__main__':
    main()
