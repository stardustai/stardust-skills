# Architecture and UI Standard

## Architecture from evidence

Read the active Spec, scoped rules, real dependency graph, public contracts, data
model, runtime path, and existing analogues. Prefer the project's approved
architecture and reusable components. Do not create a parallel subsystem merely
because it is easier to generate.

`docs/system-architecture.md` must state system boundaries, component ownership,
dependencies, data flow and lifecycle, interfaces, authentication/authorization,
failure handling, observability, runtime/deployment boundary, and rollback. For
algorithm/model/Agent/search/ranking/classification/generation/automated-decision
systems, `docs/algorithm-design.md` additionally defines business problem,
inputs/outputs, data, baseline, method, thresholds and business meaning,
determinism, cost, permissions, failure/degradation, and reproduction.

## Architecture change gate

Pause before changing module responsibility, public interface, schema, state
ownership, dependency direction, core dependency, permission model, or runtime
topology. Present evidence, impact, and 2–3 mutually exclusive choices with a
recommendation. After confirmation, update Design, Plan, tests, traceability, and
technical-debt records before implementation.

Private naming, formatting, and extraction inside newly added code may be handled
automatically when they do not alter responsibility, contract, or product behavior.

## UI source and reuse

Implement approved Spec behavior and the approved SVG wireframe/design. Inspect
and reuse the existing design system, layout, components, tokens, and comparable
screens. Do not invent fields, actions, flows, or permissions.

Cover every applicable state: loading, empty, success, validation error, system
error, no permission, timeout/offline, partial data, disabled, and confirmation.
Enforce field validation and role visibility. Verify critical journeys in a real
browser, responsive breakpoints, keyboard/focus/accessibility, and screenshots or
visual regression where useful.

If no design system exists, show 2–3 concrete visual directions before formal UI
coding. If real data or interaction makes the wireframe unsuitable, ask the user
to choose: preserve the design, make a described local adjustment, or return to
product design. User acceptance of the actual interface is required; agent visual
self-approval is insufficient.
