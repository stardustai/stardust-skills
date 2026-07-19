#!/usr/bin/env python3
"""验证 deploy/ 并输出机器可读及 Markdown 报告。"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path


PLACEHOLDERS = re.compile(r"<[^>]+>|__[A-Z0-9_]+__|pending-operations|pending-approval", re.I)
SECRET_WORDS = re.compile(
    r"(?im)^\s*(password|passwd|api[_-]?key|private[_-]?key|access[_-]?token|auth[_-]?token)"
    r"\s*:\s*[^$<{\s][^\s]*"
)


@dataclass
class Finding:
    severity: str
    rule: str
    message: str
    file: str | None = None


class Report:
    def __init__(self, root: Path, production: bool):
        self.root = root
        self.production = production
        self.findings: list[Finding] = []

    def add(self, severity: str, rule: str, message: str, path: Path | None = None) -> None:
        relative = str(path.relative_to(self.root)) if path and path.is_relative_to(self.root) else (str(path) if path else None)
        self.findings.append(Finding(severity, rule, message, relative))

    def error(self, rule: str, message: str, path: Path | None = None) -> None:
        self.add("error", rule, message, path)

    def warning(self, rule: str, message: str, path: Path | None = None) -> None:
        self.add("warning", rule, message, path)


def run(command: list[str], cwd: Path) -> tuple[int, str]:
    result = subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    return result.returncode, result.stdout.strip()


def check_yaml(report: Report, files: list[Path]) -> None:
    if shutil.which("ruby"):
        script = 'require "yaml"; ARGV.each { |f| YAML.load_stream(File.read(f)) }'
        code, output = run(["ruby", "-e", script, *map(str, files)], report.root)
        if code:
            report.error("yaml.parse", output or "YAML 解析失败")
    else:
        report.warning("yaml.tool", "未找到 Ruby/Psych；未执行基础 YAML 解析")


def check_compose(report: Report, compose: Path) -> None:
    if not compose.exists():
        report.error("compose.required", "缺少 docker-compose.yml", compose)
        return
    text = compose.read_text(encoding="utf-8")
    if re.search(r"(?m)^\s*(build|context)\s*:", text):
        report.error("compose.no-build", "Compose 禁止 build/context", compose)
    for required in ("read_only:", "cap_drop:", "no-new-privileges:true", "mem_limit:", "cpus:", "logging:", "networks:"):
        if required not in text:
            report.error("compose.baseline", f"Compose 缺少 {required}", compose)
    if SECRET_WORDS.search(text):
        report.error("secret.plaintext", "疑似包含明文敏感值", compose)
    if shutil.which("docker"):
        code, output = run(["docker", "compose", "-f", str(compose), "config"], report.root)
        if code:
            report.warning("compose.config", f"docker compose config 未通过或插件不可用：{output[:500]}", compose)
    else:
        report.warning("compose.tool", "未找到 docker，跳过 Compose 实现验证", compose)


def workload_checks(report: Report, path: Path, text: str) -> None:
    kind_match = re.search(r"(?m)^kind:\s*(Deployment|StatefulSet|Job)\s*$", text)
    if not kind_match:
        return
    kind = kind_match.group(1)
    for token in (
        "serviceAccountName:", "automountServiceAccountToken: false", "runAsNonRoot: true",
        "seccompProfile:", "allowPrivilegeEscalation: false", "readOnlyRootFilesystem: true",
        "capabilities:", "drop: [ALL]", "requests:", "limits:", "terminationGracePeriodSeconds:" if kind != "Job" else "activeDeadlineSeconds:",
    ):
        if token not in text:
            report.error("k8s.workload-security", f"{kind} 缺少 {token}", path)
    if kind in {"Deployment", "StatefulSet"}:
        for probe in ("startupProbe:", "readinessProbe:", "livenessProbe:"):
            if probe not in text:
                report.error("k8s.probes", f"{kind} 缺少 {probe}", path)
    if kind == "StatefulSet":
        for token in ("serviceName:", "volumeClaimTemplates:", "persistentVolumeClaimRetentionPolicy:", "whenDeleted: Retain", "whenScaled: Retain"):
            if token not in text:
                report.error("k8s.stateful", f"StatefulSet 缺少 {token}", path)


def check_kubernetes(report: Report, k8s: Path) -> None:
    files = sorted(k8s.glob("*.yaml")) + sorted(k8s.glob("*.yml"))
    if not files:
        report.error("k8s.required", "deploy/k8s 下没有 YAML", k8s)
        return
    check_yaml(report, files)
    kinds: dict[str, int] = {}
    for path in files:
        text = path.read_text(encoding="utf-8")
        for kind in re.findall(r"(?m)^kind:\s*([A-Za-z]+)\s*$", text):
            kinds[kind] = kinds.get(kind, 0) + 1
        if re.search(r"(?m)^kind:\s*Secret\s*$", text) and re.search(r"(?m)^\s*(data|stringData):\s*$", text):
            report.error("secret.committed", "禁止提交普通 Secret 数据；使用外部 Secret 或占位模板", path)
        if SECRET_WORDS.search(text):
            report.error("secret.plaintext", "疑似包含明文敏感值", path)
        workload_checks(report, path, text)
        if "kind: Ingress" in text:
            if "tls:" not in text:
                report.error("ingress.tls", "Ingress 缺少 TLS", path)
            if report.production and ("domain-approval: approved" not in text or ".invalid" in text):
                report.error("domain.approval", "生产 Ingress 域名尚未审批", path)
    for required in ("Namespace", "ServiceAccount", "NetworkPolicy"):
        if not kinds.get(required):
            report.error("k8s.resource", f"缺少 {required}")
    if kinds.get("StatefulSet") and not any("clusterIP: None" in p.read_text(encoding="utf-8") for p in files):
        report.error("k8s.headless", "StatefulSet 缺少 Headless Service")
    kustomization = k8s / "kustomization.yaml"
    if not kustomization.exists():
        report.error("kustomize.required", "缺少 kustomization.yaml", kustomization)
    elif shutil.which("kubectl"):
        code, output = run(["kubectl", "kustomize", str(k8s)], report.root)
        if code:
            report.error("kustomize.render", output or "kubectl kustomize 失败", kustomization)
    else:
        report.warning("kustomize.tool", "未找到 kubectl，跳过 Kustomize 渲染")


def check_release_gate(report: Report, path: Path) -> None:
    if not path.exists():
        report.error("release.gate", "缺少 release-gate.json", path)
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        report.error("release.gate", f"release-gate.json 无效：{error}", path)
        return
    if not report.production:
        return
    required_fields = ["change_ticket"]
    if data.get("external_access"):
        required_fields.extend(["domain_request", "domain"])
    for field in required_fields:
        value = str(data.get(field, ""))
        if not value or PLACEHOLDERS.search(value):
            report.error("release.approval", f"生产发布缺少已批准的 {field}", path)
    if data.get("first_cicd_approved") is not True:
        report.error("release.first-cicd", "首次 CI/CD 尚未经于海龙或授权代理人批准", path)
    if data.get("unconfirmed"):
        report.error("release.unconfirmed", f"仍有未经人工确认的探测字段：{data['unconfirmed']}", path)


def write_reports(report: Report, output: Path) -> tuple[int, int]:
    errors = sum(item.severity == "error" for item in report.findings)
    warnings = sum(item.severity == "warning" for item in report.findings)
    payload = {
        "status": "blocked" if errors else "pass",
        "production": report.production,
        "errors": errors,
        "warnings": warnings,
        "findings": [asdict(item) for item in report.findings],
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "validation-report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# 部署验证报告", "", f"- 结果：`{payload['status']}`", f"- 生产模式：`{report.production}`", f"- 错误：`{errors}`", f"- 警告：`{warnings}`", ""]
    for item in report.findings:
        location = f"（{item.file}）" if item.file else ""
        lines.append(f"- **{item.severity.upper()}** `{item.rule}`：{item.message}{location}")
    if not report.findings:
        lines.append("- 未发现问题。")
    (output / "validation-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("deploy", nargs="?", type=Path, default=Path("deploy"))
    parser.add_argument("--production", action="store_true", help="启用工单、域名、Digest 和首次 CI/CD 阻断")
    parser.add_argument("--report-dir", type=Path, default=Path("deploy/validation"))
    args = parser.parse_args()
    root = args.deploy.resolve()
    report = Report(root, args.production)
    if not root.is_dir():
        report.error("deploy.required", f"部署目录不存在：{root}")
    else:
        check_compose(report, root / "docker-compose.yml")
        check_kubernetes(report, root / "k8s")
        check_release_gate(report, root / "release-gate.json")
        for path in root.rglob("*"):
            if "validation" in path.relative_to(root).parts:
                continue
            if path.is_file() and path.suffix.lower() in {".yaml", ".yml", ".json", ".env"}:
                text = path.read_text(encoding="utf-8", errors="ignore")
                if args.production and PLACEHOLDERS.search(text):
                    report.error("placeholder.production", "生产文件仍包含待处理占位符", path)
                for image in re.findall(r"(?m)^\s*image:\s*[\"']?([^\s\"']+)", text):
                    if image.endswith(":latest"):
                        report.error("image.latest", "禁止 latest 镜像", path)
                    if args.production and "@sha256:" not in image:
                        report.error("image.digest", f"生产镜像未固定 Digest：{image}", path)
    errors, warnings = write_reports(report, args.report_dir.resolve())
    print(f"验证完成：{errors} 个错误，{warnings} 个警告；报告位于 {args.report_dir}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
