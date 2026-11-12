"""Verify the explicitly authorized public review without weakening search-launch gates."""
import datetime as dt
import importlib.util
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'site'))
sys.path.insert(0,str(ROOT))
from tools.check_site import check_site, Page
spec=importlib.util.spec_from_file_location('public_builder',ROOT/'site'/'build.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
def main():
    report=builder.build(dt.date.today(),public_review=True)
    errors=check_site(ROOT/'dist')
    if report['indexable']:errors.append('Review pages must not be indexable')
    for route in ['privacy','terms','how-we-make-money']:
        if (ROOT/'dist'/route).exists():errors.append('Unapproved legal draft exposed: '+route)
    for file in (ROOT/'dist').rglob('*.html'):
        page=Page();page.feed(file.read_text(encoding='utf-8'))
        if page.meta.get('robots')!='noindex,follow':errors.append('Missing noindex: '+str(file))
    config=json.loads((ROOT/'vercel.json').read_text())
    if config.get('buildCommand')!='python3 build.py --public-review':errors.append('Unexpected deployment mode')
    if errors:
        print('\n'.join(errors));return 1
    print('PASS: authorized public review, noindex, legal omission, links and source isolation.')
    print(json.dumps(report,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
