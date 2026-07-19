#!/usr/bin/env python3
"""在临时目录中测试识别、幂等生成、非生产验证和生产门禁。"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent


def run(*args: object, expect: int = 0) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, *map(str, args)]
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if result.returncode != expect:
        details = ""
        if "--report-dir" in command:
            report_dir = Path(command[command.index("--report-dir") + 1])
            report = report_dir / "validation-report.json"
            if report.exists():
                details = "\n" + report.read_text(encoding="utf-8")
        raise RuntimeError(f"命令返回 {result.returncode}，期望 {expect}: {' '.join(command)}\n{result.stdout}{details}")
    return result


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="production-devops-sre-test-") as directory:
        root = Path(directory)
        app = root / "orders-platform"
        app.mkdir()
        (app / "package.json").write_text('{"name":"orders-platform"}\n', encoding="utf-8")
        (app / "server.js").write_text("const PORT = 9090;\n", encoding="utf-8")
        inputs = root / "deploy-inputs.json"
        run(HERE / "inspect_project.py", app, "--output", inputs)
        candidate = root / "candidate-deploy"
        run(HERE / "generate_deployment.py", inputs, "--output", candidate)
        run(HERE / "validate_deployment.py", candidate, "--report-dir", root / "report-candidate")
        run(HERE / "validate_deployment.py", candidate, "--production", "--report-dir", root / "report-candidate-prod", expect=1)
        data = json.loads(inputs.read_text(encoding="utf-8"))
        digest = "registry.example.invalid/team/app@sha256:" + "a" * 64
        api = data["services"][0]
        api.update({"name": "api", "image": digest, "port": 9090, "expose": True, "requires_confirmation": []})
        data["services"].extend([
            {"name": "worker", "module": ".", "workload": "worker", "runtime": "node", "image": digest,
             "port": 9091, "health_path": None, "ready_path": None, "probe_command": ["node", "healthcheck.js"],
             "expose": False, "ingress_path": "/", "uid": 10000, "gid": 10000, "data_path": None, "storage_size": None},
            {"name": "store", "module": ".", "workload": "stateful", "runtime": "unknown", "image": digest,
             "port": 8081, "health_path": "/healthz", "ready_path": "/readyz", "expose": False,
             "compose_healthcheck": ["CMD", "/app/healthcheck"], "ingress_path": "/store", "uid": 10000,
             "gid": 10000, "data_path": "/data", "storage_size": "10Gi"},
            {"name": "schema-migration", "module": ".", "workload": "migration", "runtime": "unknown", "image": digest,
             "migration_command": ["/app/migrate", "up"], "uid": 10000, "gid": 10000},
        ])
        inputs.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        deploy = root / "deploy"
        run(HERE / "generate_deployment.py", inputs, "--output", deploy)
        first = tree_hash(deploy)
        run(HERE / "generate_deployment.py", inputs, "--output", deploy)
        if first != tree_hash(deploy):
            raise RuntimeError("相同输入重复生成的文件摘要不同")
        without_store = dict(data)
        without_store["services"] = [service for service in data["services"] if service["name"] != "store"]
        inputs.write_text(json.dumps(without_store, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        run(HERE / "generate_deployment.py", inputs, "--output", deploy)
        if any(path.name.startswith("store-") for path in (deploy / "k8s").glob("*.yaml")):
            raise RuntimeError("删除服务后残留旧生成清单")
        inputs.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        run(HERE / "generate_deployment.py", inputs, "--output", deploy)
        if first != tree_hash(deploy):
            raise RuntimeError("恢复输入后未收敛到原始文件摘要")
        run(HERE / "render_change_ticket.py", inputs, "--output", root / "change-ticket.md")
        run(HERE / "render_domain_request.py", inputs, "--output", root / "domain-request.md")
        run(HERE / "validate_deployment.py", deploy, "--report-dir", root / "report-nonprod")
        run(HERE / "validate_deployment.py", deploy, "--production", "--report-dir", root / "report-blocked", expect=1)
        data.update({
            "domain": "orders.example.com", "change_ticket": "CHG-2026-0001",
            "domain_request": "DNS-2026-0001", "first_cicd_approved": True,
        })
        inputs.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        run(HERE / "generate_deployment.py", inputs, "--output", deploy)
        result = run(HERE / "validate_deployment.py", deploy, "--production", "--report-dir", root / "report-production")
        report = json.loads((root / "report-production/validation-report.json").read_text(encoding="utf-8"))
        if report["status"] != "pass":
            raise RuntimeError(result.stdout)
        gate = subprocess.run([str(HERE / "ci_release_gate.sh"), str(deploy), str(root / "report-ci")],
                              text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        if gate.returncode != 0:
            raise RuntimeError(f"CI 门禁失败：\n{gate.stdout}")
    print("SELF TEST PASS：识别、幂等生成、工单、域名、非生产验证和生产阻断均符合预期。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
