# sharecrm CLI Reference

Use the installed CLI help and live object description as the source of truth. Examples contain placeholders only; target identifiers may be requested for lookup but real identifiers must never be embedded in this public skill.

## Authentication and command discovery

```bash
sharecrm auth status
sharecrm --help
sharecrm data --help
sharecrm data describe --help
sharecrm data record --help
sharecrm data describe get --help
sharecrm data record query-by-sql --help
sharecrm data record query-by-fields --help
sharecrm data record get-by-id --help
sharecrm data record query-aggregate-by-sql --help
sharecrm data record create --help
sharecrm data record update --help
```

Use help to confirm that a command exists and inspect any options it exposes; do not assume that help contains a complete payload schema. An empty `-d '{}'` payload may be used only with a read command to obtain its current parameter manifest. Never send an empty execution payload to discover a write command. If a command is missing, compare `sharecrm --help`, `sharecrm data --help`, and `sharecrm data record --help`; a missing command usually indicates an outdated CLI, unavailable remote command, or permission-limited installation.

The local aggregation examples require `jq`; verify it with `jq --version`. If authentication is absent or expired, inspect `sharecrm auth --help` and follow the installed CLI's login flow. Never request or expose tokens, secrets, cookies, or credentials.

## Describe and record reads

Describe each object before selecting fields or status options:

```bash
sharecrm data describe get -d '{"apiName":"ContractObj"}'
```

Query records through the record namespace. Dates are epoch milliseconds and every page is capped at 50:

```bash
sharecrm data record query-by-sql --sql "SELECT _id, contract_amount FROM ContractObj LIMIT 50 OFFSET 0" --need_count true
sharecrm data record query-by-sql --sql "SELECT _id, contract_amount FROM ContractObj LIMIT 50 OFFSET 50" --need_count true
```

Successful query output stores the current page directly in `.recordResult` as an array, not in a nested records key. Count metadata is available through `.queryMeta.totalNumber` and `.queryMeta.returnedCount`. Continue `LIMIT 50 OFFSET n` until the accumulated `.queryMeta.returnedCount` reaches `.queryMeta.totalNumber`, or the final page's count proves the result set is complete. Do not infer completion solely from a display table.

Live field-query and lookup usage is:

```bash
sharecrm data record query-by-fields --data '{"object_api_name":"ContractObj","need_count":true,"select_fields":["_id","contract_amount"],"search_template_query":{}}'
sharecrm data record get-by-id --object_api_name ContractObj --id TARGET_RECORD_ID
```

Run the corresponding `--help` command first to verify the installed command's accepted `search_template_query` and option encoding. Never invent an object, field, status value, payload, or record ID.

The unfiltered aggregate command is verified:

```bash
sharecrm data record query-aggregate-by-sql --sql "SELECT COUNT(*), SUM(contract_amount) FROM ContractObj"
```

Filtered aggregate support varies. For filtered metrics, default to `query-by-sql` detail pages plus local `jq`. The following Bash pattern keeps pages in memory, verifies the response envelope, collects every page, and aggregates structured records rather than parsing display text:

```bash
sql_base="SELECT amount_field, status_field FROM ObjectName WHERE date_field >= START_EPOCH_MS AND date_field < END_EPOCH_MS"
pages=()
offset=0
while true; do
  page="$(sharecrm data record query-by-sql --sql "${sql_base} LIMIT 50 OFFSET ${offset}" --need_count true)"
  if ! jq -e '(.recordResult | type) == "array" and (.queryMeta.returnedCount | type) == "number" and (.queryMeta.totalNumber | type) == "number"' >/dev/null <<<"${page}"; then
    printf 'Unexpected sharecrm response envelope; stop before aggregating.\n' >&2
    exit 1
  fi
  pages+=("${page}")
  returned="$(jq -r '.queryMeta.returnedCount' <<<"${page}")"
  total="$(jq -r '.queryMeta.totalNumber' <<<"${page}")"
  (( returned > 0 )) || break
  offset=$((offset + returned))
  (( offset < total )) || break
done
printf '%s\n' "${pages[@]}" | jq -s --arg validated_label 'VALIDATED_LIVE_LABEL' '[.[].recordResult[]?] | map(select(.status_field.label == $validated_label)) | {included_records: length, amount: (map(.amount_field // 0) | add // 0)}'
```

An empty query may omit or return an empty `.recordResult`; check its type and length before aggregation. The field-value and label paths must be adjusted only after inspecting the returned JSON. Keep substituted labels shell-quoted and pass them through `jq --arg`. Validate labels and internal status values from live describe options first; never hardcode a label from this reference.

## Customer and contact reads

Describe the live customer and contact schemas, then query only confirmed fields:

```bash
sharecrm data describe get -d '{"apiName":"AccountObj"}'
sharecrm data record query-by-sql --sql "SELECT _id, name, life_status FROM AccountObj LIMIT 50 OFFSET 0" --need_count true
sharecrm data describe get -d '{"apiName":"ContactObj"}'
sharecrm data record query-by-sql --sql "SELECT _id, name, account_id, life_status FROM ContactObj LIMIT 50 OFFSET 0" --need_count true
```

These examples contain no customer names or IDs. If live describe does not expose `account_id`, omit it and use the tenant's verified relationship field instead.

## Signed contract amount

- Object: `ContractObj`
- Fields: `contract_amount`, `confirm_time`, `life_status`
- Formula: sum `contract_amount` where `confirm_time` is in the disclosed range and `life_status` is normal according to the live option label or internal value.

```bash
sharecrm data describe get -d '{"apiName":"ContractObj"}'
sharecrm data record query-by-sql --sql "SELECT _id, contract_amount, confirm_time, life_status FROM ContractObj WHERE confirm_time >= START_EPOCH_MS AND confirm_time < END_EPOCH_MS LIMIT 50 OFFSET 0" --need_count true
```

Check the returned `life_status` label locally with `jq`, or filter server-side using its validated internal status value. Disclose the date range, source object, `confirm_time`, `contract_amount`, `life_status`, and sum formula.

## Deal cycle

- Object: `NewOpportunityObj`
- Fields: `stg_changed_time`, `cost_time`, `sales_status`, `life_status`
- Population: normal opportunities with `stg_changed_time` in the disclosed range and the live-described won status.
- Formula: convert each `cost_time` from milliseconds to days with `cost_time / 86400000`, then report both average and median.

```bash
sharecrm data describe get -d '{"apiName":"NewOpportunityObj"}'
sharecrm data record query-by-sql --sql "SELECT _id, stg_changed_time, cost_time, sales_status, life_status FROM NewOpportunityObj WHERE stg_changed_time >= START_EPOCH_MS AND stg_changed_time < END_EPOCH_MS LIMIT 50 OFFSET 0" --need_count true
```

Collect every page with the pagination pattern above. Then replace the two shell-quoted placeholders with values validated from live describe and aggregate the in-memory `pages` array:

```bash
printf '%s\n' "${pages[@]}" | jq -s --arg won_status 'VALIDATED_WON_LABEL' --arg normal_status 'VALIDATED_NORMAL_LABEL' '[.[].recordResult[]? | select(.sales_status.label == $won_status and .life_status.label == $normal_status and .cost_time != null) | (.cost_time / 86400000)] | {count: length, average_days: (if length == 0 then null else add / length end), median_days: (if length == 0 then null else sort | if length % 2 == 1 then .[length / 2 | floor] else (.[length / 2 - 1] + .[length / 2]) / 2 end end)}'
```

## Opportunity conversion

Disclose the chosen definition, numerator, denominator, date fields, and status fields. Support both:

1. **Signed contracts / created opportunities:** numerator is valid signed `ContractObj` records in the contract confirmation range; denominator is `NewOpportunityObj` records created in the opportunity creation range.
2. **Won / (won + lost):** numerator is won opportunities; denominator is won plus lost opportunities, based on live `sales_status` options and the disclosed close-stage date range.

```bash
sharecrm data describe get -d '{"apiName":"ContractObj"}'
sharecrm data describe get -d '{"apiName":"NewOpportunityObj"}'
sharecrm data record query-by-sql --sql "SELECT _id, confirm_time, life_status FROM ContractObj WHERE confirm_time >= START_EPOCH_MS AND confirm_time < END_EPOCH_MS LIMIT 50 OFFSET 0" --need_count true
sharecrm data record query-by-sql --sql "SELECT _id, create_time, stg_changed_time, sales_status, life_status FROM NewOpportunityObj WHERE create_time >= START_EPOCH_MS AND create_time < END_EPOCH_MS LIMIT 50 OFFSET 0" --need_count true
```

Validate normal, won, and lost labels/internal values through live describe. For the second definition, query the disclosed `stg_changed_time` range and locally classify returned labels with `jq`, or use validated internal status values server-side.

## Delivery volume

- Object: `SalesOrderObj`
- Fields: `order_time`, `order_amount`, `delivered_amount_sum`, `order_status`, `life_status`
- Report order count, order amount, or delivered amount explicitly. Include only confirmed and normal records after validating live option labels/internal values.

```bash
sharecrm data describe get -d '{"apiName":"SalesOrderObj"}'
sharecrm data record query-by-sql --sql "SELECT _id, order_time, order_amount, delivered_amount_sum, order_status, life_status FROM SalesOrderObj WHERE order_time >= START_EPOCH_MS AND order_time < END_EPOCH_MS LIMIT 50 OFFSET 0" --need_count true
```

Use `jq` to check that returned `order_status` and `life_status` labels match the live validated confirmed/normal options, or use their validated internal values in SQL. Never hardcode those labels before describe.

## Payment amount

- Object: `PaymentObj`
- Fields: `payment_time`, `amount`, `life_status`
- Formula: sum `amount` where `payment_time` is in range and the record is paid/normal according to live option labels/internal values.

```bash
sharecrm data describe get -d '{"apiName":"PaymentObj"}'
sharecrm data record query-by-sql --sql "SELECT _id, payment_time, amount, life_status FROM PaymentObj WHERE payment_time >= START_EPOCH_MS AND payment_time < END_EPOCH_MS LIMIT 50 OFFSET 0" --need_count true
```

Use `jq` to inspect the returned status labels before including records, or filter with validated server-side internal values. Disclose the paid/normal interpretation and all fields used.

## Writes

Confirm whether the installed CLI exposes a non-executing command description:

```bash
sharecrm data record create --help
sharecrm data record update --help
```

CLI v1.1.12 help confirms these commands exist but does not expose a complete payload schema. Do not infer a write payload from the read commands or probe a write with `-d '{}'`. If the installed version does not provide a non-executing exact schema, report the write capability as unavailable and stop.

When a future installed version does expose the exact schema, first look up the target with `query-by-fields` or `get-by-id`, show the confirmed target and exact intended changes, and obtain explicit user confirmation immediately before the final create/update command. Live usage is expected to take `--data` JSON containing `object_api_name` and `object_data`, and update data must identify the target record, but the live non-executing schema remains authoritative.

```bash
sharecrm --confirm data record create --data '{"object_api_name":"OBJECT_API_NAME","object_data":{}}'
sharecrm --confirm data record update --data '{"object_api_name":"OBJECT_API_NAME","object_data":{"_id":"TARGET_RECORD_ID"}}'
```

The empty payloads above illustrate the expected structure only and must not be run. Use them only after replacing every placeholder from a non-executing live schema and obtaining user confirmation. `--confirm` satisfies the CLI's dangerous-command gate; it does not replace the required user confirmation.

## Follow-ups

Use the verified official sales activity namespace to discover the action:

```bash
sharecrm help sales activity
sharecrm sales activity create-active-record --help
```

Creating a follow-up is a CRM write. Resolve the customer, contact, or opportunity target through a read query; inspect the live action help and schema; show the intended target and content; then obtain explicit user confirmation immediately before execution. If the installed CLI does not expose a usable payload schema, report follow-up creation as unavailable in that command version and stop. Never invent a payload template or probe the write with an empty execution payload.

## Chinese prompt examples

- `查询今年已签约合同金额，按 confirm_time 统计，并说明日期范围、状态过滤和金额口径。`
- `统计本季度成单周期，先验证赢单和正常状态值，再按 stg_changed_time 过滤，输出平均值和中位数。`
- `分别计算已签约合同数/新建商机数，以及赢单/(赢单+输单)，明确分子和分母。`
- `查询本月已确认且正常的销售订单交付量，说明订单金额和交付金额口径。`
- `统计本月已回款且正常的回款金额，先验证状态选项。`
- `给指定客户新增跟进记录。先查找并确认目标，执行写入前再次向我确认。`

## Troubleshooting

- **Authentication expired:** run `sharecrm auth status`, then inspect `sharecrm auth --help` and follow the installed login flow. Never ask for token material.
- **Missing command manifest:** compare the three help levels. For a read command only, rerun its exact `-d '{}'` discovery call. For a write command, do not probe with an empty payload; report the capability as unavailable unless the CLI exposes a non-executing exact schema.
- **IP whitelist rejection:** distinguish authentication success from CRM-side whitelist denial. Redact the source IP in broad reports, but disclose it directly to the authorized administrator when it is required to repair the whitelist.
- **Invalid field:** rerun `sharecrm data describe get -d '{"apiName":"OBJECT_API_NAME"}'`; use only live fields, types, and options.
- **Empty result:** `.recordResult` may be absent or an empty array. Check it before `jq` aggregation, then verify epoch-millisecond boundaries, timezone, object, permissions, status values, and an unfiltered first page before concluding there is no data.
- **Pagination:** request `LIMIT 50 OFFSET 0`, increment OFFSET by 50, and continue until accumulated `.queryMeta.returnedCount` reaches `.queryMeta.totalNumber` or the final page confirms completion. Aggregate all pages once.
- **Writes:** inspect live create/update manifests, look up and confirm the target, present the exact payload, then require explicit confirmation immediately before execution.
