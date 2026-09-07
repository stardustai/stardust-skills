# Output Contract

Use this structure for final review reports. Keep it concise but evidence-heavy.

```markdown
**Redteam Verdict:** block | changes_requested | risky_but_mergeable | pass

**PR Intent**
- Claimed behavior:
- Intent source: PR description | linked spec | inferred from diff
- Affected surfaces: API | UI | worker | DB | config | tests | docs | deploy
- Primary languages:
- Evidence read:

**Findings**
| Severity | Type | File | Evidence | Risk | Required action |
| --- | --- | --- | --- | --- | --- |

**Fake / Fallback Analysis**
| Severity | File | Signal | Production path? | Decision | Required proof |
| --- | --- | --- | --- | --- | --- |

**Engineering Quality Scorecard**
| Dimension | Result | Language rule | Evidence | Recommendation |
| --- | --- | --- | --- | --- |

**Targeted Optimization Plan**
| Priority | Action | Owner | Minimal fix | Better design | Acceptance criteria | Proof command |
| --- | --- | --- | --- | --- | --- | --- |

**Verification Gaps**
- Commands found:
- Commands run:
- Missing tests:
- Missing contract proof:
- Missing runtime/env proof:
- Missing docs/deploy proof:

**Merge Decision**
- Decision:
- Must fix before merge:
- Follow-ups:
- Residual risk:
```

## Verdict Rules

| Verdict | Use when |
| --- | --- |
| `block` | A blocker finding exists, or PR evidence is too weak to rule out fake production behavior, data/security risk, or broken contract. |
| `changes_requested` | No blocker is proven, but the author must add tests, remove fallback ambiguity, improve boundaries, or supply missing evidence before merge. |
| `risky_but_mergeable` | Risk is understood, bounded, owned, and acceptable for merge with explicit follow-up. |
| `pass` | No material issue found and the relevant commands/tests/contracts were freshly checked or reviewed. |

## Finding Requirements

Each `BLOCKER` and `HIGH` finding must include:

- exact file and line when available;
- why it matters to product behavior, data, security, operations, or maintainability;
- the smallest acceptable fix;
- the stronger design direction when different from the minimal fix;
- owner role;
- acceptance criteria;
- proof command or proof artifact.

## Wording Rules

- Use `PROVEN`, `LIKELY`, `SUSPECT`, or `UNKNOWN` for evidence confidence when the distinction matters.
- Do not say "looks good" without stating what was checked.
- Do not call something "bad design" without naming the language-specific rule or concrete maintenance cost.
- Do not request broad rewrites when a narrow fix can remove merge risk.
- If scanner output is used, say it supplied leads and name which leads were manually verified.
