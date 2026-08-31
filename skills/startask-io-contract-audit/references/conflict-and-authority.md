# Conflict Attribution and Field Authority

Use this reference after recording `EvidenceManifest` items and material `ContractRow` entries. A conflict is not resolved by the presence of more evidence: record the disagreement, decide authority for the affected field, and preserve the rejected alternatives.

## Conflict layers

Use exactly one primary layer for each conflict entry. The eight layers are:

1. `SPEC` — customer configuration, specification, acceptance criteria, or business vocabulary disagree.
2. `SOURCE` — real source files, layouts, encoding, value ranges, or missingness disagree.
3. `OPERATOR` — the operator or schema node shape, child order, category, or input value type disagrees.
4. `PLATFORM` — observed platform records or documented platform behavior disagree.
5. `TRANSFORM` — calibration, pose, coordinate convention, timeline, or geometry interpretation disagrees.
6. `SERIALIZER` — target record assembly, omission behavior, ordering, IDs, or lineage serialization disagrees.
7. `VALIDATOR` — the official validator, accepted output, or validation result disagrees.
8. `ENVIRONMENT` — credentials, runtime, endpoint, network, or other execution environment evidence disagrees.

If one issue crosses layers, split it into one row per independently actionable disagreement. Reuse the material `contract_id`, assign exactly one primary `layer` to each row, and connect sibling conflict IDs through `related_conflicts`. Never join layer names (for example, `PLATFORM/VALIDATOR`) in one primary-layer cell.

## Conflict register

Create one entry for every material `ContractRow` whose `status` is `CONFLICT` or `MISSING`, and whenever two relevant artifacts disagree. Keep the entry linked to the evidence manifest IDs; do not replace evidence with an unsupported conclusion.

| conflict_id | contract_id | layer | related_conflicts | conflicting_evidence | implementation_impact | recommended_decision | alternatives | status |
|---|---|---|---|---|---|---|---|---|

Use one of the eight literal layer names in `layer`; `/`, `+`, commas, and multi-layer prose are invalid there. Use `OPEN`, `DECIDED`, `BLOCKED`, or `NOT_APPLICABLE` for `status`. An `OPEN` or `BLOCKED` conflict that can change behavior, remote state, or the claimed verification level is critical until the user makes a decision.

## Field-specific authority

Select authority separately for every affected field. Do not apply one global source-precedence order.

| affected field | authority rule | required handling when evidence disagrees |
|---|---|---|
| Platform node shape, child order, input value type | Operator/schema controls platform node shape, child order, and input value type. | Record the operator evidence and stop before emitting an incompatible target structure. |
| Source semantic IDs and business vocabulary | Customer configuration/specification controls source semantic IDs and business vocabulary; operator categories are target vocabulary, not an automatic source-ID dictionary. | Record an explicit mapping decision; never infer source IDs from target categories. |
| Source layout, encoding, value range, and missingness | Real samples establish actual source layout, encoding, value range, and missingness; disagreement with a specification remains a recorded conflict. | Preserve the discrepancy and ask for a decision before changing parser or missing-value behavior. |
| Target serialization | Current specification, official validator, and accepted sample jointly constrain target serialization; disagreement among them requires a decision. | Do not serialize a disputed representation as though it were confirmed. |
| Spatial transforms | Calibration, pose definitions, coordinate conventions, and reproducible geometry checks jointly establish spatial transforms. | Keep coordinate, axis, frame, and timestamp assumptions explicit; do not implement until the disagreement is resolved. |
| Existing script behavior | Existing script behavior is compatibility evidence only. | It may explain a compatibility constraint but cannot override the field authority above. |

## Confirmation gate

Before formal implementation, resolve critical `OPEN` or `BLOCKED` conflicts with a confirmation gate. Ask at most three implementation-changing questions in one turn. Each question must include:

- the affected `conflict_id` and linked evidence;
- a recommendation and the reason it follows the field-specific authority rule;
- feasible alternatives;
- the implementation, remote-state, and verification-claim impact; and
- safe read-only work that can continue while awaiting the decision.

Ask only for decisions that change implementation, remote state, or the claimed verification level. Continue inventory, local read-only inspection, and reproducible checks where they do not presuppose the answer. Stop formal implementation while a critical conflict remains unresolved.

## Prohibited resolution shortcuts

- Do not introduce silent mappings.
- Do not use a default `other` category.
- Do not mask missing values with empty strings.
- Do not treat array indexes as child semantics.
- Do not add fallbacks unless they were explicitly approved.
