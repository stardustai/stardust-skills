# Deployment Standard

## Contents

- Docker
- Kubernetes structure
- Runtime configuration
- Database migration job
- Deploy scripts
- Release and rollback

## Docker

Use separate images for web and api unless the repository already has a proven combined deployment.

Required practices:

- Multi-stage builds.
- Non-root runtime user.
- No secrets baked into images.
- Deterministic package manager install.
- Healthcheck or Kubernetes probes.
- Small runtime image with only required artifacts.

## Kubernetes Structure

Use this structure for manifests:

```text
infra/k8s/
├── base/
│   ├── web-deployment.yaml
│   ├── web-service.yaml
│   ├── api-deployment.yaml
│   ├── api-service.yaml
│   ├── ingress.yaml
│   ├── migration-job.yaml
│   └── kustomization.yaml
└── overlays/
    ├── dev/kustomization.yaml
    ├── staging/kustomization.yaml
    └── prod/kustomization.yaml
```

Each production workload needs:

- `readinessProbe` and `livenessProbe`.
- CPU/memory requests and limits.
- `ConfigMap` or environment references for non-secret config.
- `Secret` references for sensitive config.
- Rolling update strategy.
- Labels for app, component, environment, and version.
- Ingress rules owned by the environment overlay.

## Runtime Configuration

- Frontend runtime config should be injected safely per environment.
- Backend must fail fast when required config is missing or invalid.
- Do not use production database credentials in local/dev manifests.
- Avoid hardcoded namespace, host, image tag, or database URL in base manifests.

## Database Migration Job

- Run migrations as a Kubernetes `Job` or CI/CD pre-deploy step.
- Migration job must use the same app image or a dedicated migration image.
- Migration failure must block rollout.
- Destructive migrations require manual approval and rollback/mitigation notes.

## Deploy Scripts

Standard scripts:

```text
scripts/build.sh      # build packages and images
scripts/test.sh       # lint, typecheck, unit/integration tests
scripts/migrate.sh    # run or render migrations for an environment
scripts/deploy.sh     # apply k8s manifests or call the CD system
scripts/rollback.sh   # rollback to the previous known-good version
```

Scripts should be thin wrappers around deterministic commands. They must accept environment and image tag inputs rather than editing files in place.

## Release And Rollback

Before production:

- Confirm app version and image tags.
- Confirm migration plan and compatibility.
- Render manifests for the target environment.
- Confirm probes, resources, and secrets exist.
- Confirm rollback command and previous version.
- Confirm smoke tests after rollout.
