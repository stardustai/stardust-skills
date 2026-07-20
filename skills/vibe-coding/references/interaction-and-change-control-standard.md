# Interaction and Change-Control Standard

## Default autonomy

Automatically inspect the repository, create plans, design tests, edit code,
run checks, collect evidence, review, commit, and deliver when those actions stay
inside the approved Spec, Design, risk, permissions, and plan. Do not ask users to
choose internal names, libraries, or local implementation details that do not
change product or operational outcomes.

## Mandatory pause

Stop before acting when evidence shows any of the following:

- the Spec conflicts with itself, the requested result, or an immutable system
  constraint;
- product behavior, business rule, scope, business metric, or UX must change;
- data use, authorization, external integration, cost, or risk tier must change;
- the plan conflicts with real code or requires a plan-external module;
- module ownership, public API, data schema, state model, core dependency, runtime
  topology, or approved architecture must change;
- a local refactor or technical-debt repair is necessary outside approved scope;
- an irreversible/destructive action or new production privilege is required.

## Question contract

Ask one decision at a time and include:

1. the finding and reproducible evidence;
2. why the agent cannot decide it under the existing contract;
3. product, engineering, risk, schedule, and migration impact as applicable;
4. two or three mutually exclusive choices stated in user outcomes;
5. a recommended choice and concrete reason.

Do not ask “how should I implement this?” of a non-technical employee. Translate
technical alternatives into observable behavior, risk, time, and maintainability.

## Applying a decision

After confirmation, update the authoritative artifact first:

- product/business behavior -> Spec and Business Owner confirmation;
- architecture/data/runtime contract -> Design and required owner confirmation;
- task sequencing/scope -> Plan;
- verification impact -> test plan, Eval plan, and traceability;
- risk or permission -> risk profile and Decision Owner confirmation.

Mark affected downstream artifacts stale until synchronized. Record the decision,
scope, approver, time, and linked IDs. Never silently update only the code.
