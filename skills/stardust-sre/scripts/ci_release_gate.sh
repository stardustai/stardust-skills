#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
deploy_dir=${1:-deploy}
report_dir=${2:-"$deploy_dir/validation"}

python3 "$script_dir/validate_deployment.py" "$deploy_dir" --production --report-dir "$report_dir"

if command -v conftest >/dev/null 2>&1; then
  conftest test "$deploy_dir/k8s" --policy "$script_dir/../assets/policies"
else
  echo "WARN: conftest 不可用，Rego Policy-as-Code 未执行" >&2
fi

if command -v kubeconform >/dev/null 2>&1 && command -v kubectl >/dev/null 2>&1; then
  rendered=$(mktemp "${TMPDIR:-/tmp}/sre-kustomize.XXXXXX.yaml")
  trap 'rm -f "$rendered"' EXIT HUP INT TERM
  kubectl kustomize "$deploy_dir/k8s" >"$rendered"
  kubeconform -strict -summary "$rendered"
fi

if command -v trivy >/dev/null 2>&1; then
  trivy config --exit-code 1 --severity HIGH,CRITICAL "$deploy_dir"
fi

echo "生产发布门禁通过；仍需保留工单、于海龙或授权代理人审批及首次 CI/CD 观测证据。"
