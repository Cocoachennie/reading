"""Allowlisted OpenStax narrative adaptations, with verified CC BY-NC-SA 4.0 terms."""
import datetime as dt
import hashlib
import re
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

LICENSE_URL = 'https://creativecommons.org/licenses/by-nc-sa/4.0/'
BOOKS = [
 {'repo':'osbooks-psychology','book':'Psychology 2e','modules':['m82167','m82162'],'intro':'心理学与社会科学开放教材改编材料，练习研究论证与人类行为主题。'},
 {'repo':'osbooks-biology-bundle','book':'Biology 2e','modules':['m66427','m66428'],'intro':'生命科学开放教材改编材料，练习生物学与科学说明文。'},
 {'repo':'osbooks-astronomy','book':'Astronomy 2e','modules':['m59747','m59755'],'intro':'天文学开放教材改编材料，练习宇宙与科学研究主题。'},
 {'repo':'osbooks-principles-economics-bundle','book':'Principles of Economics 3e','modules':['m63580','m63581'],'intro':'经济学开放教材改编材料，练习社会、经济与资源配置主题。'},
]
NS={'c':'http://cnx.rice.edu/cnxml'}
def source_name(book):return 'OpenStax · '+book['book']
def source_id(book):return 'openstax-'+book['repo']
def stamp():return dt.datetime.now(dt.timezone.utc).isoformat()
def read(url):
 req=urllib.request.Request(url,headers={'User-Agent':'LeafReading/2.0 (noncommercial learning; github.com/Cocoachennie/reading)'})
 with urllib.request.urlopen(req,timeout=15) as r:
  data=r.read(2_000_001)
  if len(data)>2_000_000:raise ValueError('开放材料超过大小限制')
  return data.decode('utf-8')
def permitted_body(article):
 proof=article.get('license')
 if not isinstance(proof,dict) or proof.get('url')!=LICENSE_URL:return False
 book=next((b for b in BOOKS if source_name(b)==article.get('source')),None)
 if not book:return False
 module=proof.get('module');revision=proof.get('revision','')
 if module not in book['modules'] or not re.fullmatch('[0-9a-f]{40}',revision):return False
 expected=f"https://github.com/openstax/{book['repo']}/blob/main/modules/{module}/index.cnxml"
 license_source=f"https://raw.githubusercontent.com/openstax/{book['repo']}/{revision}/LICENSE"
 return article.get('id')==article.get('url')==expected and proof.get('verified_at') and proof.get('license_source')==license_source and proof.get('body_sha256')==hashlib.sha256(article.get('body','').encode()).hexdigest()
def extract(xml):
 if '<!ENTITY' in xml.upper() or '<!DOCTYPE' in xml.upper():raise ValueError('不支持外部实体')
 root=ET.fromstring(xml);content=root.find('c:content',NS)
 if content is None:raise ValueError('缺少正文')
 # Exclude figures, tables, quoted third-party material and exercises; no images.
 excluded={'figure','table','exercise','solution','media','quote','footnote'}
 paragraphs=[]
 def walk(node):
  tag=node.tag.rsplit('}',1)[-1]
  if tag in excluded:return
  if tag in ('para','title'):
   text=' '.join(''.join(node.itertext()).split())
   if text:paragraphs.append(text)
   return
  for child in node:walk(child)
 walk(content)
 title=root.findtext('c:title','',NS)
 if not title or sum(len(p.split()) for p in paragraphs)<80:raise ValueError('缺少可分析的授权正文')
 return title,'\n\n'.join(paragraphs)
def fetch_book(book):
 remote='https://github.com/openstax/'+book['repo']+'.git'
 result=subprocess.run(['git','ls-remote',remote,'HEAD'],capture_output=True,text=True,timeout=25,check=True)
 revision=result.stdout.split()[0]
 if not re.fullmatch('[0-9a-f]{40}',revision):raise ValueError('无法确定上游版本')
 base=f"https://raw.githubusercontent.com/openstax/{book['repo']}/{revision}/"
 license_text=read(base+'LICENSE')
 if 'Attribution-NonCommercial-ShareAlike 4.0 International' not in license_text:raise ValueError('来源许可已变更，暂停采集')
 articles=[]
 for module in book['modules']:
  xml=read(base+f'modules/{module}/index.cnxml');title,body=extract(xml)
  url=f"https://github.com/openstax/{book['repo']}/blob/main/modules/{module}/index.cnxml"
  articles.append(dict(id=url,url=url,title=title,source=source_name(book),summary_en='',summary_zh=book['intro'],published_at=None,collected_at=stamp(),demo=False,body=body,content_scope='授权改编学习正文：保留叙述段落，移除图表、引文和练习，非原书完整排版。',rights='OpenStax / Rice University 及贡献者；CC BY-NC-SA 4.0，非商业使用、署名、相同方式共享。',license=dict(name='CC BY-NC-SA 4.0',url=LICENSE_URL,attribution='OpenStax, Rice University and contributors · '+book['book'],module=module,revision=revision,revision_url=f"https://github.com/openstax/{book['repo']}/blob/{revision}/modules/{module}/index.cnxml",license_source=base+'LICENSE',verified_at=stamp(),body_sha256=hashlib.sha256(body.encode()).hexdigest())))
 return articles

def collect(previous):
 state=previous
 def run(book):
  try:return book,fetch_book(book),None
  except Exception as exc:return book,[],str(exc)[:240]
 for book,incoming,error in ThreadPoolExecutor(4).map(run,BOOKS):
  key=source_id(book);old=state['statuses'].get(key,{})
  if error:
   state['statuses'][key]={**old,'name':source_name(book),'state':'失败','error':error,'checked_at':stamp()};continue
  existing={a['id']:a for a in state['articles']}
  for a in incoming:
   if a['id'] in existing:a['collected_at']=existing[a['id']]['collected_at']
   existing[a['id']]=a
  state['articles']=list(existing.values());state['last_success']=stamp()
  state['statuses'][key]={'name':source_name(book),'state':'成功','last_success':stamp(),'checked_at':stamp(),'count':len(incoming)}
 return state
