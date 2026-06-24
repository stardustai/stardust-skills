#!/usr/bin/env python3
"""Run first-pass source/config pattern rules for Dengbao code audit."""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "dist",
    "build",
    "target",
    ".next",
    ".nuxt",
    ".venv",
    "venv",
    "__pycache__",
    "coverage",
    ".idea",
    ".vscode",
    ".turbo",
    ".cache",
    "reports",
    "dengbao-code-audit",
}

TEXT_EXTENSIONS = {
    ".js", ".jsx", ".ts", ".tsx", ".vue", ".java", ".kt", ".go", ".py", ".php", ".rb",
    ".cs", ".xml", ".yml", ".yaml", ".json", ".toml", ".ini", ".properties", ".conf",
    ".env", ".sh", ".sql", ".md", ".dockerfile", ".gradle",
}

SENSITIVE_REDACTIONS = [
    re.compile(r"(?i)(password|passwd|pwd|secret|token|access[_-]?key|private[_-]?key|jwt[_-]?secret)(\s*[:=]\s*)(['\"]?)[^'\"\s]+"),
    re.compile(r"(?i)(authorization:\s*bearer\s+)[A-Za-z0-9._\-]+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
]


@dataclass(frozen=True)
class Rule:
    id: str
    category: str
    severity: str
    title: str
    pattern: str
    description: str
    recommendation: str
    file_hint: str = ""


RULES: list[Rule] = [
    Rule(
        "AUTH-001", "登录认证", "高危", "疑似硬编码账号、密码或密钥",
        r"(?i)\b(password|passwd|pwd|secret|token|access[_-]?key|jwt[_-]?secret)\b\s*[:=]\s*['\"][^'\"\n]{6,}['\"]",
        "源码或配置中疑似出现硬编码敏感凭据。",
        "迁移到密钥管理或安全环境变量；轮换已泄露凭据；报告中不要暴露真实值。",
    ),
    Rule(
        "AUTH-002", "登录认证", "中危", "疑似弱口令或默认口令",
        r"(?i)(123456|admin123|password|default[_-]?password|初始密码|默认密码)",
        "项目中出现弱口令、默认密码或初始密码线索。",
        "禁止默认弱口令；首次登录强制修改；增加密码复杂度和失败锁定。",
    ),
    Rule(
        "AUTH-003", "登录认证", "中危", "JWT 或 Session 过期时间过长",
        r"(?i)(expiresIn|expiration|timeout|maxAge)\s*[:=]\s*['\"]?(\d{7,}|[3-9]\d+d|[1-9]\d{2,}h)",
        "令牌或会话有效期疑似过长。",
        "按系统风险设置短期 access token 和可控 refresh token；退出登录后失效。",
    ),
    Rule(
        "PERM-001", "权限控制", "高危", "疑似接口跳过鉴权或匿名访问范围过宽",
        r"(?i)(permitAll|anonymous|skipAuth|ignoreAuth|noAuth|publicRoute|@Public\(|AllowAnonymous|无需登录)",
        "发现跳过鉴权或公开路由标记，需要确认是否误放到敏感接口。",
        "公开路由必须白名单化；后台和数据接口默认鉴权；补充权限测试。",
    ),
    Rule(
        "PERM-002", "权限控制", "中危", "疑似直接信任请求中的用户或租户标识",
        r"(?i)(req\.body|req\.query|request\.getParameter|params|query)\s*.*\b(userId|tenantId|orgId|roleId)\b",
        "接口可能直接使用客户端传入的用户、租户或角色标识。",
        "从认证上下文获取身份和租户；对资源 owner 和数据权限做后端校验。",
    ),
    Rule(
        "AUDIT-001", "安全审计", "中危", "疑似敏感信息写入日志",
        r"(?i)(log\.|logger\.|console\.)[^;\n]*(password|passwd|token|secret|idCard|身份证|手机号|mobile)",
        "日志语句可能输出敏感字段。",
        "对敏感字段脱敏；审计日志和业务日志区分；禁止记录密码、token、私钥。",
    ),
    Rule(
        "DATA-001", "数据安全", "高危", "疑似私钥或证书材料入库",
        r"-----BEGIN (RSA |EC |OPENSSH |DSA |)?PRIVATE KEY-----",
        "仓库中出现私钥内容。",
        "立即移除并轮换密钥；使用密钥管理；检查提交历史。",
    ),
    Rule(
        "DATA-002", "数据安全", "中危", "疑似弱哈希算法",
        r"(?i)\b(md5|sha1)\s*\(",
        "发现 MD5/SHA1 调用，若用于密码或签名安全场景风险较高。",
        "密码使用 bcrypt/argon2/PBKDF2；签名或完整性校验使用更安全算法。",
    ),
    Rule(
        "API-001", "接口安全", "高危", "疑似 SQL 拼接",
        r"(?i)(select|insert|update|delete)\s+[^;\n]*(\+|\$\{|format\(|StringBuilder|concat\()",
        "SQL 语句疑似通过字符串拼接构造。",
        "使用参数化查询、ORM 安全 API 或预编译语句；重点检查用户输入来源。",
    ),
    Rule(
        "API-002", "接口安全", "高危", "疑似命令执行",
        r"(?i)(child_process\.(exec|spawn|execFile)|Runtime\.getRuntime\(\)\.exec|ProcessBuilder|subprocess\.(Popen|run|call)|os\.system|shell_exec|exec\()",
        "发现系统命令执行 API。",
        "禁止用户输入进入 shell；使用白名单命令和参数数组；记录审计。",
    ),
    Rule(
        "API-003", "接口安全", "高危", "疑似 SSRF 风险",
        r"(?i)(requests\.get|requests\.post|axios\.(get|post)|fetch\(|http\.get|https\.get|RestTemplate|WebClient)[^;\n]*(url|uri|link|target|callback)",
        "服务端可能请求用户可控 URL。",
        "限制协议、域名、端口；阻断内网地址；使用业务白名单。",
    ),
    Rule(
        "API-004", "接口安全", "中危", "危险 HTML 渲染",
        r"(dangerouslySetInnerHTML|v-html|innerHTML\s*=|bypassSecurityTrustHtml)",
        "前端或模板中直接渲染 HTML。",
        "避免渲染不可信 HTML；必须使用可信消毒库并限制标签属性。",
    ),
    Rule(
        "API-005", "接口安全", "中危", "文件上传控制疑似不足",
        r"(?i)(multer\.any\(|upload\.any\(|MultipartFile|request\.files|FileStorage|originalname|filename\s*=)",
        "发现文件上传相关实现，需要检查类型、大小、内容和路径控制。",
        "校验扩展名/MIME/大小/内容；重命名存储；禁止可执行目录；增加审计。",
    ),
    Rule(
        "TRANS-001", "传输安全", "中危", "疑似明文 HTTP 地址",
        r"http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)[A-Za-z0-9_.:/?=&%#@\-]+",
        "发现非本地明文 HTTP 地址。",
        "公网和敏感接口使用 HTTPS；内部传输敏感数据需加密或专网隔离。",
    ),
    Rule(
        "TRANS-002", "传输安全", "中危", "Cookie 安全属性疑似缺失",
        r"(?i)(setCookie|res\.cookie|cookie)\s*\([^;\n]*(?!httpOnly|secure|sameSite)",
        "Cookie 设置语句可能缺少 HttpOnly/Secure/SameSite。",
        "登录态 Cookie 设置 HttpOnly、Secure、SameSite，并配合 HTTPS。",
    ),
    Rule(
        "OPS-001", "运维暴露面", "高危", "疑似暴露高危服务端口",
        r"(?m)(^|\s|-\s)(22|3306|5432|6379|27017|9200|9300|15672|5672|9092|9090|3000|8080|8848)\s*:\s*\2\b",
        "部署配置可能将 SSH、数据库、缓存、MQ、管理端口直接映射。",
        "内部服务不得公网暴露；使用内网、VPN、白名单、堡垒机或受控网关。",
        "docker/k8s/yaml",
    ),
    Rule(
        "OPS-002", "运维暴露面", "中危", "生产调试或开发模式线索",
        r"(?i)(debug\s*[:=]\s*true|NODE_ENV\s*[:=]\s*development|SPRING_PROFILES_ACTIVE\s*[:=]\s*dev|DJANGO_DEBUG\s*[:=]\s*true)",
        "配置中出现调试或开发模式。",
        "生产关闭 debug/dev/mock；使用生产 profile；隐藏堆栈和调试端点。",
    ),
    Rule(
        "OPS-003", "运维暴露面", "中危", "Spring Actuator 暴露范围过大",
        r"(?i)management\.endpoints\.web\.exposure\.include\s*[:=]\s*['\"]?\*",
        "Actuator 端点可能全部暴露。",
        "只开放必要端点；敏感端点加认证、内网限制或关闭。",
    ),
    Rule(
        "CHANGE-001", "发布变更", "低危", "数据库变更缺少明显回滚线索",
        r"(?i)(alter\s+table|drop\s+table|truncate\s+table|delete\s+from)",
        "发现高影响 SQL 变更，需要确认是否有回滚或修正方案。",
        "数据库变更必须评审；准备回滚或修正脚本；发布后验证。",
        ".sql/migration",
    ),
]


def iter_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS and not d.startswith(".egg")]
        for filename in filenames:
            path = Path(dirpath) / filename
            try:
                if path.is_file():
                    yield path
            except OSError:
                continue


def is_text_candidate(path: Path, max_bytes: int) -> bool:
    try:
        if path.stat().st_size > max_bytes:
            return False
    except OSError:
        return False
    name = path.name.lower()
    suffix = path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        return True
    if name in {"dockerfile", "jenkinsfile", ".env", ".env.example", "nginx.conf"}:
        return True
    if any(name.endswith(ext) for ext in (".env", ".conf", ".properties")):
        return True
    return False


def redact(text: str) -> str:
    result = text.strip()
    for pattern in SENSITIVE_REDACTIONS:
        result = pattern.sub(lambda m: f"{m.group(1)}{m.group(2) if len(m.groups()) >= 2 else ''}<redacted>", result)
    if len(result) > 240:
        result = result[:237] + "..."
    return result


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def file_hint_matches(rule: Rule, path: Path) -> bool:
    if not rule.file_hint:
        return True
    hint = rule.file_hint.lower()
    lower = str(path).lower()
    if hint == ".sql/migration":
        return path.suffix.lower() == ".sql" or "migration" in lower or "migrations" in lower
    if hint == "docker/k8s/yaml":
        return any(token in lower for token in ("docker", "compose", "k8s", "kubernetes", ".yml", ".yaml"))
    return hint in lower


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", help="Project root to scan")
    parser.add_argument("--output", "-o", help="Write JSON output to file")
    parser.add_argument("--max-bytes", type=int, default=1_000_000)
    parser.add_argument("--max-findings-per-rule", type=int, default=80)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        raise SystemExit(f"Root does not exist: {root}")

    compiled = [(rule, re.compile(rule.pattern)) for rule in RULES]
    counts_by_rule: dict[str, int] = {rule.id: 0 for rule in RULES}
    findings: list[dict] = []
    scanned_files = 0

    for path in iter_files(root):
        if not is_text_candidate(path, args.max_bytes):
            continue
        scanned_files += 1
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for line_number, line in enumerate(lines, 1):
            if not line.strip():
                continue
            for rule, pattern in compiled:
                if counts_by_rule[rule.id] >= args.max_findings_per_rule:
                    continue
                if not file_hint_matches(rule, path):
                    continue
                if pattern.search(line):
                    counts_by_rule[rule.id] += 1
                    item = asdict(rule)
                    item.update({
                        "file": rel(path, root),
                        "line": line_number,
                        "evidence": redact(line),
                        "confidence": "medium",
                    })
                    findings.append(item)

    summary = {
        "root": str(root),
        "scanned_files": scanned_files,
        "finding_count": len(findings),
        "counts_by_severity": {},
        "counts_by_category": {},
        "counts_by_rule": {k: v for k, v in counts_by_rule.items() if v},
        "findings": findings,
        "notes": [
            "Pattern findings require manual code-flow review before final reporting.",
            "Evidence snippets are redacted heuristically; do not paste real secrets into reports.",
        ],
    }
    for finding in findings:
        summary["counts_by_severity"][finding["severity"]] = summary["counts_by_severity"].get(finding["severity"], 0) + 1
        summary["counts_by_category"][finding["category"]] = summary["counts_by_category"].get(finding["category"], 0) + 1

    output = json.dumps(summary, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
