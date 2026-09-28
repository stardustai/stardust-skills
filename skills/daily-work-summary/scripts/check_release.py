#!/usr/bin/env python3
"""检查发布文件、Markdown 本地链接和明显敏感值；不是完整安全审计。"""

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP = {".git", "__pycache__", ".venv", "node_modules", ".DS_Store"}
FORBIDDEN = {"config.json", "evidence.json", "findings.json", "manifest.json", "draft.md", "report.md", ".storage_state.json"}


def main():
    errors = []
    if (ROOT / ".git").exists():
        result = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT, capture_output=True, check=True)
        files = [ROOT / item.decode("utf-8") for item in result.stdout.split(b"\0") if item]
    else:
        files = [p for p in ROOT.rglob("*") if p.is_file() and not any(part in SKIP for part in p.relative_to(ROOT).parts)]
    for path in files:
        relative = path.relative_to(ROOT)
        if path.is_symlink():
            errors.append(str(relative) + "：发布文件不能是符号链接")
            continue
        if path.name in FORBIDDEN or path.name.startswith(".env") or any(x in {"runs", "outputs", "__pycache__"} for x in relative.parts) or path.suffix in {".pyc", ".log", ".jsonl"}:
            errors.append(str(relative) + "：不应发布真实运行数据或状态")
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeError, OSError):
            errors.append(str(relative) + "：发布清单含非文本或不可读文件，请人工核查")
            continue
        checks = [r"gh[pousr]_[A-Za-z0-9]{30,}", r"github_pat_[A-Za-z0-9_]{30,}",
                  r"sk-[A-Za-z0-9_-]{30,}", r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", r"/Users/" + "mac/"]
        if any(re.search(pattern, content) for pattern in checks):
            errors.append(str(relative) + "：含疑似真实凭证或个人绝对路径；不显示命中值")
        if path.suffix == ".md":
            for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
                if "://" in target or target.startswith("#"):
                    continue
                link = target.split("#")[0]
                if link and not (path.parent / link).is_file():
                    errors.append(str(relative) + "：本地链接不存在：" + link)
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    if not skill.startswith("---\nname: daily-work-summary\ndescription:") or "[TODO" in skill:
        errors.append("SKILL.md：元数据或模板未完成")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("发布检查通过：%d 个文件；未发现已知敏感模式、运行数据或断开的本地文档链接。仍需人工审核。" % len(files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
