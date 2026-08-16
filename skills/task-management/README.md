# Task Management skill

This skill reads current internal projects, TODOs, owners, deadlines, blockers,
and follow-ups from a local CEO agent service.

Core boundaries:

- Requires the local audit Web API on `http://127.0.0.1:8765`.
- Uses read-only endpoints only; it never creates, updates, or closes tasks.
- Treats returned records as evidence and asks for clarification when multiple
  task matches remain plausible.

See [SKILL.md](SKILL.md) for the API queries and result-handling rules.
