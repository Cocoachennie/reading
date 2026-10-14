"""Reading Desk: standard-library server. No third-party dependencies."""
import datetime as dt
import email.utils
import json
import os
import re
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
PUBLIC_MODE = os.environ.get('PUBLIC_MODE', '1') == '1'
DATA = ROOT / '.local' / ('public-feeds.json' if PUBLIC_MODE else 'articles.json')
LOCK = threading.Lock()
UPDATE_LOCK = threading.Lock()
LAST_UPDATE_ATTEMPT = None
SOURCES = [
    {'id': 'guardian-science', 'name': 'The Guardian · Science', 'url': 'https://www.theguardian.com/science/rss'},
    {'id': 'guardian-environment', 'name': 'The Guardian · Environment', 'url': 'https://www.theguardian.com/environment/rss'},
    {'id': 'nasa', 'name': 'NASA · News', 'url': 'https://www.nasa.gov/feed/'},
]
# Editorial starter taxonomy; NOT derived from an examination corpus.
TOPICS = {
 '科技': ['technology', 'artificial intelligence', 'algorithm', 'digital', 'automation', 'robot', 'software'],
 '教育': ['education', 'school', 'university', 'student', 'learning', 'teacher', 'classroom'],
 '经济': ['economy', 'economic', 'inflation', 'market', 'trade', 'employment', 'finance'],
 '环境': ['climate', 'environment', 'carbon', 'biodiversity', 'ecosystem', 'conservation', 'pollution'],
 '政治与社会': ['politics', 'policy', 'election', 'democracy', 'government', 'society', 'community'],
 '科学': ['science', 'research', 'scientist', 'experiment', 'space', 'planet', 'astronomy'],
 '历史与文化': ['history', 'historical', 'ancient', 'archaeology', 'culture', 'museum', 'civilization'],
 '健康': ['health', 'medicine', 'disease', 'clinical', 'hospital', 'nutrition', 'patient'],
}
EXAMS = {
 '考研英语': ['科技', '教育', '经济', '环境', '政治与社会'],
 'IELTS': ['环境', '教育', '科技', '历史与文化', '健康'],
 'TOEFL': ['科学', '环境', '历史与文化', '教育', '健康'],
}

def now():
 return dt.datetime.now(dt.timezone.utc).isoformat()

def valid_url(value):
 p = urlparse(value)
 return p.scheme in ('http', 'https') and bool(p.hostname) and not p.username and not p.password

def classify(title, summary, body='', min_cues=2):
 # Exact terms with boundaries; distinct cues and co-occurrence required.
 text = ' '.join([title, summary, body]).lower()
 hits = {topic: [term for term in terms if re.search(r'\b' + re.escape(term) + r'\b', text)] for topic, terms in TOPICS.items()}
 # Context gate: distinct cues must co-occur in a 60-word window.
 windows = [' '.join(text.split()[i:i+60]) for i in range(0, max(1,len(text.split())), 30)]
 topics = [topic for topic, terms in hits.items() if any(sum(bool(re.search(r'\b'+re.escape(term)+r'\b', window)) for term in terms) >= min_cues for window in windows)]
 recommendations = []
 for exam, allowed in EXAMS.items():
  matched = [t for t in topics if t in allowed]
  if matched:
   recommendations.append({'exam': exam, 'reason': '主题初筛：' + '、'.join(matched) + '；同一主题在局部语境共同命中多个线索（' + ' / '.join(sum([hits[t] for t in matched], [])[:5]) + '）。需人工核对论述语境；不代表考试选用或全文难度适配。'})
 return topics, recommendations

def analyze(body):
 if not body.strip():
  return {'available': False, 'words': None, 'difficulty': None, 'coverage': None, 'basis': '暂无法分析：未获得获授权的完整正文。'}
 words = re.findall(r"[A-Za-z]+(?:['’-][A-Za-z]+)*", body)
 sentences = [s for s in re.split(r'[.!?]+', body) if re.search('[A-Za-z]', s)]
 if len(words) < 80 or len(sentences) < 3:
  return {'available': False, 'words': len(words), 'difficulty': None, 'coverage': None, 'basis': '正文不足 80 个英文词或 3 句；样本过短，不估计难度。'}
 avg = len(words) / len(sentences)
 long_ratio = sum(len(w) >= 8 for w in words) / len(words)
 level = '较难' if avg >= 25 or long_ratio >= .27 else '中等' if avg >= 17 or long_ratio >= .17 else '较易'
 return {'available': True, 'words': len(words), 'difficulty': level, 'coverage': None, 'average_sentence': round(avg, 1), 'long_word_ratio': round(long_ratio * 100, 1), 'basis': f'启发式估计：平均句长 {avg:.1f} 词，≥8 字母词占比 {long_ratio:.1%}。较难：句长≥25或长词≥27%；中等：句长≥17或长词≥17%；否则较易。非官方分级，长词仅为词汇复杂度代理；未分析语法或 CEFR。'}

def decorate(article, cues=2):
 topics, exams = classify(article['title'], article.get('summary_en', ''), article.get('body', ''), cues)
 return {**article, 'topics': topics, 'recommendations': exams, 'analysis': analyze(article.get('body', '')), 'evidence': None, 'source_label': '推荐阅读来源 · 未核实真题采用'}

def demos():
 titles = [
 ('Could artificial intelligence change the way we learn?', 'education school student learning teacher artificial intelligence technology', '当人工智能进入课堂，我们如何重新理解学习？', 'The Guardian'),
 ('The quiet work of restoring a living forest', 'climate environment biodiversity ecosystem conservation', '从森林修复看生态保护与气候变化的关联。', 'The Guardian'),
 ('What distant planets can tell us about our own world', 'science research scientist space planet astronomy', '探索行星研究与科学论证，练习学术阅读视角。', 'NASA'),
 ('Why the future of work is also a question of education', 'economy economic employment education university learning', '工作、教育与经济变化之间，有哪些值得讨论的联系？', 'The Economist'),
 ('Reading the past through ancient cities', 'history historical ancient archaeology culture civilization', '以古代城市为切入点，理解历史与文化研究。', '演示编辑部'),
 ('How communities respond to a changing climate', 'climate environment carbon politics policy community society', '观察社区行动与公共政策如何回应气候议题。', '演示编辑部'),
 ]
 return [dict(id='demo-'+str(i),title=t,summary_en=s,summary_zh=z,source=src,url='',published_at=None,collected_at=now(),body='',demo=True,rights='演示元数据；标题及简介为虚构示例，并非该来源实际发布内容。') for i,(t,s,z,src) in enumerate(titles)]

def load():
 if DATA.exists():
  return json.loads(DATA.read_text())
 return {'articles': demos(), 'statuses': {s['id']: {'state':'未获取','name':s['name'],'last_success':None} for s in SOURCES}, 'last_success': None, 'scheduler': False}

def save(state):
 DATA.parent.mkdir(exist_ok=True)
 temp = DATA.with_suffix('.tmp')
 temp.write_text(json.dumps(state,ensure_ascii=False))
 temp.replace(DATA)

def plain(text):
 return re.sub(r'\s+', ' ', re.sub('<[^>]+>', ' ', text or '')).strip()

def fetch(source):
 req = urllib.request.Request(source['url'], headers={'User-Agent':'ReadingDesk/1.0 (RSS metadata reader)'})
 with urllib.request.urlopen(req,timeout=12) as response:
  raw=response.read(2_000_001)
  if len(raw)>2_000_000: raise ValueError('RSS 响应超过限制')
 if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper(): raise ValueError('不支持包含外部实体的 XML')
 root=ET.fromstring(raw)
 items=root.findall('./channel/item')
 if not items: raise ValueError('RSS 不含可用文章条目')
 result=[]
 for item in items[:25]:
  title=plain(item.findtext('title'))
  link=(item.findtext('link') or '').strip()
  if not title or not valid_url(link): continue
  published=None
  try: published=email.utils.parsedate_to_datetime(item.findtext('pubDate')).isoformat()
  except (ValueError,TypeError,AttributeError): pass
  # Do not persist RSS descriptions/full content; classify on publicly supplied title only.
  result.append(dict(id=link,title=title,summary_en='',summary_zh='RSS 元数据条目；尚未提供人工中文简介，请前往原文阅读。',source=source['name'],url=link,published_at=published,collected_at=now(),body='',demo=False,rights='仅收集公开 RSS 标题、链接及日期；未复制全文，未获取转载授权。'))
 if not result: raise ValueError('没有有效的文章标题及链接')
 return result

class Handler(SimpleHTTPRequestHandler):
 timeout = 20
 def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT/'static'),**kwargs)
 def end_headers(self):
  self.send_header('X-Content-Type-Options', 'nosniff')
  self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
  self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'")
  super().end_headers()
 def respond(self,data,status=200):
  raw=json.dumps(data,ensure_ascii=False).encode()
  self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
 def do_GET(self):
  if self.path=='/healthz':
   self.respond({'status':'ok'}); return
  if self.path=='/api/articles':
   with LOCK: state=load()
   self.respond({**state,'articles':[decorate(a) for a in state['articles']],'sources':SOURCES,'topic_rules':TOPICS,'exam_rules':EXAMS}); return
  super().do_GET()
 def do_POST(self):
  global LAST_UPDATE_ATTEMPT
  # Restrict mutations to same-origin browser requests; no arbitrary URL fetching endpoint.
  origin=self.headers.get('Origin')
  if origin and urlparse(origin).netloc!=self.headers.get('Host'):
   self.respond({'error':'跨站请求被拒绝'},403); return
  if self.path not in ('/api/update','/api/import'):
   self.respond({'error':'不存在的接口'},404); return
  if PUBLIC_MODE and self.path=='/api/import':
   self.respond({'error':'公开网站仅支持浏览器本地导入，不接受或存储访客正文。'},403); return
  try:
   size=int(self.headers.get('Content-Length','0'))
   if size<0 or size>(4096 if self.path=='/api/update' else 1_000_000): raise ValueError('请求大小无效或超出限制')
   data=json.loads(self.rfile.read(size) or b'{}')
   if not isinstance(data,dict): raise ValueError('请求必须为 JSON 对象')
   if PUBLIC_MODE and self.path=='/api/update':
    with UPDATE_LOCK:
     current=time.monotonic()
     if LAST_UPDATE_ATTEMPT is not None and current-LAST_UPDATE_ATTEMPT<60:
      self.respond({'error':'来源正在更新或距离上次尝试不足 60 秒，请稍后再试。'},429); return
     LAST_UPDATE_ATTEMPT=current
   with LOCK:
    state=load()
    if self.path=='/api/update':
     succeeded=False
     for source in SOURCES:
      old=state['statuses'].get(source['id'],{})
      try:
       articles=fetch(source)
       existing={a['id']:a for a in state['articles']}
       for a in articles:
        if a['id'] not in existing: existing[a['id']]=a
       state['articles']=list(existing.values())
       state['statuses'][source['id']]={'name':source['name'],'state':'成功','count':len(articles),'last_success':now(),'checked_at':now()}
       succeeded=True
      except Exception as exc:
       state['statuses'][source['id']]={**old,'name':source['name'],'state':'失败','error':str(exc)[:240],'checked_at':now()}
     if succeeded: state['last_success']=now()
     if PUBLIC_MODE:
      state['articles']=state['articles'][-500:]
    else:
     title=str(data.get('title','')).strip()[:500]
     url=str(data.get('url','')).strip()
     body=str(data.get('body','')).strip()
     if not title or not valid_url(url): raise ValueError('请提供标题和有效的 HTTP(S) 原文链接')
     if body and data.get('authorized') is not True: raise ValueError('只有确认有权使用完整正文后才能导入')
     published=str(data.get('published_at','')).strip() or None
     if published: dt.date.fromisoformat(published)
     article=dict(id=url,title=title,url=url,source=str(data.get('source','手动导入'))[:100],published_at=published,collected_at=now(),summary_zh=str(data.get('summary_zh',''))[:600] or '手动导入，尚未添加中文简介。',summary_en=str(data.get('summary_en',''))[:2000],body=body,demo=False,rights='用户声明合法取得完整正文，仅限本地学习使用。' if body else '链接与用户提供的元数据；未获取全文。')
     state['articles']=[a for a in state['articles'] if a['id']!=url]+[article]
    save(state)
   self.respond({**state,'articles':[decorate(a) for a in state['articles']],'sources':SOURCES,'topic_rules':TOPICS,'exam_rules':EXAMS})
  except (ValueError,TypeError) as exc: self.respond({'error':str(exc)},400)

if __name__=='__main__':
 http = ThreadingHTTPServer(('0.0.0.0',int(os.environ.get('PORT','8000'))),Handler)
 print('Reading Desk on port '+os.environ.get('PORT','8000'),flush=True)
 http.serve_forever()
