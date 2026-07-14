# Fxiaoke CRM CLI Skill Design

## Goal

Replace the existing `fxiaoke-crm-mcp` skill with `fxiaoke-crm-cli`. The new skill teaches agents to use the official `sharecrm` CLI as the Fxiaoke CRM fact source for record lookup, object discovery, statistics, and carefully confirmed writes.

The change removes the runtime dependency on the custom Vercel MCP gateway. It does not remove or modify the separate `crm_connector` repository or deployment.

## Distribution

- Source of truth: `stardust-skills/skills/fxiaoke-crm-cli/`
- Local installation target: `~/.agents/skills/fxiaoke-crm-cli/`
- The tracked `skills/fxiaoke-crm-mcp/` directory is renamed, so only one Fxiaoke CRM skill can trigger.
- `README.md` is updated to describe the CLI dependency, installation, permissions, examples, and new directory name.

No credentials, tokens, app secrets, CRM records, or local CLI state are committed.

## Skill Structure

```text
skills/fxiaoke-crm-cli/
├── SKILL.md
└── references/
    └── cli-reference.md
```

`SKILL.md` contains the decision rules agents need on every invocation:

- use `sharecrm` as the CRM fact source;
- inherit the authenticated CRM user's permissions;
- verify `sharecrm auth status`, then verify an actual remote command because login success alone does not prove CRM access;
- inspect the live object description before selecting fields;
- default to read-only operations;
- require explicit confirmation immediately before CRM writes;
- state date range, source object, fields, status filters, numerator, and denominator for every metric;
- never expose credentials or CLI authentication state.

`references/cli-reference.md` contains command syntax and worked examples so the main skill remains concise. It covers:

- authentication and command discovery;
- `data describe get` and object identification;
- `query-by-sql`, `query-by-fields`, `get-by-id`, and aggregate queries;
- FQL dates, limits, offsets, and local `jq` aggregation;
- customer, contact, opportunity, contract, sales order, payment, and follow-up examples;
- the verified year-to-date metric playbook for signed contract amount, deal cycle, opportunity conversion, delivery volume, and payments;
- diagnosis of expired authentication, missing command manifest, IP whitelist rejection, invalid fields, empty results, and pagination truncation.

## Query Rules

Agents discover tenant fields from `sharecrm data describe get` before querying. Known object names may be used as search anchors but are not treated as universal schema.

For filtered statistics, the reliable default is:

1. Query matching records with `query-by-sql` using explicit fields and `LIMIT 50 OFFSET n`.
2. Continue until the result is complete.
3. Aggregate the returned records locally with `jq` or equivalent structured processing.

`query-aggregate-by-sql` may be used only after the exact query has been verified against the current CLI. The skill must not imply that every FQL filter is accepted by the aggregate command.

Date and date-time filters use the numeric millisecond representation accepted by live `query-by-sql`. Displayed results remain in the user's CRM locale and timezone.

## Metric Definitions

- Signed contract amount: `ContractObj`, confirmation date in range, normal contracts, sum of the live contract amount field.
- Deal cycle: `NewOpportunityObj`, opportunities entering won status in range, CRM `cost_time` converted from milliseconds to days; report average and median.
- Opportunity conversion: always name the formula. Support both signed contracts divided by created opportunities and won divided by decided opportunities.
- Delivery volume: `SalesOrderObj`, order date in range, confirmed and normal records; report count and expected delivery amount. Report shipped amount separately only when the field is populated.
- Payments: `PaymentObj`, payment date in range, paid/normal records, sum of payment amount.

## Safety

- Read operations can run directly.
- Creation, update, approval, assignment, lifecycle transition, and deletion require the user to see the target and intended change and then explicitly confirm the final command.
- `--debug` is used only for connector diagnosis. Debug output must not be copied into user-visible responses if it contains credentials or private record payloads.
- The skill never asks users to paste access tokens, refresh tokens, app secrets, permanent codes, cookies, or local encrypted state.

## Verification

Before publishing:

1. Validate frontmatter and Markdown structure.
2. Run negative trigger cases that should not invoke CRM, including generic SQL help and non-Fxiaoke CRM questions.
3. Run positive trigger cases for record lookup, year-to-date metrics, schema ambiguity, authentication failure, and a confirmed write request.
4. Run live read-only smoke tests: `auth status`, remote command discovery, one object description, and one filtered record query.
5. Scan the repository for credential-like content and inspect the staged diff.
6. Run the repository's available tests or validation scripts.

## Release And Notification

Commit the rename, skill content, references, and README changes as one feature commit, push `main` to the configured GitHub remote, and verify the remote commit.

After the push succeeds, send one message to the DingTalk group `解决方案工程师&销售工程师` containing:

- what changed and why;
- how to update/install from `stardust-skills`;
- the local dependency on the official `sharecrm` CLI and `sharecrm auth login`;
- two short example requests, including the five-metric year-to-date report;
- the rule that agents inherit each user's CRM permissions and do not require shared credentials.

Do not include live CRM values, credentials, internal IP addresses, or customer records in the group message.
