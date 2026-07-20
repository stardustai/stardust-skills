# Runtime Standard

## Runtime contract

`docs/runtime-constraints.md` defines the actual supported environment and limits:

- OS/runtime/tool versions and install/build steps;
- start, stop, test, Eval, smoke, and health commands;
- configuration sources and safe Secret acquisition;
- ports, network, upstream/downstream services, and data directories;
- timeouts, concurrency, throughput, resource and cost limits;
- logging, metrics, tracing, alerting, health/readiness signals;
- failure, retry, idempotency, recovery, restart, and rollback behavior;
- development, preview, staging, and production differences.

`PROJECT.yaml` contains machine-executable command arrays for install, build,
start, stop, full test, full Eval, smoke, and health check. README links to and
explains the same commands. The three artifacts must agree with observed behavior.

## Final runtime verification

On the delivery commit and a clean environment:

1. install dependencies without undocumented local state;
2. build the project;
3. start it with approved configuration;
4. wait for and verify health/readiness;
5. execute smoke and critical runtime journeys;
6. inspect logs for errors and sensitive data;
7. execute full tests and applicable Eval in the stated environment;
8. stop cleanly, restart, and verify recovery;
9. verify the rollback method or record the risk-tier-approved exercise evidence.

Record command, commit, environment, time, exit status, observed signal, and
evidence path. A local dev server opening successfully is not production evidence.

## Safety rules

Never write a Secret to source, fixtures, logs, command output, documentation, or
`PROJECT.yaml` command argv. Commands reference executables and safe arguments;
credentials come from the approved runtime environment or Secret manager.
Use approved Secret systems and least privilege. Retry only confirmed transient
external failures, with a finite limit, backoff, observable logging, and idempotent
effects. Do not use retries or broad exception handling to hide a deterministic
defect. Data-changing startup, migration, or recovery actions require explicit
rollback and the applicable change gate.
