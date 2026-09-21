# Semantic relatedness for software-mark screening

This reference prevents a registry class or the word “software” from becoming a substitute for a related-goods/services analysis. It is a preliminary naming-screening aid, not legal advice or a clearance opinion.

## What to compare

For each exact or near mark, quote the relevant goods/services and fill these fields:

| Field | Question |
|---|---|
| Product task | What job does the product perform? Is it an assistant, workflow tool, security control, medical tool, game, infrastructure tool, or something else? |
| User/buyer | Who uses it, who pays, and who approves procurement? |
| Channel/context | How is it sold or discovered: enterprise sales, app store, developer ecosystem, hardware bundle, specialist channel, or consumer retail? |
| Commercial impression | Would an ordinary buyer see the two offerings as a common product family, source, extension, or merely the same word? |
| Mark/status | Exact, contained, phonetic, or meaning relation; live, pending, registered, dead, or unknown. |
| Completeness | Were all-class exact, relevant goods/services, variants, public-use and controls captured? |

Do not collapse these fields into a class number. IC 009/042 is a search boundary and a useful control, not a product taxonomy.

## Disposition matrix

| Pattern | Default status | Required explanation |
|---|---|---|
| Same assistant/agent/copilot or the same enterprise workflow, **plus** a credible buyer/channel or commercial-impression bridge | `CONFLICT` (human/legal gate before project `KILL`) | Quote the task, buyer, channel and commercial-impression bridge. A shared channel alone is not enough. |
| Exact/near mark in a distinct job and vertical, with no observed bridge | `REVIEW` or `REVIEW-HIGH` | State the distinction and retain exact-mark, crowding, status and public-use uncertainty. |
| Traditional software that serves the same workflow/buyer/channel | `CONFLICT` even without AI language | Explain the functional adjacency; “non-AI” is not a safe harbor. |
| AI in an unrelated job (home security, medical imaging, games, wearables) | `REVIEW`, not automatic conflict and not automatic pass | AI is a signal; compare the job and market context. |
| Keyword-only/class-only hit, incomplete goods, failed positive control, or truncated response | `MACHINE-HOLD` / `UNKNOWN` | Preserve the failed or missing evidence and do not report zero conflicts. |
| No material relatedness after complete preliminary checks | `PASS_SCREEN` only if the frozen project rubric allows it | Keep the receipts and state that this is not legal clearance. |

`MACHINE-HOLD` is the safe intermediate state for automation. A reviewer may move it to `REVIEW` or `CONFLICT` after reading the evidence; the reviewer must not silently turn it into `PASS_SCREEN`.

## AI versus traditional software

Use the product’s job, not its marketing adjective:

- AI virtual assistant, executive agent, workflow copilot, knowledge worker, scheduling or business-administration helper: usually a direct/high-risk comparison for an enterprise execution agent.
- AI home-security, medical-image, industrial-control, game, or wearable product: usually a distinct-vertical review unless buyers, channels, integrations, or overall commercial impression bridge the gap.
- Traditional document management, collaboration, calendar, workflow, or enterprise data software: can be highly related even when no AI appears in the description; inspect the buyer and workflow adjacency.
- A shared word or class without a credible task/buyer/channel bridge: do not call it a conflict solely because both records say “software.”

These are defaults for triage, not legal conclusions. Preserve contrary evidence and escalate ambiguous high-impact cases.

## Example boundary set

For a proposed enterprise AI execution/learning agent using an exact mark such as `COVE`:

1. A registered AI virtual-assistant/workflow/project-management SaaS record is a direct/high-risk overlap: `CONFLICT` and do not retain as a normal candidate.
2. A registered home-security or home-automation software record is a distinct job and vertical: `REVIEW` (possibly `REVIEW-HIGH` for an exact crowded mark), not an automatic `KILL`.
3. A registered secure document-management platform sold to financial institutions is a boundary case: traditional software can overlap through enterprise buyers, procurement channels and workflow adjacency; retain only as explicit high-risk review, never as “safe because it is not AI.”

The examples illustrate the reasoning dimensions. They do not decide any particular mark or replace attorney review.

## Candidate rescue report fields

When revisiting a machine `KILL`, use one row per record or a clearly bounded record set:

```text
candidate:
machine_disposition:
new_triage: REVIEW | REVIEW-HIGH | CONFLICT | UNKNOWN
mark_relation:
product_task:
buyers:
channels:
commercial_impression:
status_and_goods:
missing_checks:
rescue_boundary: removed automatic KILL only; not cleared or shortlist-ready
source_receipts:
```

If multiple records point in different directions, keep both: a distinct-vertical record may justify `REVIEW`, while one direct assistant/workflow record may justify `CONFLICT`. Do not average them into a reassuring count.

## Common failure modes

- `exact + IC 042 = KILL`: wrong because the class does not identify the task or market.
- `not AI = safe`: wrong because traditional workflow/document/collaboration software can be related.
- `different vertical = zero risk`: wrong when buyers, channels, integrations or commercial impression overlap.
- `no direct competitor observed = pass`: wrong when search coverage, public use or goods details are incomplete.
- `rescued = shortlisted`: wrong; rescue only changes the machine disposition and leaves human/legal and other project gates open.
