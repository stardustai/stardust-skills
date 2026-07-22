# Internal app standards skill

This skill standardizes enterprise internal web systems built through AI coding.

It defines the default stack, engineering design expectations, frontend/backend boundaries, database and deployment rules, and production-readiness review gates for internal admin tools and business systems.

Core boundaries:

- Default to TypeScript, React, Ant Design, NestJS, PostgreSQL, migrations, Docker, and Kubernetes for new internal systems.
- Inspect existing repositories before changing stack or structure.
- Keep internal tools operational, dense, and production-oriented instead of demo-like.
- Do not mark a system production-ready without auth/RBAC, observability, deploy/rollback instructions, resource limits, probes, and critical-path tests.

See [SKILL.md](SKILL.md) for the workflow and reference map.
