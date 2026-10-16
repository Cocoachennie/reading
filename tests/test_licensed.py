import copy
import hashlib
import json
import unittest
from scripts.licensed_sources import BOOKS,extract,permitted_body
from scripts.update_articles import CATALOG,public_article,validate_catalog

class LicensedTests(unittest.TestCase):
 def test_current_public_fulltexts_have_verified_provenance(self):
  data=json.loads(CATALOG.read_text());full=[a for a in data['articles'] if a.get('body')]
  self.assertGreater(len(full),0)
  for a in full:
   self.assertTrue(permitted_body(a));self.assertIn('OpenStax',a['license']['attribution']);self.assertIsNone(a['published_at'])
   self.assertEqual(a['analysis']['words'],len(__import__('re').findall(r"[A-Za-z]+(?:['’-][A-Za-z]+)*",a['body'])))
   self.assertIsNone(a['analysis']['coverage']);self.assertEqual(set(a['exam_scores']),{'考研英语','IELTS','TOEFL'})
 def test_tampered_text_and_spoofed_licenses_cannot_be_published(self):
  data=json.loads(CATALOG.read_text());a=copy.deepcopy(next(a for a in data['articles'] if a.get('body')))
  a['body']+=' A forged sentence.'
  self.assertFalse(permitted_body(a));self.assertEqual(public_article(a)['body'],'')
  data['articles']=[a]
  with self.assertRaises(ValueError):validate_catalog(data)
  a['license']['body_sha256']=hashlib.sha256(a['body'].encode()).hexdigest();a['source']='The Guardian · Science'
  self.assertFalse(permitted_body(a))
 def test_cnxml_extraction_omits_images_quotes_and_exercises(self):
  body=' '.join(['Open educational narrative sentence.']*25)
  xml=f'<document xmlns="http://cnx.rice.edu/cnxml"><title>Real title</title><content><para>{body}</para><figure><para>EXCLUDED IMAGE TEXT</para></figure><quote><para>EXCLUDED QUOTE</para></quote><exercise><para>EXCLUDED EXERCISE</para></exercise></content></document>'
  title,text=extract(xml);self.assertEqual(title,'Real title');self.assertIn('Open educational',text);self.assertNotIn('EXCLUDED',text)
  with self.assertRaises(ValueError):extract('<!DOCTYPE x><document/>')
 def test_failed_licensed_collection_preserves_existing_texts(self):
  from unittest.mock import patch
  from scripts.licensed_sources import collect
  old=json.loads(CATALOG.read_text());before=copy.deepcopy(old['articles']);last=old['last_success']
  with patch('scripts.licensed_sources.fetch_book',side_effect=OSError('source unavailable')):result=collect(old)
  self.assertEqual(result['articles'],before);self.assertEqual(result['last_success'],last)
  self.assertTrue(all(result['statuses']['openstax-'+b['repo']]['state']=='失败' for b in BOOKS))
