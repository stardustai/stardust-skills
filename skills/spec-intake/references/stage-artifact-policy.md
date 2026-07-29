# Stage Artifact Policy

Use this reference whenever deciding what may be produced at the current stage, especially when the user supplies a long research report, PRD, architecture document, or asks to skip directly to implementation.

The stage gate controls both the readiness label and the depth of the artifacts. A document is out of stage when it says `review_required` but contains enough architecture, APIs, work packages, estimates, or delivery sequencing to start engineering.

## Artifact ceilings

| Current stage | Allowed artifacts | Prohibited artifacts |
| --- | --- | --- |
| `business_feasibility` | Customer/task anchor, current workflow, pain, evidence registry, market and competitor evidence, minimum paid artifact, blockers, next evidence action | Detailed product workflow, UI design, service architecture, APIs, schemas, SLOs, work packages, estimates, implementation order |
| `product_shape` | Exactly one first-version user/task/workflow/artifact, scope and non-goals, business success scenarios, user journeys, low-fidelity wireframe, product risks | Service decomposition, endpoint contracts, database design, deployment topology, engineering work packages, sprint plan |
| `engineering_gap_review` | Existing/partial/missing/external/unknown capabilities, inspected code paths, ownership gaps, feasibility blockers | Final architecture, complete API contract, implementation tickets, delivery estimate, engineering commitment |
| `technical_spec` | Architecture, interfaces, data model, security boundaries, technical score, failure handling | Engineering start commitment before technical and validation gates are confirmed |
| `validation_design` | Fixtures, metrics, pass/fail rules, evaluation assets, owners and timebox | Claim that validation has passed or engineering has started |
| `validation_execution` | Execution evidence, measured results, failures, decisions and rerun plan | Unapproved scope expansion or hidden product changes |
| `engineering_delivery` | Work packages, estimates, dependencies, implementation order, QA/rollout/rollback plan | Work outside the confirmed spec and change-control path |

For v1.11 structural compatibility, early-stage JSON may still include the required `implementation_mapping` object, but it must be an empty placeholder:

- `engineering_review_type=not_started`
- `capabilities=[]`
- no source-code paths or review summary
- no technical design summary, score, scoring dimensions, or confirmation

## Customer and task anchor

Do not let broad market opportunity become the main intake thread until these anchors are traceable:

1. One target buyer or customer segment.
2. One daily user.
3. One recurring task and triggering event.
4. The current workflow or substitute.
5. One costly failure, delay, or quality problem.
6. One proposed minimum paid artifact.

Market reports and competitor research may be collected as an appendix while anchors are missing. They do not substitute for first-party customer evidence.

## Existing-document audit

When an existing document is supplied, audit it before extending it:

1. Classify the artifact: customer evidence, internal strategy, product proposal, technical reference, or delivery commitment.
2. Extract confirmed facts separately from author claims, AI-generated analysis, assumptions, and proposed solutions.
3. Map traceable evidence into `opportunity_assessment.evidence_registry`.
4. Put unresolved customer, owner, baseline, data, acceptance, and scope facts in `missing_fields` and `stage_gate.blockers`.
5. Infer the real current stage from confirmed evidence. Do not inherit `P0`, `spec_review`, `review_required`, or another self-declared label without checking the gate.
6. Apply the artifact ceiling for the inferred stage. Summarize or quarantine out-of-stage technical content as non-authoritative reference material; do not expand it.

AI-generated industry analysis is `internal_judgment` or an assumption unless it cites a verifiable external source. Customer interest without a traceable customer, reviewer, workflow, budget/resource commitment, or artifact remains `anecdotal`.

## Canonical first version

Before leaving `product_shape`, require exactly one:

- daily user;
- recurring task;
- canonical workflow;
- primary Artifact;
- acceptance owner;
- explicit non-goal list.

If a brief contains several independent Domain Packs, personas, workflows, or primary artifacts, split them into separate specs or choose one first-version slice. Do not hide portfolio scope inside a single MVP.

## Human confirmation authority

A document and an AI cannot confirm their own stage transition. Record both identity and role:

- `handoff_to_product`: `business_owner`
- `request_engineering_gap_review`: `product_owner`
- `continue_technical_spec` or `mark_validation_design_ready`: `engineering_owner`
- `mark_validation_execution_ready`: `qa_owner`
- `ready_for_engineering`: `decision_owner`

For v1.11, record the role in `stage_gate.stage_exit_check.confirmed_by_role`. A confirmation from the wrong role does not advance the stage.
