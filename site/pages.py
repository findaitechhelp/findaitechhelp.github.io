"""Page rendering and original editorial content assembly; no HTML literals."""
import json
import html
from pathlib import Path
from string import Template
from urllib.parse import urlencode
from content import STATES, NEEDS, AUDIENCES, GUIDES, QUESTIONS
from tools.gates import city_gate, state_gate
ROOT = Path(__file__).resolve().parents[1]
SITE = 'https://findaitechhelp.com'
UPDATED = '2026-11-12'
TEMPLATES = ROOT / 'site' / 'templates'
PLACE_INTROS = {
 'ny-buffalo': 'For Buffalo and Western New York, decide whether you need a class, an on-site workshop, or a small setup project. Ask whether the provider serves your location and can adapt the session to your tools.',
 'tx-dallas': 'For Dallas and the wider Dallas–Fort Worth area, confirm whether a session is online or in person and whether travel is included. Bring a clear learning goal and ask about follow-up support.',
 'ny': 'Across New York, compare learning format, eligibility, and access needs before enrolling. Start with a practical plan, then confirm a program’s availability directly with its organizer.',
 'tx': 'Across Texas, choose between remote learning and an in-person session before comparing providers. Ask about the starting level, the total cost, and how the class connects to your everyday work.'
}
if len(set(PLACE_INTROS.values())) != len(PLACE_INTROS):
    raise ValueError('City/state introductions must be distinct before indexing.')

def esc(value): return html.escape(str(value),quote=True)
def render(template_name,**values): return Template((TEMPLATES/(template_name+'.html')).read_text(encoding='utf-8')).substitute(values)
def paragraph(text): return render('text',text=esc(text))
def link(label,url,attributes=''): return render('link',label=esc(label),url=esc(url),attributes=attributes)
def listing(items): return render('list',items=''.join(render('item',text=esc(i)) for i in items))
def section(heading,body,ident=''): return render('section',heading=esc(heading),content=body,id_attribute=(' id="'+esc(ident)+'"') if ident else '')
def intro(heading,description,eyebrow='Find your next step'): return render('intro',heading=esc(heading),intro=esc(description),eyebrow=esc(eyebrow))
def card(name,description,url,tag='',action='Explore'): return render('card',name=esc(name),description=esc(description),url=esc(url),tag=esc(tag),action=esc(action))
def empty(heading,text,url='/find/',label='Find a starting plan'): return render('empty',heading=esc(heading),text=esc(text),url=esc(url),label=esc(label))
def state_options(): return ''.join(render('option',value=k,label=esc(v)) for k,v in STATES.items())
def guide_card(slug):
    g=GUIDES[slug]
    return card(g['title'],g['description'],'/guides/'+slug+'/',g['tag'],'Read the guide')
def city_cards():
    return ''.join(card(name,'Local directory research. No listings are published until review is complete.',path,'Directory preview','Explore the local page') for name,path in [('Buffalo, New York','/ny/buffalo/'),('Dallas, Texas','/tx/dallas/')])
def plan_cards(need=None):
    if need: return ''.join(card(label,note,'/find/'+need+'/'+key+'/','Choose your situation','Use this plan') for key,(label,note) in AUDIENCES.items())
    return ''.join(card(n['label'],n['summary'],'/find/'+key+'/','A practical starting point','Use this plan') for key,n in NEEDS.items())

def build_plan(need,audience,site_url=SITE):
    n=NEEDS[need]; label,note=AUDIENCES[audience]
    steps=''.join(render('step',number=f'{i:02}',heading=esc(h),text=esc(t)) for i,(h,t) in enumerate(n['steps'],1))
    links=guide_card(n['guide'])+card('Learning online','Compare remote and self-paced learning.','/online/','Anywhere')+card('Change your plan','Choose another situation or type of help.','/find/','Your next step')
    email_body='\n\n'.join([n['heading'],label,note]+[str(i)+'. '+h+': '+t for i,(h,t) in enumerate(n['steps'],1)]+QUESTIONS+[site_url+'/find/'+need+'/'+audience+'/'])
    email=link('Email this plan to myself','mailto:?'+urlencode({'subject':'My AI and tech help starting plan','body':email_body}))
    return intro(n['heading'],note,label)+render('plan',need=need,audience=audience,heading=esc(n['label']),summary=esc(n['summary']),steps=steps,questions=listing(QUESTIONS),cost=esc(n['cost']),safety=esc(n['safety']),links=links,email_link=email)

def map_content():
    topo=json.loads((ROOT/'data'/'states-albers-10m.json').read_text(encoding='utf-8'))
    sx,sy=topo['transform']['scale'];tx,ty=topo['transform']['translate'];arcs=[]
    for arc in topo['arcs']:
        x=y=0;points=[]
        for dx,dy in arc:
            x+=dx;y+=dy;points.append((x*sx+tx,y*sy+ty))
        arcs.append(points)
    def ring(indexes):
        points=[]
        for i in indexes: points.extend(arcs[i] if i>=0 else list(reversed(arcs[~i])))
        kept=[]
        for p in points:
            if not kept or (p[0]-kept[-1][0])**2+(p[1]-kept[-1][1])**2>=4: kept.append(p)
        return 'M'+'L'.join(f'{x:.1f},{y:.1f}' for x,y in kept)+'Z'
    paths=[]
    for g in topo['objects']['states']['geometries']:
        polygons=g['arcs'] if g['type']=='MultiPolygon' else [g['arcs']]
        name=g.get('properties',{}).get('name','')
        state=next((key for key,label in STATES.items() if label==name),None)
        if state:paths.append(render('map-path',d=''.join(ring(r) for poly in polygons for r in poly),state=state,label=esc(name+' — build a starting plan')))
    return render('map',paths=''.join(paths))

def cards_for_records(records):
    if any(r.get('paid_relationship','none')!='none' for r in records):raise ValueError('Paid relationships require an approved separate placement; unsupported in this review build.')
    return ''.join(render('record',audience=esc(' '.join(r.get('audience',[]))),kind=esc(r.get('category',r.get('kind','Learning resource')).replace('-',' ')),name=esc(r['name']),description=esc(r['description']),cost=esc(r.get('cost','Confirm with provider')),format=esc(r.get('format','Confirm with provider')),checked=esc(r['checked']),link=link('Visit '+r['name'],r['url'],' rel="noopener"')) for r in sorted(records,key=lambda x:(not (x.get('free_option') is True or x.get('cost','').startswith('Free')),x['name'].casefold())))
def event_cards(events):
    return ''.join(card(e['name'],e['start']+' · '+e.get('cost','Confirm cost with organizer'),e['url'],'Upcoming class','View organizer details') for e in sorted(events,key=lambda x:x['start']))

def provider_sections(providers):
    free=[r for r in providers if r.get('free_option') is True or (r.get('kind') and r.get('cost')=='Free')]
    paid=[r for r in providers if r not in free]
    groups=[('Start free',free),('AI training and classes',[r for r in paid if r.get('category')=='ai-training' or (r.get('kind') and not r.get('category'))]),('AI setup and consulting',[r for r in paid if r.get('category')=='ai-consulting']),('IT support and computer repair',[r for r in paid if r.get('category') in ['it-support','computer-repair']])]
    return ''.join(section(title,cards_for_records(rows)) for title,rows in groups if rows)

def place_body(name,providers,events,local_intro,ready=False):
    records=provider_sections(providers) if providers else empty('No local listings published here yet','We are checking sources before publishing a local directory. You can still use a practical nationwide plan.')
    if providers:
        rows=''.join(render('table-row',name=link(r['name'],r['url']),cost=esc(r.get('cost','Confirm directly')),format=esc(r.get('format','Confirm directly'))) for r in providers)
        records=render('table',caption='Local help at a glance',rows=rows)+records
    classes=event_cards(events) if events else empty('No upcoming classes published here yet','Prepare your questions and check the next available date with the organizer.','/find/learn/','Build a learning plan')
    related=card('Online learning','Compare learning formats.','/online/','Anywhere')+guide_card('five-questions-before-you-hire')+card('Explore locations','A starting plan for any U.S. state.','/locations/','Across the U.S.')
    return render('place',intro=intro('AI classes & technology help in '+name,local_intro,'Local help' if ready else 'Local directory preview'),coverage_banner=paragraph(str(len(providers))+' current listings. Info checked is a source check, not an endorsement.') if ready else render('notice',heading='Local directory preview',text=esc(str(len(providers))+' published listings. Search indexing stays off until this page meets its coverage requirements. No business listings appear until their evidence and owner approval are complete.'),extra=''),place=esc(name),records=records,events=classes,questions=listing(QUESTIONS),related=related)

def original_legal():
    # Exact prototype body text retained until Dan approves replacement legal pages.
    return json.loads((ROOT/'site'/'legal-original.json').read_text(encoding='utf-8'))

def make_pages(today,records,learning_review=False):
    share_origin="https://findaitechhelp-preview.vercel.app" if learning_review else SITE
    pages={}
    def add(path,title,description,body,active='',noindex=False,schema=None): pages[path]=dict(title=title,description=description,body=body,active=active,noindex=noindex,schema=schema or [])
    add('/','Find AI Tech Help — Your next step with AI & technology','Practical starting plans for learning AI, planning a small project, and getting technology help. Free options first.',render('home',city_cards=city_cards(),guide_cards=''.join(guide_card(k) for k in list(GUIDES)[:3])),'find')
    add('/find/','Find my help — A practical AI & tech plan','Choose who needs help, what you want to do, and your state. Get a starting plan without signing up.',intro('Let’s find your next step.','A few choices. A clearer plan. No technical vocabulary required.')+render('finder',states=state_options(),plans=plan_cards()),'find',True)
    for need in NEEDS:
        add('/find/'+need+'/',NEEDS[need]['label']+' — Choose a starting plan',NEEDS[need]['summary'],build_plan(need,'individual',share_origin)+section('Choose another situation',plan_cards(need)),'find',True)
        for audience in AUDIENCES: add('/find/'+need+'/'+audience+'/',NEEDS[need]['label']+' — '+AUDIENCES[audience][0],NEEDS[need]['summary'],build_plan(need,audience,share_origin),'find',True)
    locations=intro('Start where you are.','Local learning, online options, or a clearer plan. Choose the route that fits you.','Near you, or anywhere')+render('locations',states=state_options(),map=map_content(),cities=city_cards())
    add('/locations/','AI & tech help by location — Find AI Tech Help','Choose any U.S. state for a starting plan, or explore Buffalo and Dallas directory research.',locations,'places')
    add('/states/','Browse places — Find AI Tech Help','Choose a state for a starting plan or explore local directory research.',locations,'places',True)
    programs=[r for r in records['programs'] if not r.get('state_id') and not r.get('metro_id') and r.get('format') in ['online','self-paced','live-online']]
    online=intro('Learn online. Start small.','Compare a practical class with a self-paced course. Ask what is free, what costs extra, and whether help is available when you’re stuck.','Learning, anywhere')
    online+=section('A useful way to choose',listing(['Pick one task you want to do after learning.','Ask about starting level, format, accessibility, and total cost.','Practice with made-up information and check the result yourself.']))
    online+=section('Published online learning options',cards_for_records(programs) if programs else empty('The online directory is being checked','No program listings are published here yet. You can use a learning plan while the directory is prepared.','/find/learn/','Make a learning plan'))
    online+=section('Find a route that fits',''.join(card(label,note,'/find/learn/'+a+'/','For you') for a,(label,note) in AUDIENCES.items()))
    online+=section('Explore by audience',''.join(card(label,'See the published program list and a practical starting plan.','/free-ai-training/'+slug+'/','Learning for you') for slug,label in [('seniors','Seniors and families'),('small-business','Small businesses'),('veterans','Veterans'),('teachers','Teachers'),('nonprofits','Nonprofits')]))
    add('/online/','AI learning online — Free-first starting guide','Compare AI classes, ask about free options, and choose a learning format that fits.',online,'online',len(programs)<15)
    for slug,label,audience in [('seniors','seniors and families','senior'),('small-business','small businesses','business'),('veterans','veterans','individual'),('teachers','teachers','individual'),('nonprofits','nonprofits','business')]:
        audience_tags={'home-senior','seniors'} if slug=='seniors' else {'business','small-business'} if slug=='small-business' else {slug}
        selected=[r for r in programs if audience_tags.intersection(r.get('audience',[]))]
        body=intro('AI learning for '+label,'Choose a useful task, check the starting level, and ask about free options before paying.','A learning path for you')+section('Start with a practical plan',link('Open the learning plan','/find/learn/'+audience+'/'))
        body+=section('Published program options',cards_for_records(selected) if selected else empty('No program listings published for this audience yet','Use the learning plan to prepare questions. Eligibility and availability need checking before publication.','/find/learn/'+audience+'/','Use a learning plan'))
        add('/free-ai-training/'+slug+'/','AI learning for '+label+' — Starting guide','A practical starting guide to AI training for '+label+'.',body,'online',len(selected)<8)
    for st,city,name,metro in [('ny','buffalo','Buffalo, NY','ny-buffalo'),('tx','dallas','Dallas, TX','tx-dallas')]:
        providers=[r for r in records['providers']+records['programs'] if r.get('metro_id')==metro];events=[r for r in records['events'] if r.get('metro_id')==metro]
        city_ready=city_gate(providers,events,intro=PLACE_INTROS[metro],today=today)
        add('/'+st+'/'+city+'/','AI Classes & Training in '+name+': Free + Paid ('+str(today.year)+')','Local directory research and starting plans for AI classes and tech help in '+name+'.',place_body(name,providers,events,PLACE_INTROS[metro],city_ready),'places',not city_ready)
        state_records=[r for kind in ['providers','programs','resources'] for r in records[kind] if r.get('state_id')==st]
        state_ready=state_gate(state_records,state_id=st,intro=PLACE_INTROS[st],today=today)
        body=intro('AI & tech help in '+STATES[st],PLACE_INTROS[st],'State guide' if state_ready else 'State directory preview')+section('Choose a starting plan',plan_cards())+section('Local research',card(name,'Local directory research.','/'+st+'/'+city+'/','Directory preview'))
        body+=section('Published statewide options',cards_for_records(state_records)) if state_records else paragraph('No statewide directory entries are published yet.')
        add('/'+st+'/','AI Classes & Training in '+STATES[st]+' — Preview','Starting plans and local directory research for '+STATES[st]+'.',body,'places',not state_ready)
    calendar=intro('Make room for something useful.','Check date, time zone, cost, eligibility, and device requirements with the organizer before signing up.','Upcoming classes')
    calendar+=event_cards(records['events']) if records['events'] else empty('No upcoming classes published yet','The class calendar is being prepared. You can choose a learning goal now.','/find/learn/','Build a learning plan')
    add('/classes/','Upcoming AI classes — Find AI Tech Help','Published upcoming classes and a practical checklist before enrolling.',calendar,'online',not bool(records['events']))
    add('/guides/','Plain-English AI & technology guides','Practical guides to learning AI, planning projects, and getting computer help.',intro('A little clarity goes a long way.','Short, practical reading for your next decision.','The reading room')+section('Choose a guide',''.join(guide_card(k) for k in GUIDES)),'guides')
    for slug,g in GUIDES.items():
        n=NEEDS[g['need']];body=intro(g['title'],g['description'],g['tag'])+paragraph('Editorial draft prepared for owner review · Updated '+UPDATED)
        body+=''.join(section(h,paragraph(t)) for h,t in n['steps'])+section('Before you spend',paragraph(n['cost'])+paragraph(n['safety']))+section('Questions to ask',listing(QUESTIONS))+section('Take your next step',link('Build my starting plan','/find/'+g['need']+'/'))
        schema=[{'@context':'https://schema.org','@type':'Article','headline':g['title'],'description':g['description'],'datePublished':UPDATED,'dateModified':UPDATED,'author':{'@type':'Organization','name':'Find AI Tech Help','url':SITE+'/about/'}}]
        add('/guides/'+slug+'/',g['title']+' — Find AI Tech Help',g['description'],body,'guides',False,schema)
    about=intro('A clearer way to find help.','Find AI Tech Help is a project of VirtualEcommerce Inc., led by Dan Herlehy in Hamburg, New York.','About this project')
    about+=section('What we’re building',paragraph('A guide to learning AI, getting small projects set up, and finding everyday technology help. Free options come first. Listings are published only after source checks and owner approval.'))
    if not learning_review:about+=section('Our own service',paragraph('Dan offers AI training in Western New York and online workshops. This is our own service, kept separate from independent directory listings. Contact Dan to discuss fit, format, and the current price.')+link('Ask Dan about training','mailto:hello@findaitechhelp.com?subject=AI%20training%20question'))
    about+=section('The business',paragraph('VirtualEcommerce Inc. · 5309 Roberts Rd, Hamburg, NY 14075, USA')+link('Get in touch','/contact/'))
    add('/about/','About Find AI Tech Help','The purpose and business behind Find AI Tech Help.',about)
    method=intro('A source check, not a star rating.','The directory is designed to help you ask better questions. A listing is not an endorsement.','How listings are checked')+listing(['Research starts as a candidate, hidden from visitor pages.','A listing needs supporting quotes from two independent websites, including an official source and a qualifying independent second source.','Sources must pass a recent check, and Dan must approve the record.','Every build omits expired events and records with failed, missing, or stale evidence. Source checks and scheduled rebuilds must be configured before launch.','Editorial sections are alphabetical. Paid placements do not change the order.'])
    method+=section('Corrections',paragraph('Email the business name, page link, and correction. Do not send passwords or private customer records.')+link('Report a correction','mailto:hello@findaitechhelp.com?subject=Directory%20correction'))
    add('/methodology/','How directory listings are checked','Source, approval, freshness, and ordering rules for the directory.',method)
    contact=intro('Let’s make the next step clearer.',('Questions about this learning preview or a listing correction? Send a short email.' if learning_review else 'Questions about the guide, a listing correction, or Dan’s training? Send a short email.'),'Get in touch')+section('Email us',link('hello@findaitechhelp.com','mailto:hello@findaitechhelp.com?subject=Find%20AI%20Tech%20Help%20question',' class="button"')+paragraph('Please do not send passwords, payment details, or sensitive customer information. Email opens your own mail app; there is no website submission form.'))
    add('/contact/','Contact Find AI Tech Help',('Email a preview question or listing correction.' if learning_review else 'Email a question, training inquiry, or listing correction.'),contact)
    add('/list-your-business/','Suggest or correct a listing','Email a listing suggestion for owner review.',intro('Help us get the details right.','Suggest a provider, correct a listing, or request removal. Suggestions are reviewed before publication.')+link('Email a listing request','mailto:hello@findaitechhelp.com?subject=Listing%20request',' class="button"'))
    add('/get-matched/','Ask about AI & technology help','Choose a starting plan or email a question.',intro('Need a little direction?','Choose a plan or email a question without sending sensitive information.')+section('Choose a route',plan_cards())+link('Email a question','/contact/'),'find',True)
    for path,(title,body) in original_legal().items(): add(path,title+' — Find AI Tech Help',title+' for Find AI Tech Help.',body,'',True)
    add('/404.html','Page not found — Find AI Tech Help','Choose a starting plan or return home.',intro('Let’s get you back on track.','That page isn’t here. Choose the kind of help you need.','Page not found')+section('Find your way',plan_cards()),'',True)
    return pages
