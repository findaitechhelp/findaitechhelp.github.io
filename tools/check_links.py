"""Fetch declared evidence sources once, verify exact quotes, and fail closed."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html.parser
import ipaddress
import json
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

try:
    from .validate import ROOT, safe_url, domain, source_fingerprint, validate_records
except ImportError:
    from validate import ROOT, safe_url, domain, source_fingerprint, validate_records

MAX_BYTES = 4 * 1024 * 1024


class PageText(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.skip += 1
        elif tag in {"p", "div", "br", "li", "h1", "h2", "h3", "td", "th"}:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"}:
            self.skip = max(0, self.skip - 1)
        else:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def normalize_text(value):
    return " ".join(value.split())


def page_text(raw, content_type="text/html", charset="utf-8"):
    decoded = raw.decode(charset or "utf-8", errors="replace")
    if "html" not in content_type:
        return normalize_text(decoded)
    parser = PageText()
    parser.feed(decoded)
    return normalize_text("".join(parser.parts))


def assert_public_destination(url):
    if not safe_url(url):
        raise ValueError("unsafe source URL")
    host = urlsplit(url).hostname
    # Prevent accidental access to local/private services through a DNS alias.
    addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(entry[4][0]).is_global for entry in addresses):
        raise ValueError("source resolves to a non-public address")


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        assert_public_destination(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_source(source, timeout=15):
    """One fetch, normal redirects only; no auth, retries, or restriction bypass."""
    url = source["url"]
    result = {"url": url, "pass": False, "status": None, "quote_found": False}
    try:
        assert_public_destination(url)
        request = urllib.request.Request(url, headers={
            "User-Agent": "FindAITechHelp-EvidenceChecker/0.1 (local editorial verification)",
            "Accept": "text/html,text/plain;q=0.9",
        })
        opener = urllib.request.build_opener(SafeRedirect())
        with opener.open(request, timeout=timeout) as response:
            result["status"] = response.status
            result["final_url"] = response.url
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError("response exceeds verification size limit")
            content_type = response.headers.get_content_type()
            if content_type not in {"text/html", "text/plain", "application/xhtml+xml"}:
                raise ValueError("source must be readable HTML or plain text")
            text = page_text(raw, content_type, response.headers.get_content_charset())
            quote = normalize_text(source["quote"])
            result["quote_found"] = bool(quote and quote in text)
            result["sha256"] = hashlib.sha256(raw).hexdigest()
            result["domain_unchanged"] = domain(response.url) == domain(url)
            result["pass"] = response.status == 200 and result["quote_found"] and result["domain_unchanged"]
            if not result["domain_unchanged"]:
                result["error"] = "cross-domain redirect requires editorial review of the canonical source"
            if not result["quote_found"]:
                result["error"] = "exact quote not found in fetched page text"
    except (urllib.error.URLError, OSError, ValueError, LookupError) as exc:
        if isinstance(exc, urllib.error.HTTPError):
            result["status"] = exc.code
        result["error"] = str(exc)[:300]
    return result


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def check_record(record, today, kind="programs", evidence_dir=None, fetcher=fetch_source):
    """Write evidence without changing record approval/status."""
    if isinstance(today, str):
        today = dt.date.fromisoformat(today)
    errors = validate_records([record], today, kind)
    results = [] if errors else [fetcher(source) for source in record["sources"]]
    for result in results:
        declared = result.get("url")
        final = result.get("final_url")
        if result.get("pass") is True and (not final or domain(final) != domain(declared)):
            result["pass"] = False
            result["error"] = "missing or changed final source domain; editorial review required"
    evidence = {
        "record_id": record.get("id"), "checked": today.isoformat(),
        "sources_sha256": source_fingerprint(record),
        "pass": not errors and bool(results) and all(result.get("pass") is True for result in results),
        "results": results,
    }
    if errors:
        evidence["validation_errors"] = errors
    # Unsafe IDs must never be used as file paths.
    import re
    rid = record.get("id", "")
    if isinstance(rid, str) and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", rid):
        folder = Path(evidence_dir or ROOT / "evidence") / rid
        atomic_json(folder / (today.isoformat() + ".json"), evidence)
        atomic_json(folder / "latest.json", evidence)
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records-dir", type=Path, default=ROOT / "records")
    parser.add_argument("--evidence-dir", type=Path, default=ROOT / "evidence")
    parser.add_argument("--today", type=dt.date.fromisoformat, default=dt.date.today())
    parser.add_argument("--pause-failures", action="store_true", help="Locally pause approved failed records; never approves anything")
    args = parser.parse_args()
    failed, checked = 0, 0
    checked_sources, retrieval_failures = {}, {}
    def cached_fetch(source):
        # One failed source retrieval per run; do not repeatedly hit a restriction
        # just because several candidates cite the same article.
        url = source["url"]
        key = (url, source["quote"])
        if url in retrieval_failures:
            return dict(retrieval_failures[url])
        if key not in checked_sources:
            result = fetch_source(source)
            checked_sources[key] = dict(result)
            if result.get("status") != 200:
                retrieval_failures[url] = dict(result)
        return dict(checked_sources[key])
    for kind in ("providers", "programs", "events", "resources"):
        path = args.records_dir / (kind + ".json")
        try:
            records = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"FAIL {kind}: {exc}")
            failed += 1
            continue
        if not isinstance(records, list):
            print(f"FAIL {kind}: expected a list")
            failed += 1
            continue
        changed = False
        for record in records:
            if not isinstance(record, dict):
                print(f"FAIL {kind}: malformed record")
                failed += 1
                continue
            evidence = check_record(record, args.today, kind, args.evidence_dir, fetcher=cached_fetch)
            checked += 1
            print(f"{'PASS' if evidence['pass'] else 'FAIL'} {record.get('id', '(invalid id)')}")
            if not evidence["pass"]:
                failed += 1
                if args.pause_failures and record.get("status") == "approved":
                    record["status"] = "paused"
                    record["pause_reason"] = "Evidence source/quote check failed"
                    changed = True
        if changed:
            atomic_json(path, records)
    print(f"Checked {checked} records; {failed} failure(s). No records were approved.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
