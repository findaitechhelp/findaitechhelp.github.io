"""Prepare a private review queue without inventing provenance or approvals."""
import hashlib
import json
from pathlib import Path
import re
import unicodedata

ROOT=Path(__file__).resolve().parents[1]
def slug(text):return re.sub(r'[^a-z0-9]+','-',unicodedata.normalize('NFKD',text).encode('ascii','ignore').decode().lower()).strip('-')
def build_queue():
    folder=ROOT/'review';folder.mkdir(exist_ok=True)
    providers=json.loads((ROOT/'data/providers.json').read_text(encoding='utf-8'))
    events=json.loads((ROOT/'data/events.json').read_text(encoding='utf-8'))
    rows=[]
    for old in providers:
        rows.append({'id':old['metro']+'-'+slug(old['name']),'kind':'provider','status':'candidate','name':old['name'],'original':old,'missing':['Fresh fetched source quotes','Independent non-directory corroboration','Owner approval'],'note':'Original verified date is legacy metadata, not fresh evidence.'})
    for metro,entries in events.items():
        for old in entries:rows.append({'id':metro+'-'+slug(old['title'])+'-'+old['date'],'kind':'event','status':'candidate','name':old['title'],'original':old,'missing':['Organizer-page evidence and independent quote','Full start time/time zone','Owner approval'],'note':'Check current availability; preserve old event dates, never roll them forward.'})
    research=ROOT.parent/'research'/'national-candidates.json'
    if research.exists():
        for candidate in json.loads(research.read_text(encoding='utf-8')):
            rows.append({'id':candidate['id'],'kind':'national-program','status':'candidate','name':candidate['name'],'research':candidate,'missing':['Owner approval']+([] if candidate.get('independent_pair_machine_verified') else ['Independent corroboration and/or fresh successful source check'])})
    (folder/'approval-queue.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# Owner review queue','', 'Private local review only. No entries have been approved or published. Only Dan can approve. Approval does not replace source verification.','',f'{len(providers)} legacy providers, {sum(map(len,events.values()))} legacy events, {len(rows)-len(providers)-sum(map(len,events.values()))} national proposals.','']
    for row in rows:
        lines += ['## '+row['name'],'','ID: `'+row['id']+'` · '+row['kind']+' · candidate','', 'Needs: '+', '.join(row['missing']), '']
        if 'research' in row:
            c=row['research'];lines += ['Provider: '+c['url'],'',c['description'],'', 'Cost recorded: '+c['cost'],'']
            for source in c['sources']:lines += ['- '+source['url'],'  - Source quote: '+source['quote'],'  - Independent corroboration: '+str(source.get('independent',False))]
            lines += ['']
    (folder/'APPROVAL-QUEUE.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return len(rows)
if __name__=='__main__':print('Prepared',build_queue(),'candidates for private review. Zero approvals applied.')
