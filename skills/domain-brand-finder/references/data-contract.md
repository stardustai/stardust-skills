# Structured evidence and executable commands

Run scripts with Python 3.10+ and `requests`; tests also need `pytest`. Paths below are relative to the skill directory. Do not treat examples or test fixtures as real availability evidence.

## Final delivery validator

The pre-screen creative plan/comparison uses [creative-round.md](../assets/creative-round.md); it is not a partially filled formal evidence package. Keep pool membership, row counts, actual operations, names-first reactions and user decisions there. Do not fabricate scores, domains or receipts to run the validator on creative drafts. Later promotion retains that provenance and adds the existing formal fields below.

Configure `assets/project.example.json` for the actual brief. The validator takes four JSON files, not CSV and not JSONL:

```sh
python3 scripts/validate_delivery.py --project /absolute/run/project.json \
  --candidates /absolute/run/candidates.json --checks /absolute/run/checks.json \
  --quotes /absolute/run/quotes.json --evidence-root /absolute/run \
  --output /absolute/run/delivery-validation.json
```

Output is created exclusively: choose a new revision filename on rerun. Exit 0 means configured counts and supplied evidence fields pass; exit 2 means incomplete. Malformed input is an error, not a pass. The validator cannot read a lawyer's mind or establish the semantic truth of a receipt; the principal reviewer must inspect supporting files.

### project.json (object)

Required: `rubric_version`, `weights` (dimension → maximum, total 100), `threshold`, `routes` (route → required count), `markets`, `currency`, `domain_budget`, `quote_max_age_hours`, `screen_max_age_hours`, `required_checks`. Optional `family_modules` lists every required family combination. Brief, exclusions and route descriptions can be stored alongside these fields. Freeze settings before scoring.

This executable validator certifies only the **full v3 preliminary package**: exact v3 dimension keys/weights, threshold 90–100, nonempty market scope, and both us_trademark/public_use gates. Creative-only, keyword-only and domains-only outputs do not call this full-delivery validator. A future rubric needs an explicit implementation/version change; relabeling arbitrary weights as v3 is rejected. When `reviewer` is configured, the card must name that principal. Set `require_names_first_timestamps: true` (as both templates do); cards then need timezone-aware `first_impression_recorded_at` strictly before `source_reviewed_at`, neither in the future. These timestamps document a claimed order; retain the actual names-only and review notes too.

### candidates.json (array)

Each card needs `name`, `route`, `operation`, `source_kind`, `origin`, `first_impression`, `pronunciation`, `fit`, `generator`, `primary_domain`, `family` (module → actual combination), and `review`:

`route` is the project's **perceptual/brand route** used by the existing final `routes` counts. It is not the creative-pattern row. When promoting a creative card, retain a separate `primary_creative_row` (for example `T1` or the project's approved row ID) and `creative_plan_ref` pointing to that round's plan/approval record. These are provenance metadata, not new validated gates. The current validator does **not** check creative-row quotas or source-pool membership; review those against `creative-round.md`. Do not replace `route`/`routes` with the creative rows or invent retrospective row assignments for historical cards.

```json
{
  "reviewer": "independent principal reviewer",
  "rubric_version": "v3",
  "scores": {"first_impression": 0, "distinctiveness": 0, "meaning_fit": 0,
    "english_transmission": 0, "family_extension": 0, "visual_narrative": 0},
  "reasons": {"first_impression": "reason and deduction", "distinctiveness": "reason and deduction",
    "meaning_fit": "reason and deduction", "english_transmission": "desk prediction and deduction",
    "family_extension": "tested combinations and deduction", "visual_narrative": "reason and deduction"},
  "human_test": "NOT_DONE",
  "legal_clearance": "NOT_DONE"
}
```

The zero values are placeholders, not recommended scores. Reviewer and generator must differ. Duplicate names cannot fill multiple routes. Sources may be supplied in additional fields such as `source_urls`, `attested_meaning`, `creative_association`, and `first_impression_recorded_at`.

### checks.json (array)

Exactly one current record for each name × required check × market. Keep historical receipts elsewhere.

- `name`, `kind` (`us_trademark` / `public_use` as configured), `market`
- `status`: NOT_CHECKED / UNKNOWN / CONFLICT / REVIEW / PASS_SCREEN
- `coverage_complete`: boolean, about the agreed preliminary scope, not global/legal exhaustiveness
- `reviewer`, `checked_at` (timezone-aware ISO timestamp), `source_url`, `observation`
- `receipt_files`: nonempty list of nonempty evidence files relative to evidence root
- Recommended additions: query list, scope statement, variant rationale, completeness/control decisions, relevant record links, full goods/services, major public users, unsearched sources, reasons.

Automated USPTO receipts are **not** this reviewer-authored record. Do not transform COMPLETE transport/query status into PASS_SCREEN without substantive review.

### quotes.json (array)

One exact quote for the candidate's `primary_domain`:

- `domain`, `status` (AVAILABLE_REGISTRATION / FIXED_PRICE_SALE)
- `provider`, `currency`, `initial_total`, `minimum_years`, `renewal_per_year`
- `checked_at`, `source_url`, `observation`, `receipt_files`

Numbers must be finite; compulsory term and renewal cannot be omitted. Quote currency must match the configured currency; if conversion is required, establish and document it first. No future timestamps or stale evidence. Receipt paths must stay inside the evidence root.

## Tests

```sh
python3 -m pytest tests -q
```

`tests/test_delivery_gate.py` contains an executable synthetic complete card and rejection cases. Those `.test` domains and example receipts are deliberately fictional. Unit tests verify behavior under controlled input; separately perform online positive-control checks before real execution.

## Registry scanner (not a purchase checker)

Input CSV requires `candidate`, a single ASCII DNS label, without a suffix. Optional columns: `theme`, `brand_score_10` (historical/current caller metadata only), `what_works`, `concern`, `root_a`, `root_b`, `seed_meaning`. For domains-only, split the requested exact domain into its label and explicit suffix; do not scan default extra TLDs. Do not silently strip spaces from a brand spelling: record the chosen domain spelling explicitly.

If an exact-domain request mixes suffixes, group inputs by the requested suffix and run each group with only that `--tlds` value. Feeding all labels and all suffixes together forms a Cartesian product and would exceed that request's scope. This scanner accepts ASCII DNS labels; explicitly convert a user-authorized internationalized domain to its ASCII form or use an appropriate registrar UI, rather than silently changing the brand name.

```sh
python3 scripts/brand_domain_scan.py --input /absolute/run/domain-input.csv \
  --output-all /absolute/run/domain-all.csv --output-shortlist /absolute/run/domain-leads.csv \
  --output-evidence /absolute/run/domain-registry.jsonl \
  --cache-jsonl /absolute/run/registry-cache.jsonl --cache-ttl-hours 24 \
  --tlds ai,com,io,dev,chat,tech --workers 3
```

Use `--ignore-history` for final live refresh. `--controls-json` can provide an object mapping each suffix to a known registered domain. Never regard `domain-leads.csv` as a legally/creatively qualified brand shortlist. The legacy `是否available` values pending/no/unknown are registry leads, **not** acquisition evidence; registered aftermarket domains may still have a separate qualifying fixed-price quote.

## npm public-catalog receipts

Use this optional helper only for the planned npm text-search portion of a public-use screen. Do not run it while that provider is rate-limited or access is blocked, and do not wrap it in an automatic retry or multi-query loop that continues after failure.

```sh
python3 scripts/public_catalog_capture.py --query 'Exact Spaced Name' \
  --output-dir /absolute/run/npm-exact-spaced-name-v1 --max-pages 25
```

The output directory must not already exist. The exact query, request parameters, timestamps, raw bodies and response-header pairs are retained. Candidate pages need stable totals, expected row counts and unique package identities; a configured cap, malformed page or any non-200 response stops before another page or control. Redirects and automatic retries are disabled. A successful candidate capture is followed by a first-page React identity control, whose row count and unique identities are also checked. This control establishes response behavior, not exhaustive coverage of all React-related packages.

Exit 0 / `RECEIPT_CAPTURED` means only that these bounded API receipts were captured consistently; the reviewer still must read the returned neighbors. It is **never** public-use `PASS_SCREEN`. Offset pagination has no atomic snapshot token: stable totals and unique rows do not prove the ordering remained unchanged between calls. Exit 2 or `INCOMPLETE` preserves the gap. A failed control can coexist with candidate `pagination_status=COMPLETE`; the overall capture still fails. `Retry-After` is evidence, not an instruction to retry immediately; a Cloudflare cookie expiry is not a promised rate-limit reset. Apply this distinction when integrating the receipt with reviewer-authored `checks.json`.

## US query receipts

Input is an object with `candidates`, each containing `name`, `variants` (explicit spellings/near sounds/segmented forms) and `meanings` (explicit relevant semantic terms). Supply reasons in a separate search-plan note. Empty variants/meanings are recorded as missing coverage; if there is genuinely no applicable meaning, a reviewer must separately document that reasoning, not pretend the tool checked it.

```sh
python3 scripts/us_trademark_screen.py --preflight-only \
  --output /absolute/run/us-preflight.jsonl
python3 scripts/us_trademark_screen.py --input /absolute/run/us-search-plan.json \
  --output /absolute/run/us-query-receipts.jsonl
```

This read-only helper reuses the public USPTO search route. Its reachability and query forms can change: run positive controls, inspect full receipts, and use the official UI when an authorized query cannot be verified. The tool records COMPLETE / INCOMPLETE / UNKNOWN query evidence, not PASS_SCREEN legal judgments. Queries paginate in 400-record pages, retaining each page's raw JSON, HTTP body, timestamp and offset. COMPLETE requires stable exact totals, expected page lengths, valid source fields and unique serial numbers totaling the reported count. The safe cap is 25 pages / 10,000 results; larger queries, changed totals, duplicate results, failed shards or truncated pages stay INCOMPLETE. Stop on access limits and do not silently rerun around them. Output is a new JSONL file with controls and candidate records; retain it alongside reviewer-authored checks.json.

Current automation boundary: one-word queries use an EVOLIA registered positive control; two-word phrase and component-AND queries use STAR TREK. Three-or-more-word queries and multiword fuzzy queries are UNKNOWN and are not issued, because this implementation has no validated same-shape control for them. Use explicit, justified near-spelling/near-sound variants and an authorized manual search to close these gaps; do not drop a failed channel to claim complete coverage. Quoted text queries may return longer marks containing that phrase: inspect results, do not assume an anchored exact match. Raw JSON payloads and raw HTTP response text are retained, including malformed/error responses.

CLI exit 2 means input/output failure, any incomplete/unknown query, empty input, or missing explicit variant/meaning coverage. Receipts already written remain available to inspect. Exit 0 means only that supplied query receipts were complete with supplied variants/meanings; it is never a trademark clearance verdict.

The optional generator CLI is `python3 scripts/generate_brand_candidates.py --output /absolute/run/raw-ideas.csv --limit 100`. It is a narrow morphology generator, not cross-method exploration; `generation_priority` only orders ideas and `brand_score_10` remains blank.

Check each script's `--help` before invoking, then preserve the actual command and output in the round ledger. Registry and US JSONL belong beside, not inside, the compact comparison CSV.
