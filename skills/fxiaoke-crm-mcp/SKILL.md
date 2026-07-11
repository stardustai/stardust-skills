---
name: fxiaoke-crm-mcp
description: Use this when the user asks for Fxiaoke CRM, 纷享销客, CRM contracts, signed amount, opportunities, conversion rate, deal cycle, customers, follow-ups, sales orders, delivery volume, payments, receivables, or CRM writeback through the crm_connector MCP. This skill requires using the Fxiaoke CRM MCP as the business fact source, preserving CRM permission boundaries through user OAuth, checking live tool schemas before calls, and reporting metric口径/date ranges explicitly.
---

# Fxiaoke CRM MCP

Use the `crm_connector` MCP when the user asks for Fxiaoke CRM facts, metrics, record lookup, follow-up creation, or safe CRM updates. The MCP is a transparent OAuth bridge: the agent authenticates through MCP OAuth, the user logs in to Fxiaoke, and Fxiaoke remains the permission and audit source.

## Core Rules

1. **CRM is the fact source.** Do not answer CRM metrics from memory, spreadsheets, screenshots, or guessed object names when `crm_connector` is available.
2. **Use the authenticated user.** The MCP inherits the user's Fxiaoke OAuth permissions. Do not ask for admin credentials, app secrets, permanent code, CRM access tokens, refresh tokens, cookies, or manual token paste.
3. **Login only when needed.** If MCP returns `needs_login`, run or ask the user to run:

```bash
codex mcp login crm_connector --scopes mcp,offline_access
```

4. **Inspect live schemas first.** Start with `initialize`, `tools/list`, and `crm_describe_objects` before constructing record queries or writes. Fxiaoke tenant fields can differ by deployment.
5. **State the口径.** For every aggregate, include date range, object sources, amount fields, status filters, and whether the result is count-based, amount-based, created-date-based, or signed-date-based.
6. **Do not expose credentials.** Never print Authorization headers, access tokens, refresh tokens, app IDs/secrets, callback codes, cookies, or signed confirm tokens unless the token is intended as a user confirmation token and the user requested the raw value.
7. **High-impact writes need confirmation.** Follow-up creation can be direct after target validation. Creates and updates that affect sales, contract, payment, customer, or opportunity state must dry run first and require the returned `confirm_token`.
8. **Prefer exact evidence over summaries.** When a metric looks surprising, drill into sample records and field distributions instead of smoothing over uncertainty.

## Tool Flow

When callable MCP tools are visible, use them directly. If tools are not visible in the current session, discover them:

```text
tool_search: crm_connector crm_describe_objects crm_search_records crm_add_followup crm_update_record
```

Minimum read flow:

```text
initialize -> tools/list -> crm_describe_objects -> crm_search_records
```

For writes:

```text
crm_describe_objects -> crm_search_records target -> crm_update_record dry_run=true -> user confirmation -> crm_update_record dry_run=false with confirm_token
```

If direct tool calls are unavailable but the MCP is installed locally, use the normal MCP login/list path instead of hand-written CRM API calls:

```bash
codex mcp list
codex mcp get crm_connector
codex mcp login crm_connector --scopes mcp,offline_access
```

Only use raw Streamable HTTP MCP JSON-RPC as a fallback for debugging the connector itself. If you do, still call `tools/list` first and do not print bearer tokens.

## Known Tenant Objects

Use `crm_describe_objects` as source of truth, but current live mappings are:

| Business concept | Fxiaoke object |
| --- | --- |
| Customer | `AccountObj` |
| Contact | `ContactObj` |
| Opportunity | `NewOpportunityObj` |
| Contract | `ContractObj` |
| Sales order / delivery order | `SalesOrderObj` |
| Payment / collection | `PaymentObj` |
| Project | `ProjectObj` |

Do not hard-code these without checking `crm_describe_objects`; they are anchors for this tenant, not a universal Fxiaoke schema.

## Metric Playbooks

For "今年已签约合同金额":

- Date range: from January 1 of the current year through today in the user's timezone unless the user specifies otherwise.
- Source: `contract` / `ContractObj`.
- Amount: contract amount field from schema.
- Date: signed/confirmed date if available; otherwise explain the fallback date field.
- Exclude clearly deleted, voided, draft, or failed contracts when a status field supports it.

For "成单周期":

- Source: opportunities and/or signed contracts depending on schema evidence.
- Prefer opportunity cycle duration when the tenant has a reliable `cost_time` or close-time field.
- Report average and median; explain whether cycle is from opportunity creation to close, or another available interval.

For "商机转换率":

- Source: `NewOpportunityObj`.
- Define numerator and denominator explicitly.
- If using signed-contract count as numerator, label it as "按已签约合同数 / 今年新建商机数".
- If using won opportunities as numerator, label it as "赢单商机数 / 可判定商机数".
- Avoid presenting one口径 as the only possible conversion rate.

For "交付量":

- Source: `SalesOrderObj` unless the user says project delivery or shipment delivery.
- Report both count and amount when both fields exist.
- State whether canceled/unconfirmed orders were excluded.

For "回款额":

- Source: `PaymentObj`.
- Amount: received/payment amount field.
- Date: payment/received date field.
- Exclude failed/voided payments when status supports it.

## Query Pattern

Use conservative pagination:

```text
crm_search_records(object="contract", filters=[], limit=50, offset=0)
```

Then page until there are no more records or the requested date range is fully covered. If the MCP supports server-side filters for the required date/status fields, use them; otherwise fetch pages and filter client-side while documenting that filter mode.

For each aggregate:

1. Read the object schema.
2. Identify candidate date, amount, status, owner, and relation fields from actual fields.
3. Fetch records with small pages first.
4. Check field distributions and sample records.
5. Aggregate with a clear口径.
6. Return a compact table and caveats only where data is ambiguous.

## Output Format

For executive metrics, use:

```text
时间范围：
权限口径：

| 指标 | 结果 | 口径 |
| --- | ---: | --- |
| 已签约合同金额 | ... | ... |
| 成单周期 | ... | ... |
| 商机转换率 | ... | ... |
| 交付量 | ... | ... |
| 回款额 | ... | ... |

数据说明：
- ...
```

Keep caveats tied to actual field uncertainty. Do not add generic disclaimers.
