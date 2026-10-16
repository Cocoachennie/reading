"""Validate and copy static assets into a GitHub Pages artifact."""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.update_articles import validate_catalog


def build(destination=ROOT / '_site'):
    source = ROOT / 'static'
    for required in ('index.html', 'app.js', 'analysis.js', 'learning.js', 'reader.js', 'style.css', 'favicon.svg', 'data/articles.json'):
        if not (source / required).is_file():
            raise ValueError(f'缺少静态文件：{required}')
    if any(p.is_symlink() for p in source.rglob('*')):
        raise ValueError('不允许发布符号链接')
    validate_catalog(json.loads((source / 'data/articles.json').read_text(encoding='utf-8')))
    html = (source / 'index.html').read_text(encoding='utf-8')
    if 'href="/' in html or 'src="/' in html:
        raise ValueError('项目站点必须使用相对资源路径')
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    (destination / '.nojekyll').touch()
    print(f'GitHub Pages artifact ready: {destination}')
    return destination


if __name__ == '__main__':
    build()
