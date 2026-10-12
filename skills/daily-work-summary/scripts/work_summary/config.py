"""显式范围配置；不自动发现或扩大私人目录。"""

import copy
import json
from pathlib import Path
from zoneinfo import ZoneInfo


DEFAULTS = {
    "schema_version": 1,
    "company": {"name": ""},
    "timezone": "Asia/Shanghai",
    "identity": {"name": "", "git_emails": []},
    "git": {"repositories": [], "max_commits": 2000, "include_worktree": True},
    "local": {"roots": [], "include_globs": ["**/*"], "exclude_globs": [],
              "max_files": 500, "max_file_bytes": 3000000},
    "dingtalk": {"enabled": True, "profile": "", "queries": [], "nodes": [],
                 "max_pages": 10, "max_documents": 50, "page_size": 20},
    "limits": {"timeout_seconds": 30, "max_content_chars": 20000},
}


def load_config(path):
    path = Path(path).expanduser()
    if path.stat().st_size > 1000000:
        raise ValueError("配置文件过大")
    return validate_config(json.loads(path.read_text(encoding="utf-8")))


def validate_config(raw):
    if not isinstance(raw, dict):
        raise ValueError("配置必须是 JSON 对象")
    if set(raw) - set(DEFAULTS):
        raise ValueError("配置包含未知顶层字段，请检查 references/configuration.md")
    result = copy.deepcopy(DEFAULTS)
    for key, value in raw.items():
        if isinstance(result[key], dict):
            if not isinstance(value, dict):
                raise ValueError(key + " 必须是对象")
            extra = {"max_depth", "max_docx_uncompressed_bytes"} if key == "local" else set()
            if set(value) - set(result[key]) - extra:
                raise ValueError(key + " 包含未知字段")
            result[key].update(value)
        else:
            result[key] = value
    if result["schema_version"] != 1:
        raise ValueError("不支持的配置 schema_version")
    if not isinstance(result["company"]["name"], str) or not result["company"]["name"].strip():
        raise ValueError("必须明确 company.name，不能跨公司默认采集")
    ZoneInfo(result["timezone"])
    for section, key in [("identity", "git_emails"), ("local", "include_globs"), ("local", "exclude_globs"),
                         ("dingtalk", "queries"), ("dingtalk", "nodes")]:
        value = result[section][key]
        if not isinstance(value, list) or not all(isinstance(x, str) and x.strip() for x in value):
            raise ValueError(section + "." + key + " 必须是非空字符串组成的数组")
    for section, key, maximum in [("git", "max_commits", 100000), ("local", "max_files", 20000),
                                  ("local", "max_file_bytes", 50000000), ("dingtalk", "max_pages", 100),
                                  ("dingtalk", "max_documents", 1000), ("dingtalk", "page_size", 30),
                                  ("limits", "timeout_seconds", 120), ("limits", "max_content_chars", 500000)]:
        value = result[section][key]
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
            raise ValueError("%s.%s 须为 1～%s 的整数" % (section, key, maximum))
    for section, key in [("git", "include_worktree"), ("dingtalk", "enabled")]:
        if not isinstance(result[section][key], bool):
            raise ValueError(section + "." + key + " 必须为布尔值")
    if not isinstance(result["dingtalk"]["profile"], str):
        raise ValueError("dingtalk.profile 必须是字符串")
    for section, key in [("git", "repositories"), ("local", "roots")]:
        entries = result[section][key]
        if not isinstance(entries, list):
            raise ValueError(section + "." + key + " 必须是数组")
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                raise ValueError(section + " 的每个范围须含 path")
            allowed = {"path", "name"} if section == "git" else {"path", "project", "mode", "keywords"}
            if set(entry) - allowed:
                raise ValueError(section + " 范围包含未知字段")
            path = Path(entry["path"]).expanduser()
            if not path.is_absolute() or path.resolve() in (Path("/"), Path.home().resolve()):
                raise ValueError("范围须为明确的项目绝对路径，不能是根目录或整个家目录")
            entry["path"] = str(path)
            if section == "local":
                if entry.get("mode") not in ("workspace", "mixed"):
                    raise ValueError("local.roots.mode 须明确为 workspace 或 mixed")
                words = entry.get("keywords", [])
                if not isinstance(words, list) or not all(isinstance(w, str) and w.strip() for w in words):
                    raise ValueError("keywords 必须为非空字符串数组")
                if entry["mode"] == "mixed" and not words:
                    raise ValueError("mixed 目录必须提供公司或项目关键词")
    for key, maximum in [("max_depth", 32), ("max_docx_uncompressed_bytes", 16777216)]:
        if key in result["local"]:
            value = result["local"][key]
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
                raise ValueError("local." + key + " 超出安全范围")
    return result
