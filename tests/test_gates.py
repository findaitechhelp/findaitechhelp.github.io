"""Gate thresholds use synthetic data; approval/provenance is tested separately."""
import copy
import datetime as dt
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import gates

TODAY = dt.date(2026, 11, 12)
INTRO = "A distinct synthetic local introduction used only in tests."


def providers(count=10):
    return [{"id": f"provider-{i}", "name": f"Synthetic provider {i}", "status": "approved", "category": "ai-training", "cost": "$100", "state_id": "ny", "ai_specific": i < 3} for i in range(count)]


def event():
    return {"id": "event-1", "name": "Synthetic event", "status": "approved", "start": "2026-11-12T10:00:00-05:00"}


def state_records():
    rows = providers(8)
    rows[0].update(kind="sbdc", lead_center=True, ai_specific=True)
    return rows


class ThresholdTests(unittest.TestCase):
    def setUp(self):
        # Isolates the threshold logic. Real approval/evidence eligibility is
        # exercised by DefenseTests and test_validate.py, not faked in production.
        self.mock = patch.object(gates, "approved_and_current", side_effect=lambda row, today: row.get("status") == "approved")
        self.mock.start()

    def tearDown(self):
        self.mock.stop()

    def test_city_threshold_and_event(self):
        self.assertTrue(gates.city_gate(providers(), [event()], intro=INTRO, today=TODAY))
        self.assertFalse(gates.city_gate(providers(9), [event()], intro=INTRO, today=TODAY))
        self.assertFalse(gates.city_gate(providers(), [], intro=INTRO, today=TODAY))

    def test_city_free_program_alternative(self):
        rows = providers(); rows[0].update(cost="Free")
        self.assertTrue(gates.city_gate(rows, [], intro=INTRO, today=TODAY))
        rows[0].update(cost="Paid", free_option=True)
        self.assertTrue(gates.city_gate(rows, [], intro=INTRO, today=TODAY))
        rows[0].update(category="computer-repair")
        self.assertFalse(gates.city_gate(rows, [], intro=INTRO, today=TODAY))

    def test_generic_business_mentoring_is_not_confirmed_ai_training(self):
        rows=providers(); rows[0].update(cost="Free", kind="sbdc", ai_specific=False)
        self.assertFalse(gates.city_gate(rows, [], intro=INTRO, today=TODAY))

    def test_city_deduplicates_and_ignores_nonproviders(self):
        rows = providers(9); rows.append(copy.deepcopy(rows[0]))
        self.assertFalse(gates.city_gate(rows, [event()], intro=INTRO, today=TODAY))
        rows = providers(); rows[0].pop("category")
        self.assertFalse(gates.city_gate(rows, [event()], intro=INTRO, today=TODAY))
        rows = providers(); same = event(); same["id"] = rows[0]["id"]
        self.assertFalse(gates.city_gate(rows, [same], intro=INTRO, today=TODAY))

    def test_city_different_ids_do_not_duplicate_one_provider(self):
        rows = providers(); rows[-1]["name"] = rows[0]["name"]
        self.assertFalse(gates.city_gate(rows, [event()], intro=INTRO, today=TODAY))

    def test_state_counts_ai_items_with_named_hosts_not_distinct_hosts(self):
        # SEO-GEO section3 requires three AI-specific ITEMS, not three institutions.
        rows = state_records()
        for row in rows[:3]:
            row.pop("category")
            row["host_name"] = "One synthetic in-state institution"
        self.assertTrue(gates.state_gate(rows, state_id="ny", intro=INTRO, today=TODAY))
        for row in rows[:3]:
            row.pop("host_name")
        self.assertFalse(gates.state_gate(rows, state_id="ny", intro=INTRO, today=TODAY))

    def test_city_rejects_expired_or_unapproved_events(self):
        for changes in [{"start": "2026-11-11T10:00:00-05:00"}, {"status": "candidate"}, {"status": "paused"}, {"start": "2026-11-12"}]:
            row = event(); row.update(changes)
            self.assertFalse(gates.city_gate(providers(), [row], intro=INTRO, today=TODAY))

    def test_state_threshold_ai_hosts_and_lead_center(self):
        self.assertTrue(gates.state_gate(state_records(), state_id="ny", intro=INTRO, today=TODAY))
        self.assertFalse(gates.state_gate(state_records()[:7], state_id="ny", intro=INTRO, today=TODAY))
        rows = state_records(); rows[2]["ai_specific"] = False
        self.assertFalse(gates.state_gate(rows, state_id="ny", intro=INTRO, today=TODAY))
        rows = state_records(); rows[0]["lead_center"] = False
        self.assertFalse(gates.state_gate(rows, state_id="ny", intro=INTRO, today=TODAY))

    def test_state_none_found_requires_explicit_current_date(self):
        rows = state_records(); rows[0]["ai_specific"] = False; rows[3]["ai_specific"] = True
        rows[0]["ai_offering_note"] = "None found, checked 2026-11-12"
        self.assertTrue(gates.state_gate(rows, state_id="ny", intro=INTRO, today=TODAY))
        for note in ["None found", "None found, checked 2026-11-13", "None found, checked 2025-01-01", "Maybe none found, checked 2026-11-12"]:
            rows[0]["ai_offering_note"] = note
            self.assertFalse(gates.state_gate(rows, state_id="ny", intro=INTRO, today=TODAY), note)

    def test_state_requires_in_state_hosts_and_unique_ids(self):
        rows = state_records(); rows[2]["state_id"] = "tx"
        self.assertFalse(gates.state_gate(rows, state_id="ny", intro=INTRO, today=TODAY))
        rows = state_records(); rows[-1] = copy.deepcopy(rows[0])
        self.assertFalse(gates.state_gate(rows, state_id="ny", intro=INTRO, today=TODAY))
        rows = state_records(); rows[0]["status"] = "paused"
        self.assertFalse(gates.state_gate(rows, state_id="ny", intro=INTRO, today=TODAY))

    def test_missing_or_placeholder_intro_and_invalid_inputs(self):
        for intro in ["", "  ", None, "[Dan to add local details]"]:
            self.assertFalse(gates.city_gate(providers(), [event()], intro=intro, today=TODAY))
            self.assertFalse(gates.state_gate(state_records(), state_id="ny", intro=intro, today=TODAY))
        self.assertFalse(gates.city_gate(None, [], intro=INTRO, today=TODAY))
        self.assertFalse(gates.state_gate(state_records(), state_id="zz", intro=INTRO, today=TODAY))
        self.assertFalse(gates.state_gate(state_records(), state_id="ny", intro=INTRO, today="bad date"))


class DefenseTests(unittest.TestCase):
    def test_gate_rechecks_actual_approval_and_evidence(self):
        # The synthetic rows deliberately lack provenance, checksums and evidence.
        # A caller's claim that they are already eligible must not bypass defense.
        self.assertFalse(gates.city_gate(providers(), [event()], intro=INTRO, today=TODAY))
        self.assertFalse(gates.state_gate(state_records(), state_id="ny", intro=INTRO, today=TODAY))


if __name__ == "__main__":
    unittest.main()
