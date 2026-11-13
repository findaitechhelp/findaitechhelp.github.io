"""Check generated local links, metadata, headings, schema, and record isolation."""
from html.parser import HTMLParser
import argparse
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, unquote

ROOT=Path(__file__).resolve().parents[1]
class Page(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[];self.ids=[];self.h1=0;self.meta={};self.canonical=[];self.scripts=[];self.collect=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='h1':self.h1+=1
        if a.get('id'):self.ids.append(a['id'])
        if tag in ['a','link'] and a.get('href'):self.links.append(a['href'])
        if tag in ['script','img'] and a.get('src'):self.links.append(a['src'])
        if tag=='meta':self.meta[a.get('name',a.get('property'))]=a.get('content','')
        if tag=='link' and a.get('rel')=='canonical':self.canonical.append(a.get('href'))
        if tag=='script' and a.get('type')=='application/ld+json':self.collect=True;self.scripts.append('')
    def handle_data(self,data):
        if self.collect:self.scripts[-1]+=data
    def handle_endtag(self,tag):
        if tag=='script':self.collect=False

def check_site(directory):
    directory=Path(directory).resolve();errors=[];parsed={}
    for f in directory.rglob('*.html'):
        p=Page();p.feed(f.read_text(encoding='utf-8'));parsed[f]=p
        if p.h1!=1:errors.append(f'{f.relative_to(directory)}: expected one h1, got {p.h1}')
        if len(p.ids)!=len(set(p.ids)):errors.append(f'{f.relative_to(directory)}: duplicate ids')
        if not p.meta.get('description'):errors.append(f'{f.relative_to(directory)}: missing description')
        if len(p.canonical)!=1:errors.append(f'{f.relative_to(directory)}: missing/duplicate canonical')
        for source in p.scripts:
            try:json.loads(source)
            except ValueError:errors.append(f'{f.relative_to(directory)}: malformed JSON-LD')
    for f,p in parsed.items():
        for href in p.links:
            u=urlsplit(href)
            if u.scheme or u.netloc:continue
            target=(directory/unquote(u.path).lstrip('/')) if u.path.startswith('/') else (f.parent/unquote(u.path))
            if not u.path:target=f
            if target.is_dir():target=target/'index.html'
            if not target.is_file():errors.append(f'{f.relative_to(directory)}: broken link {href}')
            elif u.fragment and target in parsed and unquote(u.fragment) not in parsed[target].ids:errors.append(f'{f.relative_to(directory)}: missing anchor {href}')
    for banned in ['records','review','prototype','.git','.env','data']:
        if (directory/banned).exists():errors.append('Private/source directory exposed: '+banned)
    # CSS assets are not visible to the HTML link parser (for example Leaflet icons).
    for css in directory.rglob('*.css'):
        source=re.sub(r'/\*.*?\*/','',css.read_text(encoding='utf-8'),flags=re.S)
        for match in re.finditer(r'url\(\s*[\"\x27]?([^\)\"\x27]+)[\"\x27]?\s*\)',source):
            href=match.group(1).strip();u=urlsplit(href)
            if u.scheme or u.netloc or not u.path:continue
            target=((directory/unquote(u.path).lstrip('/')) if u.path.startswith('/') else (css.parent/unquote(u.path))).resolve()
            if not target.is_relative_to(directory) or not target.is_file():errors.append(f'{css.relative_to(directory)}: broken CSS asset {href}')
    return errors

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',nargs='?',type=Path,default=ROOT/'dist');a=p.parse_args();errors=check_site(a.directory)
    print('\n'.join(errors) if errors else 'PASS: generated local links, metadata, headings, schema, and source isolation.')
    raise SystemExit(bool(errors))
