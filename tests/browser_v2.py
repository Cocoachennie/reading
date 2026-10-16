"""V2 browser integration tests on the Pages project subpath; Playwright optional."""
import functools,json,shutil,sys,tempfile,threading
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.build_site import build
from playwright.sync_api import sync_playwright,expect

def run():
 with tempfile.TemporaryDirectory(prefix='leaf-v2-') as tmp:
  target=Path(tmp);build(target/'reading');http=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(SimpleHTTPRequestHandler,directory=str(target)));thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{http.server_port}/reading/'
  try:
   with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=shutil.which('chromium') or None,headless=True,args=['--no-sandbox']);context=browser.new_context(viewport={'width':1440,'height':1000});page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(base);page.wait_for_selector('.article-card');assert page.locator('.demo-label').count()==0
    page.locator('#search').fill('经济学');page.locator('#source').select_option('OpenStax · Principles of Economics 3e');assert page.locator('.article-card').count()==2
    page.locator('#difficulty').select_option('B2');page.locator('#length').select_option('medium');page.locator('#topic').select_option('经济');page.locator('#date').select_option('unknown');assert page.locator('.article-card').count()==1
    page.locator('#date').select_option('7');expect(page.locator('#empty')).to_be_visible();page.locator('#reset').click()
    default_count=page.locator('.article-card').count();page.locator('#all-articles').check();assert page.locator('.article-card').count()>default_count;page.locator('#all-articles').uncheck();page.locator('#candidate-toggle').uncheck();assert page.locator('.article-card').count()<default_count;page.locator('#candidate-toggle').check()
    lists={}
    for exam in ['考研英语','IELTS','TOEFL']:
     page.locator(f'[data-exam="{exam}"]').click();lists[exam]=page.locator('.article-card').evaluate_all('(cards)=>cards.map(c=>c.dataset.article).sort()')
    assert lists['考研英语']!=lists['TOEFL'];assert lists['IELTS']!=lists['考研英语']
    catalog=json.loads((ROOT/'static/data/articles.json').read_text());full=next(a for a in catalog['articles'] if a.get('body'));key=full['id'];page.goto(base+'#article='+__import__('urllib.parse',fromlist=['quote']).quote(key,safe=''));page.wait_for_selector('#reader-body');expect(page.locator('.license-box')).to_contain_text('CC BY-NC-SA')
    page.locator('#reader-font').select_option('24');assert page.locator('#reader-body').evaluate('(e)=>getComputedStyle(e).fontSize')=='24px'
    page.locator('#reader-line').select_option('2.1');page.locator('#reader-width').select_option('600')
    def select(start=0,end=45):
     page.locator('#reader-body p').first.scroll_into_view_if_needed();page.evaluate('''([start,end])=>{const p=document.querySelector('#reader-body p'),walker=document.createTreeWalker(p,NodeFilter.SHOW_TEXT),nodes=[];let n;while(n=walker.nextNode())nodes.push(n);const range=document.createRange();range.setStart(nodes[0],start);range.setEnd(nodes[0],Math.min(end,nodes[0].length));const selection=getSelection();selection.removeAllRanges();selection.addRange(range);p.dispatchEvent(new MouseEvent('mouseup',{bubbles:true}));}''',[start,end])
    select();expect(page.locator('#selection-tools')).to_be_visible();page.locator('#highlight-color').select_option('blue');page.locator('#selection-highlight').click();assert page.locator('#reader-body .highlight-blue').count()>0
    select(0,15);page.locator('#selection-note').click();page.locator('#note-text').fill('A real reading note');page.locator('#note-form [type="submit"]').click();expect(page.locator('#annotation-list')).to_contain_text('A real reading note')
    page.reload();page.wait_for_selector('#reader-body');expect(page.locator('#annotation-list')).to_contain_text('A real reading note');assert page.locator('#reader-body .highlight-blue').count()>0
    note=page.locator('.annotation').filter(has_text='A real reading note');note.locator('[data-edit]').click();page.locator('#note-text').fill('Edited and persisted');page.locator('#note-color').select_option('pink');page.locator('#note-form [type="submit"]').click();expect(page.locator('#annotation-list')).to_contain_text('Edited and persisted')
    page.locator('#reader-search').fill('research');assert page.locator('#reader-body .search-hit').count()>0
    page.locator('#note-search').fill('Edited');assert page.locator('.annotation').count()==1;page.locator('[data-jump]').click();page.locator('#note-search').fill('');page.locator('#reader-search').fill('')
    page.locator('#reading-status').select_option('completed');page.reload();page.wait_for_selector('#reader-body');expect(page.locator('#reading-status')).to_have_value('completed')
    select(0,10);page.locator('#selection-dictionary').click();expect(page.locator('#dictionary-result')).to_contain_text('科学的')
    page.route('https://api.dictionaryapi.dev/**',lambda route:route.fulfill(status=503,body='offline dictionary fixture'))
    page.locator('#dictionary-fetch').click();expect(page.locator('#dictionary-status')).to_contain_text('词典查询失败')
    page.locator('#dictionary-add').click();expect(page.locator('#word-lemma')).to_have_value('scientific');page.locator('#word-phonetic').fill('/manual-test/');page.locator('#word-form [type="submit"]').click()
    page.locator('#learning-nav').click();expect(page.locator('#learning-page')).to_be_visible();page.locator('[data-study-tab="words"]').click();expect(page.locator('#study-content')).to_contain_text('scientific');expect(page.locator('#study-content')).to_contain_text('科学的')
    page.locator('#review-open').click();page.locator('#review-begin').click();expect(page.locator('#quiz-question')).to_have_text('scientific');page.locator('#quiz-answer').fill('科学的');page.locator('#quiz-reveal').click();page.locator('[data-grade="5"]').click();expect(page.locator('#quiz-card')).to_contain_text('本轮复习完成');page.locator('#review-close').click()
    page.locator('#review-open').click();page.locator('#review-direction').select_option('zh-en');page.locator('#review-due-only').uncheck();page.locator('#review-begin').click();expect(page.locator('#quiz-question')).to_have_text('科学的');page.locator('#quiz-answer').fill('scientific');page.locator('#quiz-reveal').click();page.locator('[data-grade="3"]').click();page.locator('#review-close').click()
    page.locator('[data-study-tab="reviews"]').click();expect(page.locator('#study-content')).to_contain_text('英译中');expect(page.locator('#study-content')).to_contain_text('中译英')
    page.locator('[data-study-tab="words"]').click();page.locator('[data-word-edit]').click();page.locator('#word-meaning').fill('科学的；经验证的（测试笔记）');page.locator('#word-form [type="submit"]').click();page.reload();page.wait_for_selector('.vocab-card');expect(page.locator('#study-content')).to_contain_text('经验证的')
    with page.expect_download() as download:
     page.locator('#word-export').click()
    vocab=target/'words.csv';download.value.save_as(vocab);assert 'scientific' in vocab.read_text(encoding='utf-8-sig')
    page.locator('[data-study-tab="notes"]').click();expect(page.locator('#study-content')).to_contain_text('Edited and persisted');page.locator('[data-study-note]').click();page.wait_for_selector('#reader-body');expect(page.locator('#annotation-list')).to_contain_text('Edited and persisted')
    page.set_viewport_size({'width':390,'height':844});page.locator('#reader-notes-toggle').click();expect(page.locator('.reader-notes')).to_have_class('reader-notes mobile-open');page.locator('#reader-notes-close').click();page.locator('#reader-font').select_option('22');assert page.locator('#reader-body').evaluate('(e)=>getComputedStyle(e).fontSize')=='22px';assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.locator('#reader-save').click()
    page.locator('#import-open').click();page.locator('[name="title"]').fill('Local V2 private article');page.locator('[name="url"]').fill('https://example.org/private-v2');page.locator('[name="source"]').fill('My own authorized article');page.locator('[name="summary_zh"]').fill('仅限当前浏览器的授权正文');private_body=('Scientific research provides evidence for education and learning. '*20)+' Literal <script>alert("not executable")</script> text.';page.locator('[name="body"]').fill(private_body);page.locator('[name="authorized"]').check();page.locator('#import-form [type="submit"]').click();expect(page.locator('#reader-body')).to_contain_text('not executable')
    page.locator('#learning-nav').click();page.locator('#study-backup').click()
    with page.expect_download() as download:
     page.locator('#export').click()
    backup_file=target/'full-v2.json';download.value.save_as(backup_file);backup=json.loads(backup_file.read_text());assert backup['version']==2;assert backup['personal']['imports']['https://example.org/private-v2']['body']==private_body;assert len(backup['learning']['annotations'])==2;assert len(backup['learning']['reviews'])==2
    fresh=browser.new_context(viewport={'width':390,'height':844});other=fresh.new_page();other.on('pageerror',lambda e:errors.append(str(e)));other.goto(base);other.wait_for_selector('.article-card');other.locator('#learning-nav').click();other.locator('[data-study-tab="words"]').click();assert other.locator('.vocab-card').count()==0
    other.locator('#study-backup').click();other.locator('#backup-file').set_input_files(backup_file);expect(other.locator('#backup-message')).to_contain_text('恢复成功');other.locator('#backup-file').set_input_files(backup_file);expect(other.locator('#backup-message')).to_contain_text('恢复成功');assert other.evaluate('LeafReader.data.reviews.length')==2
    old_article={'id':'https://example.org/legacy','url':'https://example.org/legacy','title':'Legacy saved article','source':'Previous version','summary_zh':'旧版收藏'};old_file=target/'old-v1.json';old_file.write_text(json.dumps({'version':1,'saved':{old_article['id']:old_article},'history':{'https://example.org/history-only':'2026-10-15T01:00:00Z'},'imports':{}}));other.locator('#backup-file').set_input_files(old_file);expect(other.locator('#backup-message')).to_contain_text('恢复成功');assert other.evaluate('LeafReader.data.reviews.length')==2
    other.locator('[data-close="backup-dialog"]').click();other.locator('[data-study-tab="read"]').click();expect(other.locator('#study-content')).to_contain_text('已打开原文（未记录站内进度）');other.locator('[data-study-tab="words"]').click();other.locator('#study-backup').click()
    before=other.evaluate('localStorage.getItem("leaf-learning-v2")');bad_file=target/'bad.json';bad_file.write_text('{"version":2,"format":"leaf-reading-backup","personal":{},"learning":{}}');other.locator('#backup-file').set_input_files(bad_file);expect(other.locator('#backup-message')).to_contain_text('恢复失败');assert other.evaluate('localStorage.getItem("leaf-learning-v2")')==before
    other.locator('[data-close="backup-dialog"]').click();expect(other.locator('#study-content')).to_contain_text('scientific');other.goto(base+'#article=https%3A%2F%2Fexample.org%2Fprivate-v2');other.wait_for_selector('#reader-body');expect(other.locator('#reader-body')).to_contain_text('not executable');assert other.locator('#reader-body script').count()==0
    other.locator('#all-nav').click();other.wait_for_selector('.article-card');before=other.evaluate('localStorage.getItem("leaf-learning-v2")');other.route('**/data/articles.json*',lambda route:route.fulfill(status=503,body='offline fixture'));other.locator('#update').click();expect(other.locator('#notice')).to_contain_text('HTTP 503');assert other.evaluate('localStorage.getItem("leaf-learning-v2")')==before
    other.unroute('**/data/articles.json*');other.locator('#update').click();expect(other.locator('#notice')).not_to_contain_text('HTTP 503');assert other.evaluate('localStorage.getItem("leaf-learning-v2")')==before
    fresh.close()
    page.locator('[data-close="backup-dialog"]').click();page.locator('#all-nav').click();expect(page.locator('#catalog-page')).to_be_visible();assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors,errors
    browser.close();print('PASS V2 phase 4 (including full/legacy/invalid backups, isolation, update preservation): distinct exam lists; licensed in-site reader; typography; anchored highlights; note create/edit/search/location; refresh persistence; reading status; mobile width; no JS errors.')
  finally:http.shutdown();http.server_close();thread.join()
if __name__=='__main__':run()
