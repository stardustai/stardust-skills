#!/usr/bin/env python3
"""将可发布文件安装到新 Skill 目录，拒绝覆盖已有安装。"""

import argparse
import os
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INCLUDE = ("SKILL.md", "README.md", "config.example.json", "agents", "references", "scripts", "tests")


def install(destination):
    destination = Path(destination).expanduser().resolve() / "daily-work-summary"
    if destination == ROOT or ROOT in destination.parents:
        raise ValueError("安装目录不能位于源仓库内")
    if destination.exists():
        raise ValueError("已有同名安装，未覆盖；请先核对并另选目录或备份旧安装")
    for name in INCLUDE:
        if (ROOT / name).is_symlink():
            raise ValueError("发布包顶层包含符号链接，安装已停止：" + name)
    destination.mkdir(parents=True, mode=0o700)
    copied = 0
    for name in INCLUDE:
        source = ROOT / name
        for path in ([source] if source.is_file() else source.rglob("*")):
            if not path.is_file() or path.is_symlink() or "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            relative = path.relative_to(ROOT)
            if any(part.startswith(".") or part in {"runs", "outputs", "__pycache__"} for part in relative.parts):
                continue
            if path.name in {"draft.md", "report.md", "config.json", "evidence.json", "findings.json", "manifest.json"}:
                continue
            if name in {"scripts", "tests"} and path.suffix != ".py":
                continue
            if name == "references" and path.suffix != ".md":
                continue
            if name == "agents" and relative.as_posix() != "agents/openai.yaml":
                continue
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            shutil.copyfile(path, target)
            os.chmod(target, 0o600)
            copied += 1
    return destination, copied


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", default=str(Path.home() / ".agents/skills"), help="Skill 安装父目录，默认 ~/.agents/skills")
    args = parser.parse_args()
    try:
        target, count = install(args.dest)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print("已安装 %d 个文件到 %s；未复制配置、凭证或运行数据。" % (count, target))


if __name__ == "__main__":
    main()
