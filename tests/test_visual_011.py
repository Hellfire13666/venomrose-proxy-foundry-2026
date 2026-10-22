import base64
import hashlib
import tempfile
import unittest
from pathlib import Path
from venomrose import core
from venomrose.branding import ARTWORK, REPOSITORY, embedded_banner

EXPECTED_SHA256 = "bc3bec2a9752789b7ccc505722ae009058b8ba120bd84dd33cffcd04ae13f4c1"
ROOT = Path(__file__).resolve().parents[1]

class TestVisualEdition(unittest.TestCase):
    def test_exact_image_kept_unmodified(self):
        self.assertEqual(hashlib.sha256(ARTWORK.read_bytes()).hexdigest(), EXPECTED_SHA256)

    def test_data_uri_contains_exact_png_bytes(self):
        s=embedded_banner()
        self.assertTrue(s.startswith('data:image/png;base64,'))
        self.assertEqual(base64.b64decode(s.partition(',')[2]), ARTWORK.read_bytes())

    def test_html_offline_and_repository_visible(self):
        db, feeds, fetched, bad = core.demo_data()
        rep=core.build_report(list(db.values()),feeds,'SYNTHETIC DEMO',fetched,bad,0)
        page=core.render_html(rep)
        self.assertIn('img-src data:',page)
        self.assertIn('src="data:image/png;base64,',page)
        self.assertIn(REPOSITORY,page)
        self.assertNotIn('<script',page)
        self.assertIn('illustrative, not live scan results', page)

    def test_html_still_escapes_untrusted_feed_labels(self):
        db, feeds, fetched, bad = core.demo_data()
        feeds['<img src=x onerror=alert(1)>']={'state':'received','rows':0}
        rep=core.build_report(list(db.values()),feeds,'SYNTHETIC DEMO',fetched,bad,0)
        page=core.render_html(rep)
        self.assertIn('&lt;img src=x onerror=alert(1)&gt;',page)
        self.assertNotIn('<img src=x onerror=alert(1)>',page)

    def test_generated_report_is_portable(self):
        db, feeds, fetched, bad = core.demo_data()
        rep=core.build_report(list(db.values()),feeds,'SYNTHETIC DEMO',fetched,bad,0)
        with tempfile.TemporaryDirectory() as t:
            paths=core.save_report(rep,Path(t))
            page=Path(paths['html']).read_text()
            self.assertIn('src="data:image/png;base64,',page)
            self.assertTrue(Path(paths['csv']).exists())
            self.assertTrue(Path(paths['txt']).exists())
            self.assertTrue(Path(paths['json']).exists())

    def test_readme_and_launch_center_reference_original(self):
        self.assertIn('assets/venomrose-command-center-ORIGINAL.png',(ROOT/'README.md').read_text())
        html=(ROOT/'VENOMROSE-LAUNCH-CENTER.html').read_text()
        self.assertIn('assets/venomrose-command-center-ORIGINAL.png',html)
        self.assertIn(REPOSITORY,html)

    def test_version_bumped(self):
        self.assertEqual(core.VERSION, '0.1.1')

if __name__ == '__main__': unittest.main()
