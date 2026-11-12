# Find AI Tech Help

Local review implementation for FindAITechHelp.com, operated by VirtualEcommerce Inc.
This repository is **not launch-ready**. Only Dan approves directory entries, legal text, and public launch.

## Preview on Windows

From this folder, run `./Preview-Website.ps1`, or:

```powershell
python build.py
python tools/preview.py --port 8765
```

Open http://127.0.0.1:8765. The server binds only to loopback and serves only `dist/`.
Stop it with Ctrl+C. A missing route returns the real 404 page with HTTP 404.

## Checks

```powershell
python tools/validate.py --today 2026-11-12
python -m unittest discover tests -v
python build.py --today 2026-11-12
python tools/check_site.py
node --check site/assets/site.js
```

Normal builds are nonindexable review output. `python build.py --release` intentionally fails while launch blockers remain; no bypass flag exists. Same inputs and `--today` produce identical output. Existing output is swapped only after generation, and previous outputs are retained locally beside the target in `.build-history/`.

## Structure

- `site/build.py`, `site/pages.py`, `site/content.py`: orchestration and original editorial guidance.
- `site/templates/`, `site/assets/`: HTML and local CSS/JavaScript/SVG assets.
- `site/legal-original.json`: exact original draft privacy, terms, and disclosure bodies; no replacement legal text approved.
- `records/`: publication-pipeline inputs. Currently empty, deliberately.
- `tools/validate.py`, `tools/check_links.py`: provenance, approval binding, source checks and publication eligibility.
- `tests/`: adversarial validation, evidence, deterministic build, link and isolation checks.
- `tools/review_queue.py`: private queue from preserved legacy files and national research. Legacy inputs/research/queue are deliberately excluded from the public repository; run in the owning workspace.
- `vercel.json`, `.github/workflows/ci.yml`: staged build configuration only; not deployed or connected to an active project.

## Publication safeguards

A record needs source quotes from an official site and a genuinely independent non-directory second site. Successful source checks do not approve a listing. After Dan explicitly approves the exact record, its `approved_by`, `approved_on`, and `approval_fingerprint` bind approval to the facts and sources. Edited facts invalidate approval. Candidates, failed/missing evidence, evidence older than seven days, stale records, and past events cannot be rendered by a fresh build.

These are **build-time** checks. Before launch, scheduled source checking, rebuild delivery, and withdrawal of stale deployed output must be implemented and verified on the selected host. No production scheduler or withdrawal mechanism is currently connected. Release is blocked until that verification, legal approval, content coverage, and Dan's launch approval are recorded.

Do not push internal planning, business/tax documents, unapproved candidate datasets, private source evidence, `.env`, or keys. The existing GitHub remote is public. Source publishing requires a separate review/approval; nothing was pushed during this build.

Local Git hooks are installed through `core.hooksPath=.githooks`: pre-commit runs review checks; pre-push runs source checks and the release gate. Public approval remains a separate requirement.
