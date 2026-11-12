"""Adversarial provenance, freshness, evidence and URL checks."""
import copy
import datetime as dt
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "tools"))
import validate as v
import check_links as c

TODAY = dt.date(2026, 11, 12)


def record():
    row = {
        "id": "test-program", "name": "Test only program", "url": "https://provider.example/program",
        "description": "Synthetic test fixture; not a real listing.", "status": "approved",
        "checked": "2026-11-12", "checker": "agent", "approved_by": "dan", "approved_on": "2026-11-12",
        "audience": ["business"], "cost": "Free", "format": "self-paced", "kind": "online-course",
        "sources": [
            {"url": "https://provider.example/program", "domain_class": "official", "quote": "A test class", "fetched": "2026-11-12"},
            {"url": "https://college.edu/news/program", "domain_class": "gov-edu", "quote": "A test class", "fetched": "2026-11-12", "independent": True},
        ],
    }
    return fixture_approval(row)


def fixture_approval(row):
    """Synthetic fixture setup only; never changes production approval records."""
    row["approval_fingerprint"] = v.approval_fingerprint(row)
    return row


class ValidationTests(unittest.TestCase):
    def test_valid_record(self):
        self.assertEqual([], v.validate_records([record()], TODAY))

    def test_approval_checksum_required(self):
        row = record(); del row["approval_fingerprint"]
        self.assertTrue(any("approval fingerprint" in e for e in v.validate_records([row], TODAY)))
        row = record(); row["approval_fingerprint"] = "wrong"
        self.assertTrue(any("approval fingerprint" in e for e in v.validate_records([row], TODAY)))

    def test_approval_hash_binds_all_facts_but_not_operational_fields(self):
        row = record(); original = row["approval_fingerprint"]
        for field, value in [("status", "paused"), ("checked", "2026-11-11"), ("checker", "dan"), ("approved_by", "dan"), ("approved_on", "2026-11-11"), ("pause_reason", "source outage")]:
            changed = copy.deepcopy(row); changed[field] = value
            self.assertEqual(original, v.approval_fingerprint(changed), field)
        for field, value in [("name", "Changed name"), ("cost", "$500"), ("url", "https://provider.example/changed"), ("description", "Changed facts"), ("audience", ["home-senior"]), ("eligibility", "Restricted to local residents")]:
            changed = copy.deepcopy(row); changed[field] = value
            self.assertNotEqual(original, v.approval_fingerprint(changed), field)

    def assert_bad(self, mutate, pattern):
        row = record()
        mutate(row)
        self.assertTrue(any(pattern in error for error in v.validate_records([row], TODAY)), pattern)

    def test_requires_dan_and_approval_date(self):
        self.assert_bad(lambda r: r.update(approved_by="agent"), "requires Dan")
        self.assert_bad(lambda r: r.update(approved_on="2026-11-13"), "requires Dan")

    def test_stale_and_future_dates(self):
        self.assert_bad(lambda r: r.update(checked="2026-01-01"), "stale")
        self.assert_bad(lambda r: r.update(checked="2026-11-13"), "future checked")
        self.assert_bad(lambda r: r["sources"][0].update(fetched="2026-11-13"), "future fetched")

    def test_missing_quote_and_two_domains(self):
        self.assert_bad(lambda r: r["sources"][0].update(quote=""), "exact quote")
        self.assert_bad(lambda r: r["sources"][1].update(url="https://news.provider.example/report"), "distinct registrable")
        self.assertEqual("provider.co.uk", v.domain("https://news.provider.co.uk/a"))

    def test_second_source_must_be_independent_not_directory(self):
        self.assert_bad(lambda r: r["sources"][1].update(independent=False), "independent non-directory")
        self.assert_bad(lambda r: r["sources"][1].update(domain_class="directory"), "independent non-directory")
        self.assert_bad(lambda r: r["sources"][0].update(domain_class="news"), "official source")

    def test_ids_enums_and_foreign_keys(self):
        self.assert_bad(lambda r: r.update(id="../../private"), "invalid id")
        self.assert_bad(lambda r: r.update(status="published"), "invalid status")
        self.assert_bad(lambda r: r.update(category="made-up"), "invalid category")
        self.assert_bad(lambda r: r.update(audience=["everyone-ish"]), "invalid audience")
        self.assert_bad(lambda r: r.update(state_id="zz"), "unknown state")
        self.assertTrue(v.validate_records([record(), record()], TODAY))
        row = record(); row["metro_id"] = "unknown"
        self.assertTrue(v.validate_records([row], TODAY, metro_centers={"ny-buffalo": [42.9, -78.8]}))

    def test_coordinates(self):
        row = record(); row.update(metro_id="ny-buffalo", lat=0, lng=0)
        self.assertTrue(any("150 km" in e for e in v.validate_records([row], TODAY, metro_centers={"ny-buffalo": [42.9, -78.8]})))

    def test_event_host_foreign_key_must_exist(self):
        with tempfile.TemporaryDirectory() as folder:
            directory=Path(folder)
            row=record();row.update(start="2026-11-13T10:00:00-05:00",host_provider_id="missing-provider");fixture_approval(row)
            for kind in ["providers","programs","events","resources"]:
                (directory/(kind+".json")).write_text(json.dumps([row] if kind=="events" else []),encoding="utf-8")
            self.assertTrue(any("unknown host_provider_id" in error for error in v.load_and_validate(directory,TODAY)))

    def test_unsafe_urls(self):
        for url in ["javascript:alert(1)", "http://provider.example", "https://user:pass@provider.example", "https://127.0.0.1/a", "https://localhost/a", "https://10.0.0.1", "https://provider.example:22", "https://provider.example/ bad"]:
            with self.subTest(url=url):
                self.assertFalse(v.safe_url(url))

    def test_candidate_never_approved(self):
        self.assert_bad(lambda r: r.update(status="candidate"), "must not claim approval")

    def test_event_requires_full_iso_datetime(self):
        row = record(); row["start"] = "2026-11-12"
        self.assertTrue(v.validate_records([row], TODAY, kind="events"))

    def test_malformed_field_types_return_errors_not_exceptions(self):
        for field in ["status", "checker", "format", "category", "availability", "paid_relationship", "state_id", "metro_id", "start"]:
            with self.subTest(field=field):
                row = record(); row[field] = {"bad": "type"}
                self.assertTrue(v.validate_records([row], TODAY))
        row = record(); row["audience"] = [{}]
        self.assertTrue(v.validate_records([row], TODAY))
        row = record(); row["sources"][0]["domain_class"] = {}
        self.assertTrue(v.validate_records([row], TODAY))


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patch = patch.object(v, "EVIDENCE_DIR", self.root)
        self.patch.start()

    def tearDown(self):
        self.patch.stop(); self.tmp.cleanup()

    def evidence(self, row, **changes):
        value = {"record_id": row["id"], "checked": TODAY.isoformat(), "pass": True,
                 "sources_sha256": v.source_fingerprint(row), "results": [{"url": s["url"], "final_url": s["url"], "pass": True, "status": 200, "quote_found": True} for s in row["sources"]]}
        value.update(changes)
        p = self.root / row["id"] / "latest.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value), encoding="utf-8")

    def test_no_evidence_is_hidden(self):
        self.assertEqual([], v.visible_records([record()], TODAY))

    def test_good_evidence_visible(self):
        row = record(); self.evidence(row)
        self.assertEqual([row], v.visible_records([row], TODAY))

    def test_facts_changed_after_approval_are_hidden_despite_good_sources(self):
        for field, value in [("name", "Changed name"), ("cost", "$500"), ("url", "https://provider.example/changed"), ("description", "Changed facts"), ("audience", ["home-senior"]), ("eligibility", "Restricted to local residents")]:
            with self.subTest(field=field):
                row = record(); self.evidence(row)
                before = v.source_fingerprint(row)
                self.assertEqual([row], v.visible_records([row], TODAY))
                row[field] = value
                self.assertEqual(before, v.source_fingerprint(row))
                self.assertEqual([], v.visible_records([row], TODAY))
                self.assertTrue(any("approval fingerprint" in e for e in v.validate_records([row], TODAY)))

    def test_absent_approval_checksum_blocks_display(self):
        row = record(); self.evidence(row)
        del row["approval_fingerprint"]
        self.assertEqual([], v.visible_records([row], TODAY))

    def test_array_inputs_fail_closed(self):
        for value in [None, {}, "bad", 42]:
            with self.subTest(value=value):
                self.assertTrue(v.validate_records(value, TODAY))
                self.assertEqual([], v.visible_records(value, TODAY))

    def test_source_changes_invalidate_evidence(self):
        row = record(); self.evidence(row)
        row["sources"][0]["quote"] = "A changed quote"
        self.assertEqual([], v.visible_records([row], TODAY))
        self.assertTrue(any("approval fingerprint" in e for e in v.validate_records([row], TODAY)))
        # A fresh source-check result cannot approve changed record content.
        self.evidence(row)
        self.assertTrue(v.evidence_current(row, TODAY))
        self.assertEqual([], v.visible_records([row], TODAY))

    def test_old_future_failed_incomplete_and_wrong_evidence_hidden(self):
        row = record()
        for change in [{"checked": "2026-11-04"}, {"checked": "2026-11-13"}, {"pass": False}, {"results": []}, {"record_id": "someone-else"}]:
            self.evidence(row, **change)
            self.assertEqual([], v.visible_records([row], TODAY))

    def test_malformed_evidence_is_hidden_without_crashing(self):
        row = record()
        self.evidence(row, results=["bad", "type"])
        self.assertEqual([], v.visible_records([row], TODAY))

    def test_candidate_and_paused_hidden_even_with_evidence(self):
        for status in ["candidate", "paused", "retired"]:
            row = record(); row["status"] = status
            self.evidence(row)
            self.assertEqual([], v.visible_records([row], TODAY))

    def test_expired_event_and_no_dates_hidden(self):
        row = record(); row["start"] = "2026-11-11T10:00:00-05:00"; fixture_approval(row); self.evidence(row)
        self.assertEqual([], v.visible_records([row], TODAY))
        row = record(); row["availability"] = "no_dates"; fixture_approval(row); self.evidence(row)
        self.assertEqual([], v.visible_records([row], TODAY))

    def test_checker_success_and_failure_are_fail_closed(self):
        row = record()
        evidence = c.check_record(row, TODAY, evidence_dir=self.root,
            fetcher=lambda s: {"url": s["url"], "final_url": s["url"], "pass": True, "status": 200, "quote_found": True})
        self.assertTrue(evidence["pass"])
        self.assertTrue(v.approved_and_current(row, TODAY))
        evidence = c.check_record(row, TODAY, evidence_dir=self.root,
            fetcher=lambda s: {"url": s["url"], "pass": False, "status": 403})
        self.assertFalse(evidence["pass"])
        self.assertEqual([], v.visible_records([row], TODAY))
        self.assertEqual("approved", row["status"])

    def test_sources_converging_on_provider_domain_fail_closed(self):
        row = record()
        evidence = c.check_record(row, TODAY, evidence_dir=self.root,
            fetcher=lambda source: {"url": source["url"], "final_url": row["url"], "pass": True, "status": 200, "quote_found": True})
        self.assertFalse(evidence["pass"])
        self.assertFalse(v.evidence_current(row, TODAY))
        self.assertEqual([], v.visible_records([row], TODAY))

    def test_evidence_requires_status_quote_and_unchanged_final_domain(self):
        row = record()
        for change in [{"final_url": "https://provider.example/program"}, {"final_url": "https://third.example/page"}, {"status": 403}, {"quote_found": False}, {"final_url": None}]:
            self.evidence(row)
            path = self.root / row["id"] / "latest.json"
            value = json.loads(path.read_text()); value["results"][1].update(change)
            path.write_text(json.dumps(value))
            self.assertEqual([], v.visible_records([row], TODAY))

    def test_checker_does_not_fetch_invalid_or_write_unsafe_id(self):
        row = record(); row["id"] = "../../escape"
        with patch.object(c, "fetch_source", side_effect=AssertionError("must not fetch")):
            evidence = c.check_record(row, TODAY, evidence_dir=self.root, fetcher=lambda _: self.fail("must not fetch"))
        self.assertFalse(evidence["pass"])
        self.assertEqual([], list(self.root.iterdir()))

    def test_quote_normalization_ignores_scripts(self):
        text = c.page_text(b"<h1>A test</h1><p>class &amp; more</p><script>secret quote</script>")
        self.assertIn("A test class & more", text)
        self.assertNotIn("secret quote", text)


if __name__ == "__main__":
    unittest.main()
