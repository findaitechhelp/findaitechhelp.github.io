"""Fail-closed record validation and publication eligibility (stdlib only)."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "evidence"
METRO_CENTERS = {"ny-buffalo": (42.93, -78.82), "tx-dallas": (32.86, -96.9)}
STATUSES = {"candidate", "approved", "paused", "retired"}
DOMAIN_CLASSES = {"official", "gov-edu", "news", "chamber", "directory", "social"}
AUDIENCES = {"business", "individual", "home-senior", "seniors", "veterans", "teachers", "nonprofits", "small-business"}
FORMATS = {"in-person", "live-online", "self-paced", "on-site", "online", "hybrid", "varies", "not-specified"}
CATEGORIES = {"ai-training", "ai-consulting", "it-support", "computer-repair"}
PROGRAM_KINDS = {"sbdc", "score", "chamber-baisics", "openai-academy", "library", "college", "online-course", "senior", "veteran", "other"}
STATE_IDS = set("al ak az ar ca co ct de fl ga hi id il in ia ks ky la me md ma mi mn ms mo mt ne nv nh nj nm ny nc nd oh ok or pa ri sc sd tn tx ut vt va wa wv wi wy dc".split())
ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
# Deliberately conservative support for common multi-label public suffixes.
# Other country suffixes must be reviewed before relying on domain independence.
MULTI_SUFFIXES = {"co.uk", "org.uk", "ac.uk", "gov.uk", "com.au", "org.au", "edu.au", "co.nz", "co.jp", "co.in", "com.br", "com.cn", "com.mx", "co.za"}
BLOCKED_HOSTS = {"localhost", "localhost.localdomain", "metadata.google.internal"}
APPROVAL_OPERATIONAL_FIELDS = {
    "status", "checked", "checker", "approved_by", "approved_on",
    "approval_fingerprint", "pause_reason",
}


def _date(value):
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    try:
        return dt.date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def safe_url(url):
    """Only externally hosted HTTPS URLs; never credentials/local/private hosts."""
    import ipaddress
    if not isinstance(url, str) or not url or any(ord(c) <= 32 for c in url):
        return False
    try:
        u = urlsplit(url)
        host = (u.hostname or "").lower().rstrip(".")
        if u.scheme != "https" or not host or u.username or u.password or u.port not in (None, 443):
            return False
        if host in BLOCKED_HOSTS or host.endswith((".local", ".localhost", ".internal")) or "." not in host:
            return False
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            return bool(re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", host)) and ".." not in host
    except ValueError:
        return False


def domain(url):
    """Conservative registrable-domain comparison, without guessing by suffix."""
    if not safe_url(url):
        return ""
    labels = urlsplit(url).hostname.lower().rstrip(".").split(".")
    suffix = ".".join(labels[-2:])
    return ".".join(labels[-3:]) if suffix in MULTI_SUFFIXES else suffix


def source_fingerprint(record):
    payload = json.dumps(record.get("sources", []), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def approval_fingerprint(record):
    """Bind human approval to all content facts and the exact source bundle.

    This is a change detector, not a signature or an approval action. Only the
    owner's review workflow may record the resulting value as an approval.
    Unknown/new fields are included so future published facts fail closed too.
    """
    facts = {key: value for key, value in record.items() if key not in APPROVAL_OPERATIONAL_FIELDS}
    payload = json.dumps(facts, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _distance_km(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    v = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371 * 2 * math.asin(min(1, math.sqrt(v)))


def validate_records(records, today, kind="programs", metro_centers=None):
    """Return all errors. Incomplete candidates belong in review/, not records/."""
    today = _date(today)
    if metro_centers is None:
        metro_centers = METRO_CENTERS
    if today is None:
        return ["today must be an ISO date"]
    if not isinstance(records, list):
        return [f"{kind}: expected a JSON list"]
    errors, seen = [], set()
    for index, record in enumerate(records):
        label = f"{kind}[{index}]"
        if not isinstance(record, dict):
            errors.append(f"{label}: expected an object")
            continue
        rid = record.get("id")
        if not isinstance(rid, str) or not ID_PATTERN.fullmatch(rid):
            errors.append(f"{label}: invalid id")
        elif rid in seen:
            errors.append(f"{label}: duplicate id {rid}")
        else:
            seen.add(rid)
        label = f"{kind}/{rid or index}"
        for field in ("name", "description"):
            if not isinstance(record.get(field), str) or not record[field].strip():
                errors.append(f"{label}: missing {field}")
        if not safe_url(record.get("url")):
            errors.append(f"{label}: url must be a safe external HTTPS URL")
        if not isinstance(record.get("status"), str) or record["status"] not in STATUSES:
            errors.append(f"{label}: invalid status")
        checked = _date(record.get("checked"))
        if checked is None or checked > today:
            errors.append(f"{label}: invalid/future checked date")
        if not isinstance(record.get("checker"), str) or record["checker"] not in {"agent", "dan"}:
            errors.append(f"{label}: invalid checker")
        if record.get("status") == "approved":
            approved = _date(record.get("approved_on"))
            if record.get("approved_by") != "dan" or approved is None or approved > today:
                errors.append(f"{label}: approved record requires Dan and a non-future approval date")
            if checked and (today - checked).days > 120:
                errors.append(f"{label}: approved record is stale; pause it")
            try:
                expected_approval = approval_fingerprint(record)
            except (TypeError, ValueError):
                expected_approval = None
            saved_approval = record.get("approval_fingerprint")
            if not isinstance(saved_approval, str) or saved_approval != expected_approval:
                errors.append(f"{label}: approval fingerprint missing or content changed; Dan must review again")
        elif record.get("approved_by") or record.get("approved_on"):
            # Paused/retired records may retain their prior human approval audit.
            if record.get("status") == "candidate":
                errors.append(f"{label}: candidate must not claim approval")
        if record.get("status") == "candidate" and record.get("approval_fingerprint"):
            errors.append(f"{label}: candidate must not claim an approval fingerprint")
        sources = record.get("sources")
        valid_sources = []
        if not isinstance(sources, list):
            errors.append(f"{label}: sources must be a list")
            sources = []
        for i, source in enumerate(sources):
            prefix = f"{label}: source {i+1}"
            if not isinstance(source, dict):
                errors.append(f"{prefix} must be an object")
                continue
            valid_sources.append(source)
            if not safe_url(source.get("url")):
                errors.append(f"{prefix} has unsafe URL")
            if not isinstance(source.get("domain_class"), str) or source["domain_class"] not in DOMAIN_CLASSES:
                errors.append(f"{prefix} has invalid domain_class")
            quote = source.get("quote")
            if not isinstance(quote, str) or not quote.strip():
                errors.append(f"{prefix} needs an exact quote")
            fetched = _date(source.get("fetched"))
            if fetched is None or fetched > today:
                errors.append(f"{prefix} has invalid/future fetched date")
            if "independent" in source and type(source["independent"]) is not bool:
                errors.append(f"{prefix} independent must be boolean")
        domains = {domain(s.get("url")) for s in valid_sources} - {""}
        own = domain(record.get("url"))
        if len(domains) < 2:
            errors.append(f"{label}: need two distinct registrable source domains")
        if not any(domain(s.get("url")) == own and isinstance(s.get("domain_class"), str) and s["domain_class"] in {"official", "gov-edu"} for s in valid_sources):
            errors.append(f"{label}: needs an official source on its own domain")
        if not any(domain(s.get("url")) not in {"", own} and isinstance(s.get("domain_class"), str) and s["domain_class"] in DOMAIN_CLASSES - {"directory", "social"} and s.get("independent") is True for s in valid_sources):
            errors.append(f"{label}: needs an independent non-directory second source")
        if "audience" in record:
            audience = record["audience"]
            if not isinstance(audience, list) or not audience or any(not isinstance(a, str) or a not in AUDIENCES for a in audience):
                errors.append(f"{label}: invalid audience")
        elif kind in {"programs", "providers"}:
            errors.append(f"{label}: missing audience")
        if "format" in record and (not isinstance(record["format"], str) or record["format"] not in FORMATS):
            errors.append(f"{label}: invalid format")
        if kind == "providers" and "category" not in record:
            errors.append(f"{label}: missing category")
        if kind == "programs" and "kind" not in record:
            errors.append(f"{label}: missing program kind")
        if "category" in record and (not isinstance(record["category"], str) or record["category"] not in CATEGORIES):
            errors.append(f"{label}: invalid category")
        if "availability" in record and (not isinstance(record["availability"], str) or record["availability"] not in {"current", "no_dates"}):
            errors.append(f"{label}: invalid availability")
        if "paid_relationship" in record and (not isinstance(record["paid_relationship"], str) or record["paid_relationship"] not in {"none", "affiliate", "referral", "sponsor", "own"}):
            errors.append(f"{label}: invalid paid_relationship")
        if "ai_specific" in record and type(record["ai_specific"]) is not bool:
            errors.append(f"{label}: ai_specific must be boolean")
        if "kind" in record and kind == "programs" and (not isinstance(record["kind"], str) or record["kind"] not in PROGRAM_KINDS):
            errors.append(f"{label}: invalid program kind")
        if "pin_precision" in record and (not isinstance(record["pin_precision"], str) or record["pin_precision"] not in {"approx", "none"}):
            errors.append(f"{label}: invalid pin_precision")
        for field in ("free_option", "good_first_step", "remote", "online"):
            if field in record and type(record[field]) is not bool:
                errors.append(f"{label}: {field} must be boolean")
        for field in ("cost", "format"):
            if kind in {"programs", "providers"} and (not isinstance(record.get(field), str) or not record[field].strip()):
                errors.append(f"{label}: missing {field}")
        state = record.get("state_id")
        if state is not None and (not isinstance(state, str) or state not in STATE_IDS):
            errors.append(f"{label}: unknown state_id")
        metro = record.get("metro_id")
        if metro is not None and (not isinstance(metro, str) or (metro_centers is not None and metro not in metro_centers)):
            errors.append(f"{label}: unknown metro_id")
        if record.get("lat") is not None or record.get("lng") is not None:
            try:
                lat, lng = float(record["lat"]), float(record["lng"])
                if not math.isfinite(lat) or not math.isfinite(lng) or not (-90 <= lat <= 90 and -180 <= lng <= 180):
                    raise ValueError
                if metro_centers and isinstance(metro, str) and metro in metro_centers:
                    center = metro_centers[metro]
                    if isinstance(center, dict):
                        center = center["center"]
                    if _distance_km((lat, lng), center) > 150:
                        errors.append(f"{label}: coordinates over 150 km from metro")
            except (TypeError, ValueError, KeyError):
                errors.append(f"{label}: invalid coordinates")
        if "host_provider_id" in record and (not isinstance(record["host_provider_id"], str) or not ID_PATTERN.fullmatch(record["host_provider_id"])):
            errors.append(f"{label}: invalid host_provider_id")
        if kind == "events" or "start" in record:
            if not isinstance(record.get("cost"), str) or not record["cost"].strip():
                errors.append(f"{label}: event needs cost (use an honest unknown label if not published)")
            try:
                start = dt.datetime.fromisoformat(record["start"].replace("Z", "+00:00"))
                if "T" not in record["start"]:
                    raise ValueError
            except (AttributeError, KeyError, TypeError, ValueError):
                errors.append(f"{label}: event start needs ISO date-time")
    return errors


def evidence_current(record, today, evidence_dir=None):
    today = _date(today)
    rid = record.get("id", "")
    if not isinstance(rid, str) or not ID_PATTERN.fullmatch(rid):
        return False
    try:
        evidence = json.loads((Path(evidence_dir or EVIDENCE_DIR) / rid / "latest.json").read_text(encoding="utf-8"))
        checked = _date(evidence.get("checked"))
        results = evidence.get("results")
        expected = {s["url"] for s in record["sources"]}
        return bool(today and evidence.get("record_id") == rid and evidence.get("pass") is True
                    and checked and 0 <= (today-checked).days <= 7
                    and evidence.get("sources_sha256") == source_fingerprint(record)
                    and isinstance(results, list) and len(results) == len(expected)
                    and {s.get("url") for s in results} == expected
                    and all(s.get("pass") is True and s.get("status") == 200 and s.get("quote_found") is True
                            and safe_url(s.get("final_url")) and domain(s["final_url"]) == domain(s["url"]) for s in results))
    except (AttributeError, OSError, ValueError, TypeError, KeyError):
        return False


def approved_and_current(record, today):
    today = _date(today)
    if not today or not isinstance(record, dict) or record.get("status") != "approved":
        return False
    kind = "events" if "start" in record else "resources"
    if validate_records([record], today, kind=kind) or not evidence_current(record, today):
        return False
    if record.get("availability") == "no_dates":
        return False
    if "start" in record:
        try:
            # Date-only expiry is deliberate: throughout event day it remains listed.
            if dt.datetime.fromisoformat(record["start"].replace("Z", "+00:00")).date() < today:
                return False
        except (ValueError, TypeError):
            return False
    return True


def visible_records(records, today):
    if not isinstance(records, list):
        return []
    return [record for record in records if approved_and_current(record, today)]


def load_and_validate(records_dir=ROOT / "records", today=None):
    today = today or dt.date.today()
    errors, all_ids = [], set()
    provider_ids, event_hosts = set(), []
    for kind in ("providers", "programs", "events", "resources"):
        try:
            records = json.loads((Path(records_dir) / f"{kind}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            errors.append(f"{kind}: cannot read records: {exc}")
            continue
        errors.extend(validate_records(records, today, kind))
        if isinstance(records, list):
            for record in records:
                if isinstance(record, dict) and isinstance(record.get("id"), str):
                    if record["id"] in all_ids:
                        errors.append(f"cross-file duplicate id {record['id']}")
                    all_ids.add(record["id"])
                    if kind == "providers":
                        provider_ids.add(record["id"])
                    if kind == "events" and isinstance(record.get("host_provider_id"), str):
                        event_hosts.append((record["id"], record["host_provider_id"]))
    for event_id, host_id in event_hosts:
        if host_id not in provider_ids:
            errors.append(f"events/{event_id}: unknown host_provider_id {host_id}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records-dir", type=Path, default=ROOT / "records")
    parser.add_argument("--today", default=dt.date.today().isoformat())
    args = parser.parse_args()
    errors = load_and_validate(args.records_dir, args.today)
    if errors:
        print("\n".join(errors))
        return 1
    print("Record validation passed; candidates are not publication approvals.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
