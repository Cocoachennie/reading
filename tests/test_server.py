import io
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch
import server

class ReadingTests(unittest.TestCase):
 def test_requires_multiple_distinct_context_cues(self):
  self.assertEqual(server.classify('AI technology technology', '')[0], [])
  topics, exams=server.classify('Climate and carbon policy', 'Environment conservation')
  self.assertIn('环境',topics)
  self.assertEqual({e['exam'] for e in exams},{'考研英语','IELTS','TOEFL'})
 def test_separate_exam_topics(self):
  _,exams=server.classify('Ancient history and archaeology', '')
  self.assertEqual({e['exam'] for e in exams},{'IELTS','TOEFL'})
 def test_full_text_only_and_estimate(self):
  self.assertIsNone(server.analyze('')['words'])
  self.assertIsNone(server.analyze('Short text.')['difficulty'])
  a=server.analyze(('Scientists study the environment and examine how climate affects community health. '*12))
  self.assertTrue(a['available']);self.assertEqual(a['words'],132)
  self.assertIsNone(a['coverage']);self.assertIn('非官方',a['basis'])
 def test_rss_metadata_not_full_content(self):
  xml=b'<rss><channel><item><title>Science and space research</title><link>https://example.com/article</link><pubDate>Tue, 13 Oct 2026 12:00:00 GMT</pubDate><description>Secret full content must not be stored</description></item></channel></rss>'
  with patch('server.urllib.request.urlopen',return_value=io.BytesIO(xml)):
   a=server.fetch(server.SOURCES[0])[0]
  self.assertEqual(a['body'],'');self.assertEqual(a['summary_en'],'')
  self.assertNotIn('Secret',json.dumps(a));self.assertTrue(a['published_at'])
 def test_http_import_and_failed_update_preserves_content(self):
  with tempfile.TemporaryDirectory() as temp,patch.object(server,'DATA',Path(temp)/'data.json'),patch.object(server,'PUBLIC_MODE',False):
   http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
   thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
   base='http://127.0.0.1:'+str(http.server_port)
   def post(path,body):
    req=urllib.request.Request(base+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req) as r:return json.load(r)
   try:
    article={'title':'Climate and environment conservation','url':'https://example.com/a','source':'Owned source','body':'Unlicensed text'}
    with self.assertRaises(urllib.error.HTTPError) as ctx:post('/api/import',article)
    self.assertEqual(ctx.exception.code,400)
    article['body']='';result=post('/api/import',article)
    self.assertEqual(len(result['articles']),7)
    with patch.object(server,'fetch',side_effect=urllib.error.URLError('blocked')):result=post('/api/update',{})
    self.assertEqual(len(result['articles']),7)
    self.assertIsNone(result['last_success'])
    self.assertTrue(all(s['state']=='失败' for s in result['statuses'].values()))
    with patch.object(server,'fetch',return_value=[server.demos()[0]|{'id':'https://example.com/live','demo':False,'url':'https://example.com/live'}]):
     result=post('/api/update',{})
    self.assertEqual(len(result['articles']),8);self.assertIsNotNone(result['last_success'])
    first=result['last_success']
    with patch.object(server,'fetch',side_effect=ValueError('bad RSS')):result=post('/api/update',{})
    self.assertEqual(result['last_success'],first)
    self.assertEqual(len(result['articles']),8)
    with self.assertRaises(urllib.error.HTTPError):post('/api/import',{'title':'bad','url':'javascript:alert(1)'})
   finally:http.shutdown();http.server_close();thread.join()

 def test_public_mode_keeps_imports_private_and_throttles_updates(self):
  with tempfile.TemporaryDirectory() as temp,patch.object(server,'DATA',Path(temp)/'public.json'),patch.object(server,'PUBLIC_MODE',True),patch.object(server,'LAST_UPDATE_ATTEMPT',None):
   http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
   thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
   base='http://127.0.0.1:'+str(http.server_port)
   def post(path,data):
    with urllib.request.urlopen(urllib.request.Request(base+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})) as r:return json.load(r)
   try:
    with server.LOCK:
     with urllib.request.urlopen(base+'/healthz') as r:
      self.assertEqual(json.load(r)['status'],'ok')
      self.assertEqual(r.headers['Cache-Control'],'no-store')
      self.assertIn("frame-ancestors 'none'",r.headers['Content-Security-Policy'])
    with self.assertRaises(urllib.error.HTTPError) as ctx:
     post('/api/import',{'title':'Private','url':'https://example.com/private','body':'Private full text','authorized':True})
    self.assertEqual(ctx.exception.code,403)
    self.assertFalse(server.DATA.exists())
    with patch.object(server,'fetch',side_effect=ValueError('unavailable')) as fetch:
     state=post('/api/update',{})
     self.assertEqual(len(state['articles']),6)
     with self.assertRaises(urllib.error.HTTPError) as ctx:post('/api/update',{})
     self.assertEqual(ctx.exception.code,429)
     self.assertEqual(fetch.call_count,len(server.SOURCES))
    with urllib.request.urlopen(base+'/api/articles') as r:
     self.assertNotIn('Private',r.read().decode())
   finally:http.shutdown();http.server_close();thread.join()

 def test_invalid_payload_is_rejected(self):
  http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
  thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
  try:
   request=urllib.request.Request('http://127.0.0.1:'+str(http.server_port)+'/api/update',data=b'[]',headers={'Content-Type':'application/json'})
   with self.assertRaises(urllib.error.HTTPError) as ctx:urllib.request.urlopen(request)
   self.assertEqual(ctx.exception.code,400)
  finally:http.shutdown();http.server_close();thread.join()

if __name__=='__main__':unittest.main()
