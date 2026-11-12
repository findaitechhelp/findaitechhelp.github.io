"""Create a review-only candidate skeleton. Never writes approved records."""
import argparse
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('id');p.add_argument('--name',required=True);p.add_argument('--url',required=True);a=p.parse_args()
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',a.id):p.error('Use a stable lowercase hyphenated id.')
    target=ROOT/'review'/'new'/(a.id+'.json');target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():p.error('Candidate already exists; existing review record was not changed.')
    record={'id':a.id,'name':a.name,'url':a.url,'status':'candidate','sources':[],'checked':None,'checker':'agent','review_note':'Incomplete candidate. Fetch two independent sources and exact quotes before review. Only Dan approves.'}
    target.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(target)
