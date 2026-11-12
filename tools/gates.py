"""Publication gates for real, approved state and city coverage.

The caller supplies records scoped to one city and a distinct local introduction.
State records are additionally filtered by state_id here. Empty preview pages
must remain noindex. This module neither approves records nor changes thresholds.
"""
from __future__ import annotations

import datetime as dt
import re

try:
    from .validate import CATEGORIES, STATE_IDS, approved_and_current
except ImportError:
    from validate import CATEGORIES, STATE_IDS, approved_and_current


def _today(value):
    if value is None:
        return dt.date.today()
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    try:
        return dt.date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _intro_ready(intro):
    # Cross-page uniqueness must be checked where the set of pages is known.
    return isinstance(intro, str) and bool(intro.strip()) and not re.search(r"\[[^\]]*\]", intro)


def _eligible_unique(records, today):
    if not isinstance(records, list) or today is None:
        return []
    result, seen = [], set()
    for record in records:
        if not isinstance(record, dict):
            continue
        rid = record.get("id")
        name = record.get("name")
        if not isinstance(rid, str) or not rid or rid in seen or not isinstance(name, str) or not name.strip():
            continue
        if approved_and_current(record, today):
            result.append(record)
            seen.add(rid)
    return result


def _free_program(record):
    cost = record.get("cost")
    free = record.get("free_option") is True or (isinstance(cost, str) and cost.strip().casefold() in {"free", "$0", "0", "no cost"})
    # Free repair estimates alone are not a named learning/mentoring program.
    learning = record.get("category") == "ai-training" or isinstance(record.get("kind"), str)
    ai_confirmed = record.get("ai_specific") is True or (record.get("category") == "ai-training" and record.get("ai_specific") is not False)
    return free and learning and ai_confirmed


def _current_event(record, today):
    value = record.get("start")
    if not isinstance(value, str) or "T" not in value:
        return False
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).date() >= today
    except ValueError:
        return False


def city_gate(records, events, *, intro="", today=None):
    """Ten distinct eligible providers plus a current event or free program."""
    today = _today(today)
    if not today or not _intro_ready(intro) or not isinstance(records, list) or not isinstance(events, list):
        return False
    local = _eligible_unique(records, today)
    providers = [row for row in local if isinstance(row.get("category"), str) and row["category"] in CATEGORIES and "start" not in row]
    # A second ID for the same named provider is not another local option.
    identities = {str(row.get("provider_id") or row["name"]).strip().casefold() for row in providers}
    if len(identities) < 10:
        return False
    provider_ids = {row["id"] for row in providers}
    dated = [row for row in _eligible_unique(events, today) if row["id"] not in provider_ids and _current_event(row, today)]
    return bool(dated or any(_free_program(row) for row in local))


def _explicit_no_ai_offering(record, today):
    value = record.get("ai_offering_note")
    if not isinstance(value, str):
        return False
    match = re.fullmatch(r"\s*none found,?\s+checked\s+(\d{4}-\d{2}-\d{2})\.?\s*", value, flags=re.IGNORECASE)
    if not match:
        return False
    checked = _today(match.group(1))
    return checked is not None and 0 <= (today - checked).days <= 120


def state_gate(records, *, state_id, intro="", today=None):
    """Eight local records, three AI-specific items with named hosts, and the SBDC lead center."""
    today = _today(today)
    if not today or not isinstance(state_id, str) or state_id not in STATE_IDS or not _intro_ready(intro):
        return False
    local = [row for row in _eligible_unique(records, today) if row.get("state_id") == state_id]
    if len(local) < 8 or sum(row.get("ai_specific") is True and bool(row.get("host_name") or row.get("category") in CATEGORIES or row.get("kind") == "sbdc") for row in local) < 3:
        return False
    return any(row.get("kind") == "sbdc" and row.get("lead_center") is True
               and (row.get("ai_specific") is True or _explicit_no_ai_offering(row, today))
               for row in local)
