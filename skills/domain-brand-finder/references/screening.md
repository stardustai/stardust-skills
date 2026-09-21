# Domain acquisition and US preliminary screening

## Domain registry observations

Resolve registry endpoints using IANA bootstrap; use documented registry sources for unsupported cases. Normalize the full domain, not just the candidate stem. Cache by exact normalized domain with timestamp and evidence. Legacy CSV yes/no rows and old explanations are not current evidence. Cached registry facts must never overwrite the current candidate's meaning or score.

Statuses: REGISTERED, NO_REGISTRY_RECORD, UNKNOWN, UNSUPPORTED. A valid RDAP 404 establishes only that no registry record was returned. Validate endpoint behavior with a known registered positive control for the relevant TLD. Errors, rate limits, malformed responses, failed controls and unsupported lookups do not establish absence. Preserve separate evidence for every checked suffix. Retry sparingly; obey access restrictions.

## Acquisition evidence

Prefer an authorized documented registrar API when available, otherwise the visible registrar/marketplace UI. Require the **exact domain** with a current purchasable registration result or a publicly posted fixed sale price. Record:

- domain, provider, source URL, observation timestamp and retained receipt;
- status AVAILABLE_REGISTRATION or FIXED_PRICE_SALE;
- currency, minimum compulsory registration years, initial total, annual renewal;
- relevant taxes/fees or uncertainty, and any premium-renewal condition.

One qualifying primary domain is enough if the brief says so. The budget covers its initial acquisition including compulsory minimum term; disclose renewal separately. Do not silently assume currency conversion or accept extraordinary recurring costs. Generic TLD pricing is not an exact-domain quote. Exact availability and a separate applicable registrar renewal/term page may together support a quote if their applicability is explicit and both receipts are retained.

Inquiry, “may be for sale”, auction estimates, RDAP absence and unsupported valuations fail the acquisition gate. Do not add to cart, buy, contact a seller or negotiate. A screenshot is a point-in-time observation, not a guarantee that the domain will remain purchasable. Refresh final status/quote within the project's freshness window (default 24h).

## US trademark search

Follow USPTO's current [federal searching guidance](https://www.uspto.gov/trademarks/search/federal-trademark-searching) and distinguish it from [comprehensive clearance](https://www.uspto.gov/trademarks/search/comprehensive-clearance-search-similar-trademarks). Search is about similarities in appearance, sound, meaning and overall commercial impression **and** related goods/services, not just exact matches or class numbers.

Prepare for each name:

- exact name across classes, segmented/contained forms;
- plausible spelling and near-sound variants with reasons (do not pretend an arbitrary edit-distance list covers phonetics);
- relevant semantic equivalents where meaningful, or a reasoned not-applicable record;
- priority class 9/42 searches informed by the actual software/services, without excluding related other-class records.

Retain queries, query shape, counts, completeness, time and official source/record links. For every relevant application/registration preserve serial, owner, live/dead status, full goods/services and context. Dead marks can still signal ongoing public use; live status alone does not establish a conflict.

For an automated endpoint, validate each query form with a meaningful known-positive control. Verify returned structure, matching semantics and total versus returned records. A response cap is not an exhaustive search. Failed controls, 403/429, truncated results, missing data or unclear semantics must remain UNKNOWN. Do not bypass access controls, forge sessions or claim a search engine index is the full federal database.

The receipt tool never grants legal clearance. The principal reviewer reads the relevant results and assigns a scoped preliminary disposition, explaining similarities and goods/services relevance. Mark issues needing professional judgment REVIEW; do not declare “safe” merely because the count is zero. Descriptiveness and other registrability concerns also deserve explicit review. Company size or funding is not a reason to ignore adverse evidence.

Offset pagination uses the official UI's ascending serial/id sort and retains the exact request payload for each page. Check stable exact totals, expected page sizes and unique nonblank serials. A record-level metadata omission must not hide later otherwise valid pages: collect the bounded remaining evidence, identify each omitted field by page/index/serial, and keep the aggregate INCOMPLETE. Missing/blank serials cannot count as unique records. Transport, rate-limit, shard, changing-total or duplicate-page failures still stop the query. A documented manual interpretation can close one specific data gap without rewriting the automated receipt or changing the general parser rule.

Goods/services and both owner-name and owner-history fields must contain nonempty arrays of nonblank strings; an empty list is not complete evidence. Preserve all returned owner/history values without assuming the first listed owner is current. Apply improved validation to retained records offline and record any changed completeness assessment separately; never rewrite historical raw receipts or silently grandfather a previous pass. A non-registration insignia record or design mark may need a specific documented interpretation instead of invented goods or text.

Passing does not require zero search results. A shared weak element, unrelated goods, a different overall name, or a developer handle is not automatically a conflict; explain the actual relation. Conversely, a descriptive suffix may not distinguish a name whose dominant element already identifies directly related software. A material adverse finding can justify rejection before every query is complete; preserve the incomplete remainder rather than calling the entire search complete. A null literal-wordmark field can belong to a design or non-Latin mark: retain the source and inspect official imagery/transliteration where relevant, never invent the missing name or convert it to zero results. Automated UNKNOWN remains until the recorded manual review closes the specific data/coverage gap.

## Public use and search crowding

Check exact and plausible near names in AI/Agent products, adjacent enterprise/consumer software appropriate to the brief, and relevant app stores and developer ecosystems. Record query, major observed entity, product/use, URL/date, and concern. Search-engine site queries have incomplete catalog coverage; say which native catalogs were actually accessed and which were not. Do not equate no indexed result with no common-law rights. Search crowding is an observation, not a promise to own search results in 6–12 months.

For native catalogs and public developer APIs, retain the actual request URL/parameters, time, HTTP status, full returned response and query-specific totals/limits, not just a summary of exact-name matches. Inspect the returned neighboring names too. Preserve the actual known control item and its identity; a broad control query returning many unrelated hits is not a verified control. Candidate-result truncation or missing source receipts remains UNKNOWN until a documented supplement closes it. If old responses were not retained, recapture with a new time instead of inventing an old raw receipt. For browser-only checks, retain a reproducible visible-state transcript or screenshot, the query/storefront and all returned identity rows; distinguish that from a raw HTTP body. A song title, artist/studio, developer handle and marketed software product are different uses: record their actual scope before judging their relevance.

For npm text searches, the optional `public_catalog_capture.py` helper retains bounded pages and a known-item control; see [commands](data-contract.md). Stop the entire provider sequence at the first access-limit response, not merely the current page. Do not issue remaining pages, another candidate query, or a control after that failure. Preserve the unseen remainder as unknown. Offline regression success does not establish that live access has recovered.

## Review status contract

| Status | Meaning | Formal candidate allowed? |
|---|---|---|
| NOT_CHECKED | No check performed | No |
| UNKNOWN | Failed/incomplete query, control or evidence | No |
| CONFLICT | Material conflicting use found in scope | No |
| REVIEW | Results exist but require further judgment | No |
| PASS_SCREEN | No disqualifying issue found in the agreed, completed preliminary scope | Yes, if other gates pass |

US-only never implies EU/UK coverage. Default screening freshness is 48h at delivery. PASS_SCREEN remains preliminary: full US legal clearance includes other sources and common-law use, and should be professionally reviewed before final adoption. Never label this agent work privileged or imply a lawyer-client relationship.
