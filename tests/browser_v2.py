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
    page.set_viewport_size({'width':390,'height':844});page.locator('#reader-font').select_option('22');assert page.locator('#reader-body').evaluate('(e)=>getComputedStyle(e).fontSize')=='22px';assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors,errors
    browser.close();print('PASS V2 phase 3: distinct exam lists; licensed in-site reader; typography; anchored highlights; note create/edit/search/location; refresh persistence; reading status; mobile width; no JS errors.')
  finally:http.shutdown();http.server_close();thread.join()
if __name__=='__main__':run()
