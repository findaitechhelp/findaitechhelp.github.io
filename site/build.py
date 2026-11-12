"""Deterministic static review builder. HTML is kept in templates."""
from __future__ import annotations
import argparse
import ast
import datetime as dt
import html
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
from string import Template
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.validate import validate_records,visible_records,load_and_validate
from content import STATES,NEEDS,AUDIENCES,GUIDES,QUESTIONS
from pages import make_pages, render, original_legal, esc, PLACE_INTROS
from tools.gates import city_gate
SITE='https://findaitechhelp.com'
UPDATED='2026-11-12'
TEMPLATES=ROOT/'site'/'templates'

def load_records(today,records_dir=None):
    records_dir=Path(records_dir) if records_dir else ROOT/'records'
    structural_errors=load_and_validate(records_dir,today)
    if structural_errors:raise ValueError('\n'.join(structural_errors))
    collections={};errors=[];ids=set()
    for kind in ['providers','programs','events','resources']:
        records=json.loads((records_dir/(kind+'.json')).read_text(encoding='utf-8'))
        record_errors=validate_records(records,today,kind=kind,metro_centers={'ny-buffalo':(42.93,-78.82),'tx-dallas':(32.86,-96.9)})
        if record_errors:
            errors.extend(record_errors);collections[kind]=[];continue
        for r in records:
            if r.get('id') in ids: errors.append('Duplicate global record id: '+str(r.get('id')))
            ids.add(r.get('id'))
        collections[kind]=visible_records(records,today)
    if errors: raise ValueError('\n'.join(errors))
    collections['events']=[e for e in collections['events'] if e['start'][:10]>=today.isoformat()]
    return collections

def release_blockers(records,pages,today=None):
    blockers=[];settings=json.loads((ROOT/'site'/'settings.json').read_text(encoding='utf-8'))
    if settings.get('legal_approved_by')!='dan':blockers.append('Legal pages need Danâ€™s approval; original drafts are preserved.')
    if settings.get('launch_approved_by')!='dan':blockers.append('Dan has not approved public launch.')
    if settings.get('freshness_delivery_verified') is not True:blockers.append('Scheduled source checks, rebuilds and stale-output withdrawal must be verified on the selected host.')
    if len([r for r in records['programs'] if not r.get('state_id') and not r.get('metro_id') and r.get('format') in ['online','self-paced','live-online']])<15:blockers.append('National layer needs at least 15 approved, evidence-current online programs.')
    for metro in ['ny-buffalo','tx-dallas']:
        local=[r for r in records['providers']+records['programs'] if r.get('metro_id')==metro]
        events=[r for r in records['events'] if r.get('metro_id')==metro]
        if not city_gate(local,events,intro=PLACE_INTROS[metro],today=today):blockers.append(metro+': city indexing gate is not satisfied.')
    for path,page in pages.items():
        if re.search(r'\[[^\]\n]{2,200}\]',page['body']):blockers.append(path+': unresolved placeholder.')
    return blockers

def build(today,release=False,output=None,records_dir=None,public_review=False):
    if release and public_review:raise ValueError('Choose release or public review, not both.')
    records=load_records(today,records_dir);pages=make_pages(today,records);blockers=release_blockers(records,pages,today=today)
    if release and blockers:raise ValueError('RELEASE BLOCKED:\n- '+'\n- '.join(blockers))
    if public_review:
        settings=json.loads((ROOT/'site'/'settings.json').read_text(encoding='utf-8'))
        if settings.get('public_review_approved_by')!='dan':raise ValueError('Public review needs owner authorization.')
        pages={path:page for path,page in pages.items() if path not in ['/privacy/','/terms/','/how-we-make-money/']}
        for page in pages.values():
            if re.search(r'\[[^\]\n]{2,200}\]',page['body']):raise ValueError('Public review cannot contain unfinished placeholders.')
    target=Path(output).resolve() if output else ROOT/'dist'
    if target.exists() and target != ROOT/'dist' and not (target/'build-report.json').is_file():raise ValueError('Unsafe output path: existing non-build directory')
    if target==ROOT or target in ROOT.parents or (ROOT in target.parents and target.relative_to(ROOT).parts[0] in ['site','data','records','tools','tests','prototype','review','.git']):raise ValueError('Unsafe output path')
    target.parent.mkdir(parents=True,exist_ok=True);staging=Path(tempfile.mkdtemp(prefix='.dist-',dir=target.parent))
    try:
        shutil.copytree(ROOT/'site'/'assets',staging/'assets');indexable=[]
        for path,page in pages.items():
            org={'@context':'https://schema.org','@type':'Organization','@id':SITE+'/#organization','name':'Find AI Tech Help','legalName':'VirtualEcommerce Inc.','url':SITE,'logo':SITE+'/assets/icon.svg','founder':{'@type':'Person','name':'Dan Herlehy','url':SITE+'/about/'}}
            webpage={'@context':'https://schema.org','@type':'WebPage','url':SITE+path,'name':page['title'],'description':page['description'],'dateModified':UPDATED,'publisher':{'@id':SITE+'/#organization'}}
            crumbs=[{'@type':'ListItem','position':1,'name':'Home','item':SITE+'/'}]
            if path!='/':
                if path.startswith('/ny/') and path!='/ny/':crumbs.append({'@type':'ListItem','position':2,'name':'New York','item':SITE+'/ny/'})
                elif path.startswith('/tx/') and path!='/tx/':crumbs.append({'@type':'ListItem','position':2,'name':'Texas','item':SITE+'/tx/'})
                elif path.startswith('/guides/') and path!='/guides/':crumbs.append({'@type':'ListItem','position':2,'name':'Guides','item':SITE+'/guides/'})
                crumbs.append({'@type':'ListItem','position':len(crumbs)+1,'name':page['title'],'item':SITE+path})
            breadcrumb={'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':crumbs}
            schema=render('schema',json=json.dumps([org,webpage,breadcrumb]+page['schema'],ensure_ascii=False).replace('<','\\u003c'))
            active={f'active_{n}':' aria-current="page"' if page['active']==n else '' for n in ['find','online','places','guides']}
            noindex=not release or page['noindex']
            document=render('base',title=esc(page['title']),description=esc(page['description']),canonical=esc(SITE+path),robots='noindex,follow' if noindex else 'index,follow',body=(render('notice',heading='Early website review',text='Listings show their source-check date. Confirm current details directly before enrolling. Local directories are still being researched.',extra='') if public_review else '')+page['body'],schema=schema,year=today.year,og_image=SITE+'/assets/social-card.svg',og_type='article' if path.startswith('/guides/') and path!='/guides/' else 'website',money_link='' if public_review else render('link',url='/how-we-make-money/',label='How we make money',attributes=''),**active)
            dest=staging/path.strip('/')/'index.html' if path.endswith('/') else staging/path.strip('/')
            dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(document,encoding='utf-8',newline='\n')
            if not noindex:indexable.append(path)
        sm=ET.Element('urlset',xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
        for path in indexable:
            node=ET.SubElement(sm,'url');ET.SubElement(node,'loc').text=SITE+path;ET.SubElement(node,'lastmod').text=UPDATED
        ET.ElementTree(sm).write(staging/'sitemap.xml',encoding='utf-8',xml_declaration=True)
        (staging/'robots.txt').write_text('User-agent: *\nAllow: /\nDisallow: /go/\nSitemap: '+SITE+'/sitemap.xml\n',encoding='utf-8')
        (staging/'llms.txt').write_text(('# Find AI Tech Help\n> Early public review; confirm listings directly. Search indexing is disabled.\n' if public_review else '# Find AI Tech Help\n> Local review build; directory coverage is not published.\n')+'\n'.join(SITE+p for p in indexable)+'\n',encoding='utf-8')
        (staging/'_headers').write_text('/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  X-Frame-Options: DENY\n  Permissions-Policy: camera=(), microphone=(), geolocation=()\n/assets/*\n  Cache-Control: public, max-age=3600\n',encoding='utf-8')
        (staging/'_redirects').write_text('/buffalo-ny/ /ny/buffalo/ 301\n/dallas-tx/ /tx/dallas/ 301\n',encoding='utf-8')
        report={'today':today.isoformat(),'mode':'public-review' if public_review else 'release' if release else 'local-review','pages':len(pages),'indexable':indexable,'visible_records':{k:len(v) for k,v in records.items()},'release_blockers':['Search launch remains disabled for this review.'] if public_review else blockers}
        (staging/'build-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        previous=target.with_name(target.name+'.previous')
        if previous.exists():raise ValueError('Inspect existing output backup before rebuilding: '+str(previous))
        if target.exists():target.rename(previous)
        try:staging.rename(target)
        except Exception:
            if previous.exists():previous.rename(target)
            raise
        if previous.exists():
            archive=target.parent/'.build-history'/target.name;archive.mkdir(parents=True,exist_ok=True)
            previous.rename(archive/staging.name)
    finally:
        if staging.exists():shutil.rmtree(staging)
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--today',default=dt.date.today().isoformat());p.add_argument('--release',action='store_true');p.add_argument('--output');p.add_argument('--public-review',action='store_true');args=p.parse_args()
    try:report=build(dt.date.fromisoformat(args.today),args.release,args.output,public_review=args.public_review)
    except (ValueError,OSError,json.JSONDecodeError) as e:print(e,file=sys.stderr);return 1
    print(json.dumps(report,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
