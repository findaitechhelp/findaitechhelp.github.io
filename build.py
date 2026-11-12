"""Compatibility entrypoint for the separated standard-library site builder."""
from pathlib import Path
import runpy
import sys
if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).parent / 'site'))
    runpy.run_path(str(Path(__file__).parent / 'site' / 'build.py'), run_name='__main__')
