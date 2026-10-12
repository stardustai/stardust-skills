"""从授权本地仓库采集 Git 记录，不修改仓库或联网更新引用。"""

import re
from pathlib import Path

from .common import in_window, run, safe_text, stable_id


_GIT = ["git", "--no-optional-locks", "-c", "core.quotepath=false", "-c", "core.fsmonitor=false"]
_DIFF = ["--no-ext-diff", "--no-textconv", "--no-renames", "--no-color"]
_COAUTHOR = re.compile(r"^Co-authored-by:\s*[^\r\n<]*<([^<>\r\n]+)>\s*$", re.I | re.M)
_SENSITIVE = re.compile(
    r"(?:^|/)\.env(?:[./]|$)|(?:^|[/._-])(?:keys?|tokens?|credentials?|secrets?|passwords?|passwd|private[_-]key)(?:[/._-]|$)|"
    r"(?:^|/)(?:\.netrc|\.npmrc|\.pypirc|id_rsa|id_ed25519)(?:$|/)|"
    r"\.(?:pem|p12|pfx|jks|keystore)$|(?:^|/)\.docker/config\.json$",
    re.I,
)
_MAX_FILES = 2000


def _git(path, arguments, timeout, output_limit=2_000_000):
    return run(_GIT + arguments, cwd=str(path), timeout=timeout,
               max_output_bytes=output_limit)


def _number(value, default):
    try:
        return max(1, int(value))
    except (TypeError, ValueError, OverflowError):
        return default


def _inside(path, roots):
    return any(path == root or root in path.parents for root in roots)


def _unique(values):
    return list(dict.fromkeys(values))


def _clip(content, limit, warnings):
    content = safe_text(content)
    if len(content) > limit:
        warnings.append("内容超过 max_content_chars，已截断。")
        return content[:limit]
    return content


def _paths(output):
    """解析禁用重命名检测的 --name-status -z 输出。"""
    fields = output.split("\0")[:-1]
    return [{"status": fields[i], "path": fields[i + 1]}
            for i in range(0, len(fields) - 1, 2)
            if fields[i] and fields[i + 1]]


def _changed_files(path, revision, parents, timeout, warnings):
    if parents:
        arguments = ["diff"] + _DIFF + ["--name-status", "-z", parents[0], revision, "--"]
    else:
        arguments = (["diff-tree", "--root", "--no-commit-id", "-r"] + _DIFF
                     + ["--name-status", "-z", revision, "--"])
    result = _git(path, arguments, timeout)
    if result.returncode and not result.truncated:
        warnings.append("无法读取此提交的文件清单。")
        return [], False
    if result.truncated:
        warnings.append("提交文件清单输出达到上限，已截断。")
    return _paths(result.stdout), not result.truncated


def _patch(path, files, timeout, limit, warnings, revision=None, parents=None, staged=False):
    filtered = [entry["path"] for entry in files if _SENSITIVE.search(entry["path"])]
    allowed = [entry["path"] for entry in files if not _SENSITIVE.search(entry["path"])]
    if filtered:
        warnings.append("已过滤敏感文件的 diff，仅保留文件名和状态。")
    if len(allowed) > _MAX_FILES:
        warnings.append("可读取的 diff 文件数达到上限，已截断。")
        allowed = allowed[:_MAX_FILES]
    if not allowed:
        return "", filtered
    if revision and not parents:
        arguments = ["show", "--format=", "--root", "--patch"] + _DIFF + [revision]
    else:
        arguments = ["diff"] + _DIFF
        if staged:
            arguments.append("--cached")
        if revision:
            arguments.extend([parents[0], revision])
    arguments.extend(["--"] + [":(literal)" + name for name in allowed])
    result = _git(path, arguments, timeout, max(4096, min(2_000_000, limit * 4)))
    if result.returncode and not result.truncated:
        warnings.append("无法读取实际 diff。")
        return "", filtered
    if result.truncated:
        warnings.append("实际 diff 输出达到上限，已截断。")
    return result.stdout, filtered


def _safe_files(files):
    return [{"path": safe_text(entry["path"]), "status": entry["status"]} for entry in files]


def _worktree(path, project, window, timeout, limit):
    result = _git(path, ["-c", "status.renames=false", "status", "--porcelain=v1", "-z",
                         "--untracked-files=normal"], timeout)
    if result.returncode and not result.truncated:
        raise RuntimeError("工作区状态读取失败")
    warnings = []
    if result.truncated:
        warnings.append("工作区状态输出达到上限，已截断。")
    files = [{"status": value[:2], "path": value[3:]}
             for value in result.stdout.split("\0")[:-1] if len(value) > 3]
    if not files:
        return None, warnings
    warnings.append("未提交修改的发生日期和作者无法由当前工作区确认；不计为当天完成。")
    tracked = [entry for entry in files if entry["status"] != "??"]
    untracked = [entry["path"] for entry in files if entry["status"] == "??"]
    if untracked:
        warnings.append("未跟踪文件只记录文件名，未读取内容。")
    staged, filtered = _patch(path, tracked, timeout, limit, warnings, staged=True)
    unstaged, _ = _patch(path, tracked, timeout, limit, warnings)
    content = "工作区观察记录；发生时间和贡献者未知。\n"
    content += "\n".join(entry["status"] + " " + entry["path"] for entry in files)
    if staged:
        content += "\n\n已暂存 diff：\n" + staged
    if unstaged:
        content += "\n\n未暂存 diff：\n" + unstaged
    item = {
        "id": stable_id("git-worktree", str(path)), "source": "git", "kind": "worktree",
        "project": project, "title": "工作区存在未提交修改（日期未知）",
        "locator": safe_text(str(path)), "event_time": None, "time_basis": "unknown",
        "attribution": "unknown", "content": _clip(content, limit, warnings),
        "verification": "record_only", "warnings": _unique(warnings),
        "metadata": {"observed_at": window.get("observed_at"), "files": _safe_files(files),
                     "filtered_files": [safe_text(name) for name in filtered],
                     "untracked_files": [safe_text(name) for name in untracked]},
    }
    return item, warnings


def _commit(path, project, fields, emails, window, timeout, limit):
    revision, parent_text, author_email, committer_email, authored_at, committed_at, message = fields
    author_in_window = in_window(authored_at, window)
    committer_in_window = in_window(committed_at, window)
    if not (author_in_window or committer_in_window):
        return None
    if author_email.strip().casefold() in emails:
        attribution = "author"
    elif any(email.strip().casefold() in emails for email in _COAUTHOR.findall(message)):
        attribution = "coauthor"
    elif committer_email.strip().casefold() in emails:
        attribution = "committer"
    else:
        return None
    warnings = []
    if attribution == "committer":
        description = "本人仅匹配提交者；原始作者为他人，不能据此认定为本人开发。"
        warnings.append(description)
    elif attribution == "coauthor":
        description = "提交声明本人为共同作者；具体贡献比例未经核验。"
    else:
        description = "本人匹配提交作者；提交记录不代表测试通过、发布或实际耗时。"
    if not author_in_window:
        warnings.append("作者时间在统计窗口外；此记录按提交时间进入候选，属于历史创作的提交或合入。")
    if not committer_in_window:
        warnings.append("提交时间在统计窗口外；此记录仅作者时间位于窗口内。")
    use_author_time = author_in_window and attribution != "committer"
    if attribution == "committer" and not committer_in_window:
        use_author_time = True
        warnings.append("本人作为提交者的动作不在统计窗口内，不可算为本人当天提交。")
    parents = parent_text.split()
    files, _ = _changed_files(path, revision, parents, timeout, warnings)
    patch, filtered = _patch(path, files, timeout, limit, warnings, revision, parents)
    if len(parents) > 1:
        warnings.append("合并提交的 diff 相对第一父提交；其中可包含他人改动，不代表全部由本人编写。")
    content = description + "\n作者时间：" + authored_at + "\n提交时间：" + committed_at
    content += "\n\n提交说明：\n" + message.rstrip()
    content += "\n\n文件清单：\n" + "\n".join(entry["status"] + " " + entry["path"] for entry in files)
    if patch:
        content += "\n\n实际 diff：\n" + patch
    return {
        "id": stable_id("git-commit", revision), "source": "git", "kind": "commit",
        "project": project, "title": safe_text(message.splitlines()[0] if message.strip() else revision[:12]),
        "locator": safe_text(str(path)) + "@" + revision,
        "event_time": authored_at if use_author_time else committed_at,
        "time_basis": "author_time" if use_author_time else "committer_time",
        "attribution": attribution, "content": _clip(content, limit, warnings),
        "verification": "record_only", "warnings": _unique(warnings),
        "metadata": {"commit": revision, "parents": parents, "author_email": safe_text(author_email),
                     "committer_email": safe_text(committer_email), "authored_at": authored_at,
                     "committed_at": committed_at, "author_in_window": author_in_window,
                     "committer_in_window": committer_in_window, "is_merge": len(parents) > 1,
                     "files": _safe_files(files), "filtered_files": [safe_text(name) for name in filtered]},
    }


def collect(config: dict, window: dict) -> dict:
    """采集本地引用、授权工作区及匹配身份的提交；范围为 [start, end)。"""
    settings = config.get("git", {})
    repositories = settings.get("repositories", [])
    output = {"source": "git", "status": "not_configured", "scope": [], "items": [], "gaps": []}
    if not repositories:
        return output
    limits = config.get("limits", {})
    timeout = _number(limits.get("timeout_seconds"), 30)
    limit = _number(limits.get("max_content_chars"), 20_000)
    cap = _number(settings.get("max_commits"), 500)
    emails = {str(email).strip().casefold() for email in config.get("identity", {}).get("git_emails", [])
              if str(email).strip()}
    if not emails:
        output["gaps"].append("未配置本人 Git 邮箱，无法归属提交；请设置 identity.git_emails。")
    roots = []
    for repository in repositories:
        try:
            roots.append(Path(repository["path"]).expanduser().resolve())
        except (KeyError, TypeError, ValueError, OSError):
            output["gaps"].append("仓库配置缺少有效 path。")
    seen_roots, seen_worktrees, seen_commits = set(), set(), {}
    usable = 0
    for repository in repositories:
        try:
            path = Path(repository["path"]).expanduser().resolve()
        except (KeyError, TypeError, ValueError, OSError):
            continue
        if path in seen_roots:
            continue
        seen_roots.add(path)
        project = safe_text(str(repository.get("name") or path.name))
        label = project + "（" + safe_text(str(path)) + "）"
        output["scope"].append(label + "：本地全部引用及 HEAD；远端跟踪引用仅为已有本地快照，未联网更新。")
        if not path.is_dir():
            output["gaps"].append(label + "：目录不存在或不是目录。")
            continue
        try:
            bare_result = _git(path, ["rev-parse", "--is-bare-repository"], timeout)
            if bare_result.returncode:
                output["gaps"].append(label + "：不是可读取的 Git 仓库。")
                continue
            bare = bare_result.stdout.strip() == "true"
            root_result = _git(path, ["rev-parse", "--absolute-git-dir" if bare else "--show-toplevel"], timeout)
            if root_result.returncode or Path(root_result.stdout.strip()).resolve() != path:
                output["gaps"].append(label + "：配置路径不是仓库根目录，未读取授权路径外的父级仓库。")
                continue
            shallow = _git(path, ["rev-parse", "--is-shallow-repository"], timeout)
            if shallow.returncode or shallow.stdout.strip() == "true":
                output["gaps"].append(label + "：浅克隆或无法确认历史完整性。")
            worktrees = []
            heads = []
            tree_result = _git(path, ["worktree", "list", "--porcelain", "-z"], timeout)
            if tree_result.returncode and not tree_result.truncated:
                output["gaps"].append(label + "：无法枚举已有工作区。")
                if not bare:
                    worktrees.append(path)
            else:
                if tree_result.truncated:
                    output["gaps"].append(label + "：工作区清单输出达到上限，已截断。")
                for block in tree_result.stdout.split("\0\0"):
                    values = block.split("\0")
                    if not values or not values[0].startswith("worktree "):
                        continue
                    tree_path = Path(values[0][9:]).resolve()
                    if "bare" in values:
                        continue
                    if not _inside(tree_path, roots):
                        output["gaps"].append(label + "：发现配置路径外的工作区，未读取：" + safe_text(str(tree_path)))
                        continue
                    worktrees.append(tree_path)
                    heads.extend(value[5:] for value in values if value.startswith("HEAD ")
                                 and re.fullmatch(r"[0-9a-f]{40,64}", value[5:]) and set(value[5:]) != {"0"})
            # 不使用 --since：作者时间可乱序；--single-worktree 防止自动遍历未授权工作区。
            history = _git(path, ["log", "--single-worktree", "--all", "--max-count=" + str(cap + 1),
                                  "--no-show-signature", "-z", "--format=%H%x00%P%x00%ae%x00%ce%x00%aI%x00%cI%x00%B"]
                           + _unique(heads) + ["--"], timeout)
            if history.returncode and not history.truncated:
                output["gaps"].append(label + "：无法读取提交历史。")
                continue
            usable += 1
            if history.truncated:
                output["gaps"].append(label + "：提交历史输出达到上限，已截断。")
            fields = history.stdout.split("\0")[:-1]
            records = [fields[index:index + 7] for index in range(0, len(fields), 7)
                       if len(fields[index:index + 7]) == 7]
            if len(records) > cap:
                output["gaps"].append(label + "：历史扫描达到 max_commits=" + str(cap)
                                      + "，更早可达记录未检查，可能包含窗口内乱序时间记录。")
            if emails:
                for record in records[:cap]:
                    if not re.fullmatch(r"[0-9a-f]{40,64}", record[0]):
                        output["gaps"].append(label + "：提交记录格式无法完整解析。")
                        continue
                    if record[0] in seen_commits:
                        seen_commits[record[0]]["metadata"].setdefault("additional_locations", []).append(label)
                        continue
                    try:
                        item = _commit(path, project, record, emails, window, timeout, limit)
                    except (RuntimeError, OSError):
                        output["gaps"].append(label + "：提交 " + record[0][:12] + " 的 diff 读取失败或超时。")
                        continue
                    if item:
                        seen_commits[record[0]] = item
                        output["items"].append(item)
            if settings.get("include_worktree", True):
                for tree_path in _unique(worktrees):
                    if tree_path in seen_worktrees:
                        continue
                    seen_worktrees.add(tree_path)
                    try:
                        item, warnings = _worktree(tree_path, project, window, timeout, limit)
                        if item:
                            output["items"].append(item)
                        elif warnings:
                            output["gaps"].extend(label + "：" + warning for warning in warnings)
                    except (RuntimeError, OSError):
                        output["gaps"].append(label + "：授权工作区读取失败或超时：" + safe_text(str(tree_path)))
        except (RuntimeError, OSError, ValueError):
            output["gaps"].append(label + "：Git 采集失败或超时；未包含原始错误输出。")
    for item in output["items"]:
        for warning in item["warnings"]:
            if any(word in warning for word in ("截断", "无法读取", "过滤敏感")):
                output["gaps"].append(item["project"] + "：" + warning)
    output["gaps"] = _unique(output["gaps"])
    output["status"] = "unavailable" if not usable else "partial" if output["gaps"] else "complete"
    return output
