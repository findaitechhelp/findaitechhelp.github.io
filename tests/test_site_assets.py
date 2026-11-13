"""Stylesheet dependencies must be deployed too, including nested vendor icons."""
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.check_site import check_site

class StylesheetAssetTests(unittest.TestCase):
    def test_nested_css_images_are_checked_and_comments_ignored(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);vendor=root/'assets'/'vendor';vendor.mkdir(parents=True)
            css=vendor/'style.css';css.write_text('/* url(not-real.png) */ .a{background:url(images/icon.png)}',encoding='utf-8')
            self.assertTrue(any('broken CSS asset' in error for error in check_site(root)))
            (vendor/'images').mkdir();(vendor/'images'/'icon.png').write_bytes(b'fixture')
            self.assertEqual([],check_site(root))

    def test_css_parent_escape_is_not_a_valid_public_asset(self):
        with tempfile.TemporaryDirectory() as name:
            parent=Path(name);(parent/'private.png').write_bytes(b'private fixture')
            root=parent/'public';root.mkdir();(root/'style.css').write_text('a{background:url(../private.png)}',encoding='utf-8')
            self.assertTrue(any('broken CSS asset' in error for error in check_site(root)))
