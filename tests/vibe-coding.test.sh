#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
skill_dir="$repo_root/skills/vibe-coding"

required=(
  SKILL.md
  README.md
  evals/evals.json
  scripts/self_test.py
  scripts/schema_runtime.py
  scripts/validate_project.py
  scripts/validate_traceability.py
  scripts/validate_feedback.py
  scripts/run_project_checks.py
  scripts/install_pre_commit.py
  scripts/validate_delivery.py
  assets/schemas/project.schema.json
  assets/schemas/task-feedback.schema.json
  assets/schemas/traceability.schema.json
  assets/schemas/evidence-manifest.schema.json
  assets/schemas/business-evidence.schema.json
  assets/schemas/review-evidence.schema.json
  assets/templates/PROJECT.yaml.tpl
  assets/templates/business-evidence.json.tpl
  assets/templates/README.md.tpl
  references/spec-input-contract.md
  references/technical-debt-standard.md
  references/loop-engineering-standard.md
  references/pull-request-standard.md
)

for path in "${required[@]}"; do
  test -f "$skill_dir/$path" || {
    echo "missing required vibe-coding asset: $path" >&2
    exit 1
  }
done

python3 - <<'PY' "$skill_dir/evals/evals.json" "$skill_dir/assets/schemas"
import json
import pathlib
import sys

eval_path = pathlib.Path(sys.argv[1])
schema_dir = pathlib.Path(sys.argv[2])
payload = json.loads(eval_path.read_text(encoding="utf-8"))
assert payload.get("skill_name") == "vibe-coding", "eval suite must target vibe-coding"
evals = payload.get("evals")
assert isinstance(evals, list) and len(evals) >= 12, "at least twelve behavior evals required"
names = {case.get("name") for case in evals}
required_names = {
    "existing-project-initialization-and-debt-choice",
    "unit-tests-only-false-completion",
    "multi-person-small-feature-direct-push",
    "large-feature-requires-pr",
    "single-owner-large-r1-direct-push",
    "small-r2-still-requires-pr",
    "repository-requires-human-review",
    "non-engineering-ready-spec-blocks-code",
}
assert required_names <= names, f"missing behavior evals: {sorted(required_names - names)}"
for path in schema_dir.glob("*.json"):
    json.loads(path.read_text(encoding="utf-8"))
PY

python3 "$skill_dir/scripts/self_test.py"

rg -q '^name: vibe-coding$' "$skill_dir/SKILL.md"
rg -q 'business_success_scenarios' "$skill_dir/SKILL.md"
rg -q 'qa-generated-test-case' "$skill_dir/SKILL.md"
rg -q 'production-devops-sre' "$skill_dir/SKILL.md"
rg -q 'subagent-driven-development' "$skill_dir/SKILL.md"

if rg -qi 'graphify (is required|must be|required gate)|必须(使用|运行).*graphify|强制(使用|运行).*graphify' "$skill_dir"; then
  echo "Graphify must not be a company-level vibe-coding requirement" >&2
  exit 1
fi

echo "vibe-coding repository checks passed"
