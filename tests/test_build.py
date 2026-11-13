import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import quote

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'site'))
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('review_builder',ROOT/'site'/'build.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
from tools.check_site import check_site,Page
from pages import public_site_origin

class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.output=Path(cls.temp.name)/'first'
        cls.today=dt.date(2026,11,12)
        cls.fixture_records=Path(cls.temp.name)/'records';cls.fixture_records.mkdir()
        for kind in ['providers','programs','events','resources']:
            (cls.fixture_records/(kind+'.json')).write_text('[]',encoding='utf-8')
        cls.report=builder.build(cls.today,output=cls.output,records_dir=cls.fixture_records)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_links_metadata_headings_and_isolation(self):self.assertEqual(check_site(self.output),[])
    def test_preview_noindex_and_empty_sitemap(self):
        for file in self.output.rglob('*.html'):
            p=Page();p.feed(file.read_text(encoding='utf-8'));self.assertEqual(p.meta['robots'],'noindex,follow')
        self.assertNotIn('<loc>',(self.output/'sitemap.xml').read_text())
    def test_candidates_and_original_records_never_exposed(self):
        text='\n'.join(f.read_text(encoding='utf-8') for f in self.output.rglob('*.html'))
        self.assertNotIn('SRM Creative Solutions',text)
        self.assertNotIn('IBM SkillsBuild',text)
        self.assertEqual(self.report['visible_records'],dict.fromkeys(['providers','programs','events','resources'],0))
    def test_legal_body_preserved(self):
        for path,(_,body) in builder.original_legal().items():self.assertIn(body,(self.output/path.strip('/')/'index.html').read_text(encoding='utf-8'))
    def test_release_refuses_unapproved_and_preserves_output(self):
        before=(self.output/'index.html').read_bytes()
        with self.assertRaisesRegex(ValueError,'RELEASE BLOCKED'):builder.build(self.today,records_dir=self.fixture_records,release=True,output=self.output)
        self.assertEqual(before,(self.output/'index.html').read_bytes())
    def test_deterministic_build(self):
        second=Path(self.temp.name)/'second';builder.build(self.today,records_dir=self.fixture_records,output=second)
        first_hash={str(f.relative_to(self.output)):hashlib.sha256(f.read_bytes()).hexdigest() for f in self.output.rglob('*') if f.is_file()}
        second_hash={str(f.relative_to(second)):hashlib.sha256(f.read_bytes()).hexdigest() for f in second.rglob('*') if f.is_file()}
        self.assertEqual(first_hash,second_hash)
    def test_all_need_audience_plans_exist(self):
        for need in builder.NEEDS:
            for audience in builder.AUDIENCES:self.assertTrue((self.output/'find'/need/audience/'index.html').is_file())
    def test_50_states_but_no_empty_50_state_directories(self):
        self.assertEqual(len(builder.STATES),50)
        self.assertFalse((self.output/'ca').exists())
        self.assertIn('Alaska',(self.output/'locations'/'index.html').read_text(encoding='utf-8'))
        self.assertIn('Hawaii',(self.output/'locations'/'index.html').read_text(encoding='utf-8'))
    def test_valid_audience_aliases_reach_their_hubs(self):
        for audience, slug in [("seniors", "seniors"), ("home-senior", "seniors"), ("small-business", "small-business"), ("business", "small-business")]:
            row={"id":"synthetic-only","name":"Synthetic alias test","description":"Test fixture only, never a real listing.","url":"https://example.org/","cost":"Free","format":"self-paced","audience":[audience],"checked":"2026-11-12"}
            records={key:[] for key in ["providers","programs","events","resources"]};records["programs"]=[row]
            pages=builder.make_pages(self.today,records)
            self.assertIn("Synthetic alias test",pages["/free-ai-training/"+slug+"/"]["body"])

    def test_unsafe_output_rejected(self):
        with self.assertRaisesRegex(ValueError,'Unsafe output'):builder.build(self.today,records_dir=self.fixture_records,output=ROOT/'records')
    def test_repeated_custom_output_build_keeps_history_on_same_drive(self):
        target=Path(self.temp.name)/'repeat'
        builder.build(self.today,records_dir=self.fixture_records,output=target)
        builder.build(self.today,records_dir=self.fixture_records,output=target)
        self.assertTrue((target/'index.html').is_file())
        self.assertTrue((target.parent/'.build-history'/target.name).is_dir())
    def test_all_audience_hubs_are_linked_from_online(self):
        text=(self.output/'online'/'index.html').read_text(encoding='utf-8')
        for audience in ['seniors','small-business','veterans','teachers','nonprofits']:
            self.assertIn('/free-ai-training/'+audience+'/',text)
    def test_freshness_delivery_blocks_release_without_live_verification(self):
        records={key:[] for key in ['providers','programs','events','resources']}
        self.assertTrue(any('stale-output withdrawal' in s for s in builder.release_blockers(records,{})))

    def test_cloudflare_static_host_contract(self):
        target=Path(self.temp.name)/'cloudflare-review'
        builder.build(self.today,records_dir=self.fixture_records,output=target,public_review=True)
        headers=(target/'_headers').read_text()
        for expected in ['X-Content-Type-Options: nosniff','Referrer-Policy: strict-origin-when-cross-origin',
                         'X-Frame-Options: DENY','X-Robots-Tag: noindex, follow',
                         'Permissions-Policy: camera=(), microphone=(), geolocation=()',
                         '/assets/*\n  Cache-Control: public, max-age=3600']:
            self.assertIn(expected,headers)
        self.assertNotIn('X-Robots-Tag',builder.hosting_headers(release=True))
        self.assertEqual((target/'_redirects').read_text(),'/buffalo-ny/ /ny/buffalo/ 301\n/dallas-tx/ /tx/dallas/ 301\n')
        self.assertTrue((target/'404.html').is_file())
        self.assertFalse((target/'404.html'/'index.html').exists())
        self.assertFalse((target/'_worker.js').exists())
        self.assertFalse((target/'functions').exists())
        self.assertIn('Page not found',(target/'404.html').read_text(encoding='utf-8'))
        for name in ['privacy','terms','how-we-make-money']:
            self.assertFalse((target/name).exists())

    def test_public_origin_defaults_validation_and_shared_plan(self):
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(public_site_origin(True),'https://findaitechhelp-preview.vercel.app')
            self.assertEqual(public_site_origin(False),'https://findaitechhelp.com')
        for value in ['', 'http://example.com','https://user:secret@example.com','https://example.com/path',
                      'https://example.com?query=1','https://example.com#fragment','https://example.com?',
                      'https://localhost','https://127.0.0.1','https://[::1]','https://site.local',
                      'https://example.com:8443','https://bad_host.com','https://example.com\n']:
            with self.subTest(value=value),patch.dict(os.environ,{'PUBLIC_SITE_ORIGIN':value}):
                with self.assertRaisesRegex(ValueError,'PUBLIC_SITE_ORIGIN'):public_site_origin(True)
        target=Path(self.temp.name)/'cloudflare-origin'
        with patch.dict(os.environ,{'PUBLIC_SITE_ORIGIN':'https://Example.pages.dev:443/'}):
            self.assertEqual(public_site_origin(True),'https://example.pages.dev')
            report=builder.build(self.today,records_dir=self.fixture_records,output=target,public_review=True)
        plan=(target/'find'/'learn'/'individual'/'index.html').read_text(encoding='utf-8')
        self.assertIn(quote('https://example.pages.dev/find/learn/individual/',safe=''),plan)
        self.assertNotIn('findaitechhelp-preview.vercel.app',plan)
        self.assertIn('https://findaitechhelp.com/find/learn/individual/',plan)
        self.assertEqual(report['indexable'],[])
        self.assertEqual(check_site(target),[])


    def test_learning_review_omits_sales_and_legal_drafts(self):
        target=Path(self.temp.name)/'learning-review'
        with patch.dict(os.environ,{},clear=True):
            report=builder.build(self.today,records_dir=self.fixture_records,output=target,public_review=True)
        self.assertEqual(report['indexable'],[])
        self.assertEqual(check_site(target),[])
        about=(target/'about'/'index.html').read_text(encoding='utf-8')
        self.assertNotIn('Our own service',about)
        self.assertNotIn('Ask Dan about training',about)
        plan=(target/'find'/'learn'/'individual'/'index.html').read_text(encoding='utf-8')
        self.assertIn('https%3A%2F%2Ffindaitechhelp-preview.vercel.app%2Ffind%2Flearn%2Findividual%2F',plan)
        for route in ['privacy','terms','how-we-make-money']:self.assertFalse((target/route).exists())
        for file in target.rglob('*.html'):
            text=file.read_text(encoding='utf-8');self.assertIn('Directory preview',text)
            self.assertIn('noindex,follow',text)


    def test_location_map_exposes_all_50_states_without_fake_local_counts(self):
        text=(self.output/'locations'/'index.html').read_text(encoding='utf-8')
        for state in builder.STATES:self.assertIn('data-map-state="'+state+'"',text)
        self.assertEqual(text.count('data-map-state='),51)
        self.assertIn('data-map-state="dc"',text)
        self.assertNotIn('class="map-state has-listings"',text)
        self.assertIn('All U.S.',text)
        self.assertIn('id="location-results"',text)
    def test_explorer_separates_local_resources_and_national_programs(self):
        records={key:[] for key in ['providers','programs','events','resources']}
        sample={'id':'synthetic-only','name':'Synthetic geography fixture','description':'Test fixture only.','url':'https://example.org/','cost':'Free','format':'in-person','audience':['individual'],'checked':'2026-11-12','kind':'library','state_id':'ca','location_label':'Synthetic test city','location_slug':'test-city'}
        records['resources']=[sample]
        pages=builder.make_pages(self.today,records)
        text=pages['/locations/']['body']
        self.assertIn('data-local-state="ca"',text)
        self.assertIn('data-local-metro="ca-test-city"',text)
        self.assertIn('data-city="ca-test-city"',text)
        self.assertIn('/locations/?state=ca&amp;city=ca-test-city#location-results',text)
        self.assertIn('href="#directory-search"',text)
        self.assertIn('id="explore-city"',text)
        self.assertIn('class="map-state has-listings"',text)
        self.assertIn('0 programs are nationwide online options',text)
        self.assertIn('Synthetic geography fixture',text)
        ny=dict(sample,state_id='ny',metro_id='ny-buffalo',id='synthetic-buffalo')
        records['resources']=[ny]
        ny_page=builder.make_pages(self.today,records)['/ny/']['body']
        self.assertNotIn('Published statewide options',ny_page)
        self.assertIn('Published options in New York',ny_page)
        self.assertIn('Buffalo, New York',ny_page)

if __name__=='__main__':unittest.main()
