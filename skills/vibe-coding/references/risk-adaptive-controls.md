# Risk-Adaptive Controls

## Source and calculation

Use the Spec's confirmed `delivery_risk_profile`. Its final tier is the highest
risk produced by user scope, data sensitivity, operation/destructive write,
permissions and external integrations, recoverability, or business impact. Do
not average dimensions and do not lower the tier during coding.

If implementation reveals a higher-risk fact, stop, update the Spec and risk
decision, and apply the higher controls. Lowering risk requires the authorized
Decision Owner to confirm a changed product or operating scope.

## Controls by tier

| Control | R0 | R1 | R2 | R3 |
| --- | --- | --- | --- | --- |
| Data | Synthetic/isolated only | Approved low-risk internal data | Approved real data with explicit access controls | High-sensitivity controls; engineering-led |
| Release | Never production | Allowed after full gate | PR and controlled release | Engineering/security/compliance-led release |
| TDD | May be simplified | Required for behavior changes | Required | Required with highest scrutiny |
| Business E2E | Core demo flow | Critical scenarios | Critical, negative, permission, recovery | Full critical suite and high-impact failure coverage |
| Integration/permission tests | As applicable | As applicable | Required | Required with adversarial coverage |
| Runtime/rollback | Minimal reproducible preview | Verified and recoverable | Verified runbook and rollback | Exercised operational controls |
| Independent review | Basic | Required automated review | Full automated review; repository human policy applies | Full automated review plus mandatory higher policies |
| Git delivery | Branch; no production claim | Direct push allowed only under delivery rules | PR required | PR required |

## Cross-cutting escalations

Regardless of tier, architecture/API/data-schema/permission changes, migrations,
new external dependencies, plan-external refactors, irreversible actions, and new
production privileges trigger their specialist gates. Risk controls are minimums,
not permission to bypass repository or company policy.

## R0 boundary

R0 is a prototype, not a weaker production path. It must be visibly marked
prototype-only, use synthetic or explicitly isolated data, remain recoverable,
and never be described as deployable or production-ready. The user must explicitly
authorize creating the R0 prototype, and that authorization must be recorded before
any code is created; the agent may not silently downgrade an unready Spec to R0.
