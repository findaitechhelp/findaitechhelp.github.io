"""Display changes must preserve price uncertainty, conditions and source facts."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'site'))
from listing import listing_facts
from pages import cards_for_records

def example(**changes):
    row={'id':'example','name':'Example learning','description':'Exact checked description.','cost':'Check provider','format':'varies','audience':['individual'],'state_id':'ny','location_label':'Buffalo, New York','checked':'2026-11-12','url':'https://example.org','sources':[]}
    row.update(changes)
    return row

class ListingDisplayTests(unittest.TestCase):
    def test_unknown_cost_does_not_become_paid_or_free(self):
        facts=listing_facts(example(cost='Request a project quote'))
        self.assertEqual('confirm',facts['cost_kind'])
        self.assertEqual('Request a project quote',facts['cost'])

    def test_conditional_free_and_workshop_fees_remain_distinct(self):
        self.assertEqual('eligible',listing_facts(example(cost='Free for accepted eligible applicants'))['cost_kind'])
        facts=listing_facts(example(cost='No-cost advising; confirm workshop fees',free_option=True))
        self.assertEqual('free',facts['cost_kind'])
        self.assertEqual('Check extra costs',facts['cost_caution'])
        self.assertEqual('No-cost advising; confirm workshop fees',facts['cost'])

    def test_explicit_paid_and_location_are_not_rewritten(self):
        facts=listing_facts(example(cost='Paid courses; confirm current tuition'))
        self.assertEqual('paid',facts['cost_kind'])
        self.assertEqual('Buffalo, New York',facts['location'])
        self.assertEqual('Format varies',facts['format_label'])

    def test_existing_eligibility_and_library_card_terms_stay_on_front(self):
        costs=['Free; library or university card required for center use.','No tuition; eligibility requirements apply.','Free for Mississippi participants; confirm current eligibility and credential terms.','Confirm library-card eligibility and access']
        for cost in costs:
            with self.subTest(cost=cost):
                facts=listing_facts(example(cost=cost,free_option=True))
                self.assertEqual('eligible',facts['cost_kind'])
                self.assertEqual(cost,facts['cost'])

    def test_concise_front_keeps_all_original_facts_in_native_details(self):
        cost='Free for selected businesses; other program fees may apply'
        html=cards_for_records([example(cost=cost,description='Exact <checked> wording.',sources=[{'url':'https://example.org/source','domain_class':'official'}])])
        self.assertIn('<details class="listing-details',html)
        self.assertIn('Exact &lt;checked&gt; wording.',html)
        self.assertIn(cost,html)
        self.assertIn('https://example.org/source',html)
        self.assertIn('Eligibility-based free',html)
        self.assertIn('Check extra costs',html)
        self.assertIn('alt=""',html)
        self.assertRegex(html,r'src="/assets/art/learning-[0-2]\.svg\?v=[a-f0-9]{12}"')

    def test_paid_relationship_still_requires_separate_approval(self):
        with self.assertRaises(ValueError):cards_for_records([example(paid_relationship='sponsor')])
