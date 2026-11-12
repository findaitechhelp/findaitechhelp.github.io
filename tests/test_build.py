import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'site'))
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('review_builder',ROOT/'site'/'build.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
from tools.check_site import check_site,Page

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


    def test_learning_review_omits_sales_and_legal_drafts(self):
        target=Path(self.temp.name)/'learning-review'
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
            text=file.read_text(encoding='utf-8');self.assertIn('Learning and testing preview',text)
            self.assertIn('noindex,follow',text)


    def test_location_map_exposes_all_50_states_without_fake_local_counts(self):
        text=(self.output/'locations'/'index.html').read_text(encoding='utf-8')
        for state in builder.STATES:self.assertIn('data-map-state="'+state+'"',text)
        self.assertEqual(text.count('data-map-state='),50)
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
        self.assertIn('class="map-state has-listings"',text)
        self.assertIn('0 programs are nationwide online options',text)
        self.assertIn('Synthetic geography fixture',text)

if __name__=='__main__':unittest.main()
