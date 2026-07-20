# Delivery Risk Profile

Use this reference whenever `spec-intake` collects, assesses, confirms, or changes
`delivery_risk_profile`, and before setting `product_ready` or any later readiness label.

## Purpose

`delivery_risk_profile` is product input that determines what the first version may do
and which controls engineering must implement. Risk is decided before engineering starts;
engineering must not discover after coding that the product was allowed to use the wrong
data, users, permissions, or write path.

The profile evaluates six independent dimensions. The final `risk_tier` is at least the
highest floor produced by any dimension; it is never an average.

## Six Dimensions

| Dimension | Allowed values from lower to higher risk |
| --- | --- |
| `user_exposure` | `prototype_only`, `internal_single_team`, `internal_multi_team`, `external_users`, `customer_facing`, `unknown` |
| `data_sensitivity` | `synthetic`, `public`, `internal`, `confidential`, `restricted`, `unknown` |
| `write_impact` | `none`, `read_only`, `reversible_write`, `irreversible_write`, `bulk_destructive`, `unknown` |
| `integrations_and_permissions` | `none`, `approved_internal`, `external_or_elevated`, `production_privileged`, `unknown` |
| `reversibility` | `easy`, `moderate`, `difficult`, `irreversible`, `unknown` |
| `business_impact` | `demo`, `low`, `medium`, `high`, `critical`, `unknown` |

Ask in business language and extract facts already given:

1. Who will use the first version: demo viewers, one internal team, multiple teams, external
   users, or customers?
2. What is the most sensitive data it may read or produce?
3. Is it read-only, a reversible write, an irreversible write, or a destructive batch?
4. Which systems and permission level must it access?
5. If it produces a wrong result, how easily can the system and data return to the last
   correct state?
6. What is the highest realistic business impact of a wrong result or unavailable system?

Do not ask the user to assign R0-R3 before collecting the underlying facts. Show the
derived profile, rationale, controls, and proposed tier to the decision owner for
confirmation.

## Risk Tiers

| Tier | Meaning | Typical product boundary |
| --- | --- | --- |
| `R0` | Isolated prototype | Prototype-only users, synthetic/public data, no business writes, no privileged integration, easy recovery, demo impact; never production |
| `R1` | Low-risk internal delivery | One or more internal teams, internal data, read-only or otherwise low-impact behavior, approved internal access, low business impact |
| `R2` | Material business delivery | External/customer exposure, confidential data, reversible writes, elevated/external integration, difficult recovery, or medium/high impact |
| `R3` | Critical or destructive delivery | Restricted data, irreversible or bulk-destructive writes, production-privileged access, irreversible recovery, or critical business impact |

Exact minimum floors are deterministic:

- `external_users`, `customer_facing`, `confidential`, `reversible_write`,
  `external_or_elevated`, `difficult`, `medium`, or `high` require at least `R2`.
- `restricted`, `irreversible_write`, `bulk_destructive`, `production_privileged`,
  `irreversible`, or `critical` require `R3`.
- A lower-risk dimension never cancels a higher-risk dimension.

## Field Contract

`delivery_risk_profile` contains:

| Field | Meaning |
| --- | --- |
| `risk_tier` | `R0`, `R1`, `R2`, `R3`, or `unknown` while unresolved |
| `rationale` | Why the tier follows from real product facts |
| `dimensions` | The six resolved dimension values |
| `required_controls` | Controls the downstream delivery must implement |
| `assessment.status` | `pending`, `confirmed`, or `rejected` |
| `assessment.assessed_by` | Person or agent that structured the assessment |
| `assessment.confirmed_by` | Must match `owners.decision_owner` at product-ready or later |
| `assessment.confirmed_at` | Valid ISO date such as `2026-07-20` |

Controls are risk-specific constraints, not vague reminders. Examples include data
redaction and authorization, read-only access, approval before writes, idempotency,
auditability, rollback, human review, staged rollout, and production approval.

## Product Gate

- Before `product_ready`, the six dimensions may still contain `unknown`, the tier may be
  `unknown`, and assessment may be pending. These gaps must remain visible blockers.
- `product_ready` and every later product-proof label require all six dimensions resolved,
  a tier between R0 and R3, a non-empty rationale, and confirmed assessment.
- R1-R3 require non-empty `required_controls`.
- `assessment.confirmed_by` must match `owners.decision_owner`, `assessed_by` must be
  present, and `confirmed_at` must be a valid ISO date.
- A requested `risk_tier` below the highest dimension floor is invalid. Raise the tier or
  change the actual product boundary and obtain confirmation; never lower the risk label
  to make engineering easier.

If a mature brief demands `engineering_ready` but leaves any dimension unknown, lacks
decision-owner confirmation, or conflicts with the derived floor, refuse the gate and
return to `product_shape` with the exact missing or conflicting inputs.
