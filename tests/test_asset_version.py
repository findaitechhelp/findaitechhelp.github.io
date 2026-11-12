"""Returning visitors must get a compatible style/script set after a UI change."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'site'))
spec=importlib.util.spec_from_file_location('asset_builder',ROOT/'site'/'build.py')
builder=importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

class AssetVersionTests(unittest.TestCase):
    def test_changed_asset_invalidates_the_version(self):
        with tempfile.TemporaryDirectory() as directory:
            files=[Path(directory)/name for name in ['style.css','app.js']]
            files[0].write_bytes(b'body { color: white; }\n')
            files[1].write_bytes(b'const version = 1;\n')
            original=builder.asset_fingerprint(files)
            self.assertEqual(original,builder.asset_fingerprint(files))
            files[1].write_bytes(b'const version = 2;\n')
            self.assertNotEqual(original,builder.asset_fingerprint(files))

    def test_windows_line_endings_do_not_change_the_version(self):
        with tempfile.TemporaryDirectory() as directory:
            file=Path(directory)/'style.css'
            file.write_bytes(b'a {}\nb {}\n')
            original=builder.asset_fingerprint([file])
            file.write_bytes(b'a {}\r\nb {}\r\n')
            self.assertEqual(original,builder.asset_fingerprint([file]))

    def test_file_boundaries_are_unambiguous(self):
        with tempfile.TemporaryDirectory() as directory:
            a,b=Path(directory)/'a',Path(directory)/'b'
            a.write_bytes(b'ab');b.write_bytes(b'c')
            original=builder.asset_fingerprint([a,b])
            a.write_bytes(b'a');b.write_bytes(b'bc')
            self.assertNotEqual(original,builder.asset_fingerprint([a,b]))
