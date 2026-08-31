# Evidence and Contract Matrix

Use the matrix only for material fields: fields whose values, representation, omission, identity, coordinates, timeline, point order, or lineage can change platform behavior, customer acceptance, or delivery claims. Redact external locators so they reveal no credentials, signed URLs, private object keys, or customer-sensitive paths. An `INFERRED` row remains `INFERRED` until supporting evidence is recorded; do not promote it from code behavior, a default, or an unverified assumption.

## Evidence manifest

| evidence_id | class | locator | version_hint | proves | status | notes |
|---|---|---|---|---|---|---|

Allowed evidence status: `PRESENT`, `MISSING`, `STALE`, `CONFLICTING`, `NOT_APPLICABLE`.

## Material contract rows

| contract_id | domain | business_field | source_evidence | platform_contract | transform_rule | target_contract | authority | missing_policy | unknown_policy | validator | status |
|---|---|---|---|---|---|---|---|---|---|---|---|

Allowed row status: `CONFIRMED`, `INFERRED`, `CONFLICT`, `MISSING`.

## Implementation scope card

| item | frozen decision |
|---|---|
| files_to_create_or_modify | Repository-relative paths only |
| immutable_entrypoints | Entrypoints, parameters, top-level config, and production flows that must not change |
| input_boundary | Accepted source packages, records, fields, and data types |
| output_boundary | Required records, files, metadata, and serialization shape |
| remote_io_boundary | Read-only, approved writes, or not applicable |
| local_modification_policy | Freeze exactly one user-authorized strategy: `copy-on-write`, `modify-in-place`, or `no-change` |
| fallback_policy | Explicitly approved fallbacks only |
| hard_failures | Missing or conflicting evidence that must stop implementation |
| maximum_planned_gate | One of G0 through G6 |

Do not infer `local_modification_policy` from repository history or convenience. Freeze it from the user's current authorization before implementation.

## Sanitized minimal examples

These synthetic rows demonstrate shape only. Do not reuse their values as customer mappings or evidence.

### Import example

| contract_id | domain | business_field | source_evidence | platform_contract | transform_rule | target_contract | authority | missing_policy | unknown_policy | validator | status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| EX-IMPORT-001 | identity | record ID | `demo.json:id` is a string | attachment requires string `id` | preserve unchanged | `attachment.id` | current sample plus current schema | block | reject | source/attachment equality | `INFERRED` |

### Prelabel example

| contract_id | domain | business_field | source_evidence | platform_contract | transform_rule | target_contract | authority | missing_policy | unknown_policy | validator | status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| EX-PRELABEL-001 | semantic | source label | synthetic source uses code `7` | operator exposes target value `class-a` | require confirmed mapping evidence | `preprocessedData.annotations[].value` | confirmed customer mapping plus operator | block | reject | mapping and annotation-type check | `MISSING` |

### Export example

| contract_id | domain | business_field | source_evidence | platform_contract | transform_rule | target_contract | authority | missing_policy | unknown_policy | validator | status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| EX-EXPORT-001 | lineage | object ID | annotation uses `demo-object` | slot carries a stable ID | preserve identity | `objects[].id` string | current target spec plus accepted sample | block | reject | round-trip identity check | `INFERRED` |
