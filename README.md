# Find AI Tech Help

Public review implementation for FindAITechHelp.com, operated by VirtualEcommerce Inc.
This repository is **not launch-ready**. Only Dan approves directory entries, legal text, and public launch.

The current owner-approved visual design uses a navy/gold map-led hero, illustrated raised listing cards, native expandable details and a shared theme across all routes. Ambient motion has a Pause control and follows reduced-motion preferences. Local and nationwide listings remain separate, with verified free options first. Original SVG artwork is decorative rather than provider photography or logos.

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

Normal builds are nonindexable review output. `python build.py --release` intentionally fails while launch blockers remain; the public review mode remains noindex and omits unfinished legal drafts. Same inputs and `--today` produce identical output. Existing output is swapped only after generation, and previous outputs are retained locally beside the target in `.build-history/`.

## Structure

- `site/build.py`, `site/pages.py`, `site/content.py`: orchestration and original editorial guidance.
- `site/templates/`, `site/assets/`: HTML and local CSS/JavaScript/SVG assets.
- `site/legal-original.json`: exact original draft privacy, terms, and disclosure bodies; no replacement legal text approved.
- `records/`: publication-pipeline inputs. Source-checked local/state resources and nationwide programs approved under Dan’s conditional authorization.
- `tools/validate.py`, `tools/check_links.py`: provenance, approval binding, source checks and publication eligibility.
- `tests/`: adversarial validation, evidence, deterministic build, link and isolation checks.
- `tools/review_queue.py`: private queue from preserved legacy files and national research. Legacy inputs/research/queue are deliberately excluded from the public repository; run in the owning workspace.
- `vercel.json`, `.github/workflows/ci.yml`: public review build configuration.

## Publication safeguards

A record needs source quotes from an official site and a genuinely independent non-directory second site. Successful source checks do not approve a listing. After Dan explicitly approves the exact record, its `approved_by`, `approved_on`, and `approval_fingerprint` bind approval to the facts and sources. Edited facts invalidate approval. Candidates, failed/missing evidence, evidence older than seven days, stale records, and past events cannot be rendered by a fresh build.

These are **build-time** checks. Before launch, scheduled source checking, rebuild delivery, and withdrawal of stale deployed output must be implemented and verified on the selected host. No production scheduler or withdrawal mechanism is currently connected. Release is blocked until that verification, legal approval, content coverage, and Dan's launch approval are recorded.

Do not push internal planning, business/tax documents, unapproved candidate datasets, private source evidence, `.env`, or keys. The existing GitHub remote is public. Source publishing requires a separate review/approval; Dan authorized publication on November 12, 2026.

Local Git hooks are installed through `core.hooksPath=.githooks`: pre-commit runs review checks; pre-push checks the explicitly configured public review mode, or source checks and the strict release gate for a full launch. Public approval remains a separate requirement.

Public review uses `python build.py --public-review`. Sanitized source-verification receipts are bundled in `site/verified-evidence/`; failed local checks override them. Receipts expire after seven days on subsequent builds. There is no verified automatic withdrawal of already deployed pages yet.

## Cloudflare Pages review hosting

The live review site is [www.findaitechhelp.com](https://www.findaitechhelp.com/), hosted by the dedicated Find AI Tech Help Cloudflare account through the Git-integrated Pages project `findaitechhelp`. The fallback address is [findaitechhelp.pages.dev](https://findaitechhelp.pages.dev/). Domain registration, authoritative DNS, and existing email forwarding remain in the owner's original domain account. The apex redirects to HTTPS www while preserving paths and query strings; www uses a DNS-only CNAME to the Pages project. No domain or email transfer is required. Review indexing and full-launch safeguards below still apply.

Use the authorized dedicated Cloudflare account and the existing repository. For a Git-integrated Pages project, choose no framework, build command `python3 tools/build_cloudflare.py`, output directory `dist`, and `PYTHON_VERSION=3.13`. The repository root is this folder (the current GitHub repository has `build.py` at its root). Select only the explicitly approved deployment branch; account/domain moves and deployment remain separate owner actions.

The Cloudflare build command validates the origin first, runs record validation and all unit tests, then builds and checks the exact public-review output. Any failure exits nonzero and stops deployment; it does not depend on a separate GitHub Actions run finishing first. The existing Vercel build command remains compatible.

Set `PUBLIC_SITE_ORIGIN` in both production and preview build environments to the verified HTTPS origin visitors should receive in emailed plans (the assigned Pages URL, then the custom domain only after it works). It accepts a public DNS origin, with an optional root slash or port 443, and rejects credentials, other ports, paths, queries and fragments. Invalid configuration fails the build. Cloudflare deployments (`CF_PAGES` set) require this explicit value. Outside Cloudflare, when absent, email links keep the existing Vercel preview origin in public-review mode and `https://findaitechhelp.com` otherwise. Tests isolate their default-origin fixtures without erasing the production origin used for the final build. This setting changes share links only; canonical/schema URLs, URL paths and indexing gates are preserved.

The generated `dist/_headers` supplies security headers, asset caching and `X-Robots-Tag: noindex, follow` for review builds. A future authorized release omits that global noindex header while retaining each page's indexing gate. `dist/_redirects` preserves the two legacy city redirects. The root `dist/404.html` makes Pages return a genuine missing-page response instead of its SPA fallback. Do not add a catch-all rewrite to the home page. Deploy only `dist`, with no Pages Functions or Worker interception.

These are local build contracts, not proof of live hosting behavior. After deployment verify the home, directory and finder return 200, both legacy paths redirect, an unknown route and omitted legal routes return 404, and review HTML/assets/404 responses carry noindex and the security headers. Verify an emailed plan uses the intended origin and all 203 currently eligible entries remain present. Cloudflare references: [build configuration](https://developers.cloudflare.com/pages/configuration/build-configuration/), [headers](https://developers.cloudflare.com/pages/configuration/headers/), and [serving pages](https://developers.cloudflare.com/pages/configuration/serving-pages/).


City-marker coordinates are representative geographic points from the [2026 U.S. Census Gazetteer](https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html), not provider addresses. State outlines are US Atlas Census-derived geometry. The mathematical Albers projection matches the [US Atlas configuration](https://github.com/topojson/us-atlas) and [D3 geographic projection parameters](https://github.com/d3/d3-geo/tree/main/src/projection). The default map is local and requires no external tile requests. Optional road/radius mode uses self-hosted Leaflet 1.9.4 and requests OpenStreetMap tiles only after a visitor explicitly chooses that mode, with adjacent IP/viewed-area disclosure and visible attribution. Radius distances are straight-line city-center exploration distances, not provider service areas or travel times. OpenStreetMap's public tile service is best effort and must follow its [tile policy](https://operations.osmfoundation.org/policies/tiles/); no prefetch or offline download feature is provided. A tile failure returns visitors to the local map without automatic retries. Licenses are in `site/assets/vendor/`.

All shared assets contribute to a deterministic cache fingerprint. Mapping CSS/JavaScript are included only on the two explorer routes; all pages and listing facts remain statically rendered, and the original draft legal pages remain excluded from public-review output. Do not treat the visual release as approval of the separate full search/legal launch gates.


The national explorer supports state/city selection, Census city dots, topic search, AI/general/free filters and separate classes, AI consulting, IT support and computer-repair choices, and progressive result pagination. All entries remain in static HTML for no-JavaScript access. `build-report.json` reports actual coverage against the 50 most populous incorporated places in Census Vintage2025 estimates; this measures geographic breadth, not depth of AI offerings or provider quality.
