import json
import tempfile
import unittest
from pathlib import Path
from scripts import build_site, update_articles as catalog


def article(url='https://example.org/science', title='Science and space research'):
    return {
        'id': url, 'title': title, 'url': url,
        'source': catalog.SOURCES[0]['name'], 'summary_zh': '公开 RSS 元数据',
        'summary_en': '', 'body': '', 'published_at': '2026-10-15T00:00:00+00:00',
        'collected_at': '2026-10-15T01:00:00+00:00', 'demo': False,
        'rights': '仅公开元数据',
    }


class CatalogTests(unittest.TestCase):
    def test_failed_sources_preserve_articles_and_last_success(self):
        previous = catalog.initial_catalog()
        previous['articles'].append(catalog.public_article(article()))
        previous['last_success'] = '2026-10-15T01:00:00+00:00'
        previous['statuses'][catalog.SOURCES[0]['id']]['last_success'] = previous['last_success']
        def offline(_):
            raise OSError('network unavailable')
        updated = catalog.update_catalog(previous, offline)
        self.assertEqual(updated['articles'], previous['articles'])
        self.assertEqual(updated['last_success'], previous['last_success'])
        self.assertTrue(all(s['state'] == '失败' for s in updated['statuses'].values()))
        self.assertEqual(updated['statuses'][catalog.SOURCES[0]['id']]['last_success'], previous['last_success'])
        self.assertIsNone(updated['scheduler']['last_scheduled_run'])

    def test_dedup_preserves_collection_date_and_updates_metadata(self):
        previous = catalog.initial_catalog()
        previous['articles'] = [catalog.public_article(article())]
        incoming = article(title='Updated science and space research')
        incoming['collected_at'] = '2026-10-16T00:00:00+00:00'
        updated = catalog.update_catalog(previous, lambda _: [incoming], event='schedule')
        self.assertEqual(len(updated['articles']), 1)
        self.assertEqual(updated['articles'][0]['collected_at'], article()['collected_at'])
        self.assertEqual(updated['articles'][0]['title'], incoming['title'])
        self.assertIsNotNone(updated['last_success'])
        self.assertIsNotNone(updated['scheduler']['last_scheduled_run'])
        self.assertEqual(updated['collection_event'], 'schedule')

    def test_partial_source_failure_is_visible(self):
        def partial(source):
            if source['id'] == 'nasa':
                raise ValueError('bad RSS')
            return [article()]
        updated = catalog.update_catalog(catalog.initial_catalog(), partial)
        self.assertEqual(updated['statuses']['nasa']['state'], '失败')
        self.assertEqual(updated['statuses']['guardian-science']['state'], '成功')
        self.assertIsNotNone(updated['last_success'])
        self.assertEqual(sum(not a['demo'] for a in updated['articles']), 1)

    def test_public_allowlist_strips_full_text_and_private_fields(self):
        private = article()
        private.update(body='PRIVATE FULL TEXT DO NOT PUBLISH', token='SECRET DO NOT PUBLISH')
        safe = catalog.public_article(private)
        payload = json.dumps(safe)
        self.assertNotIn('PRIVATE FULL TEXT', payload)
        self.assertNotIn('SECRET DO NOT PUBLISH', payload)
        self.assertIsNone(safe['analysis']['words'])
        self.assertIsNone(safe['analysis']['coverage'])
        self.assertTrue(safe['recommendations'])
        self.assertIsNone(safe['evidence'])

    def test_bad_json_is_not_overwritten_and_body_cannot_be_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'articles.json'
            path.write_text('original', encoding='utf-8')
            invalid = catalog.initial_catalog()
            invalid['articles'][0]['body'] = 'private text'
            with self.assertRaises(ValueError):
                catalog.write_catalog(path, invalid)
            self.assertEqual(path.read_text(), 'original')
        invalid = catalog.initial_catalog()
        invalid['articles'][0]['url'] = 'javascript:alert(1)'
        invalid['articles'][0]['demo'] = False
        with self.assertRaises(ValueError):
            catalog.validate_catalog(invalid)

    def test_static_build_contains_only_static_assets_and_relative_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = build_site.build(Path(tmp) / 'reading')
            self.assertTrue((output / '.nojekyll').is_file())
            self.assertTrue((output / 'data/articles.json').is_file())
            self.assertFalse((output / 'server.py').exists())
            self.assertFalse((output / '.git').exists())
            html = (output / 'index.html').read_text()
            self.assertIn('src="./app.js"', html)
            self.assertIn('href="./style.css"', html)
            self.assertNotIn('href="/', html)
            self.assertNotIn('src="/', html)
            script = (output / 'app.js').read_text()
            self.assertNotIn('/api/', script)
            self.assertIn("new URL('./data/articles.json',document.baseURI)", script)

    def test_checked_in_catalog_is_valid_and_matches_rules(self):
        state = catalog.validate_catalog(json.loads(catalog.CATALOG.read_text(encoding='utf-8')))
        self.assertTrue(state['articles'])
        self.assertTrue(all(not a.get('body') or catalog.permitted_body(a) for a in state['articles']))
        self.assertTrue({s['id'] for s in catalog.SOURCES}.issubset(state['statuses']))


if __name__ == '__main__':
    unittest.main()
