"""DWS 只读采集：组织锁定、时间筛选、分页与正文证据，不推断个人贡献。"""

import json
import math
import re
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import parse_qs, urlsplit, urlunsplit

from .common import parse_time, run, safe_text, stable_id


class ReadFailure(Exception):
    def __init__(self, message, fatal=False):
        super().__init__(message)
        self.fatal = fatal


def _layers(value):
    """只解开契约中的 data 包装，不遍历正文或任意业务字段。"""
    result = []
    for _ in range(5):
        if not isinstance(value, dict):
            break
        result.append(value)
        value = value.get("data")
    return result


def _flags(value, pagination=False):
    warnings = []
    for layer in _layers(value):
        status = str(layer.get("outcome", layer.get("status", ""))).lower()
        failed = layer.get("ok") is False or layer.get("success") is False
        if failed or status in {"failed", "failure", "error", "unknown", "unauthorized", "forbidden"}:
            error = layer.get("error", {})
            code = (error.get("code") or error.get("reason") or "") if isinstance(error, dict) else ""
            code = str(code or layer.get("code") or layer.get("reason") or "")
            # 错误消息和 stderr 可能含原始正文/签名链接，绝不落入报告。
            known_code = code if re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", code) else "未知错误"
            fatal = any(word in (code + " " + status).lower()
                        for word in ("auth", "permission", "forbid", "denied", "401", "403", "profile", "token"))
            raise ReadFailure("DWS 返回失败（%s）；未尝试登录、授权或切换组织" % known_code, fatal)
        if status and status not in {"success", "partial_success", "partial", "ok"}:
            raise ReadFailure("DWS 状态契约无法识别，停止该读取")
        if status in {"partial_success", "partial"}:
            warnings.append("DWS 返回部分成功，结果并不完整")
        if layer.get("complete") is False:
            has_continuation = layer.get("hasMore") is True and bool(layer.get("nextCursor"))
            if not (pagination and has_continuation):
                warnings.append("DWS 明确标记结果不完整")
        for key in ("failedItems", "failures", "errors"):
            if layer.get(key):
                warnings.append("DWS 返回失败项，未将其计为成功读取")
    return list(dict.fromkeys(warnings))


def _json_call(arguments, timeout, profile=None, cwd=None):
    args = ["dws"] + list(arguments)
    if profile:
        args += ["--profile", profile]
    args += ["--format", "json"]
    try:
        result = run(args, cwd=cwd, timeout=timeout)
    except RuntimeError as exc:
        # common.run 的异常不含 stderr；仍只给固定诊断，不暴露配置或正文。
        message = "DWS 执行超时" if "超时" in str(exc) else "DWS 无法启动或执行失败"
        raise ReadFailure(message) from None
    if result.truncated:
        raise ReadFailure("DWS 输出超过采集上限并被截断，不能作为完整结果")
    try:
        value = json.loads(result.stdout)
    except (ValueError, TypeError):
        raise ReadFailure("DWS 未返回有效 JSON；请检查 CLI 版本、登录或权限") from None
    if not isinstance(value, dict):
        raise ReadFailure("DWS 返回结构无法识别")
    _flags(value, pagination=True)
    if result.returncode:
        raise ReadFailure("DWS 执行失败（退出码 %s），原始错误未写入报告" % result.returncode)
    return value


def _select_profile(config, timeout):
    company = str(config.get("company", {}).get("name", "")).strip()
    if not company:
        raise ReadFailure("未配置 company.name，无法核验公司组织", True)
    response = _json_call(["profile", "list"], timeout)
    if _flags(response):
        raise ReadFailure("组织列表不完整，不能安全选择账号", True)
    profiles = next((x["profiles"] for x in _layers(response) if isinstance(x.get("profiles"), list)), None)
    if profiles is None or not all(isinstance(x, dict) for x in profiles):
        raise ReadFailure("DWS 组织列表结构无法识别", True)
    configured = config.get("dingtalk", {}).get("profile")
    matches = [p for p in profiles if str(p.get("corpName", "")).strip() == company]
    if configured:
        matches = [p for p in matches if p.get("profile") == configured]
    else:
        matches = [p for p in matches if p.get("isOrgCurrent") is True]
    if len(matches) != 1:
        raise ReadFailure("公司名称与账号不匹配，或没有唯一默认账号；请明确指定本公司 profile", True)
    selected = matches[0]
    if not isinstance(selected.get("profile"), str) or not selected["profile"]:
        raise ReadFailure("选定账号缺少稳定 profile", True)
    if selected.get("status") not in (None, "active"):
        raise ReadFailure("本公司账号未处于 active 状态，未自动登录或切换账号", True)
    return selected["profile"]


def _node(value):
    """仅接受稳定节点 ID 和已知钉钉节点链接，不解析分享短链。"""
    if not isinstance(value, str) or not value.strip():
        raise ReadFailure("节点 ID 为空或类型无效")
    value = value.strip()
    if "://" not in value:
        if re.fullmatch(r"[A-Za-z0-9_-]{1,256}", value) and not value.isdigit():
            return value
        raise ReadFailure("节点 ID 格式不支持，不能用纯数字 dentryId 代替节点 ID")
    parsed = urlsplit(value)
    if parsed.scheme != "https" or parsed.hostname != "alidocs.dingtalk.com" or parsed.username:
        raise ReadFailure("仅支持钉钉 alidocs HTTPS 节点链接")
    match = re.fullmatch(r"/i/nodes/([^/]+)/?", parsed.path)
    if match:
        return _node(match.group(1))
    if parsed.path in {"/document/edit", "/document/preview"}:
        ids = parse_qs(parsed.query).get("dentryKey", [])
        if len(ids) == 1:
            return _node(ids[0])
    raise ReadFailure("分享短链或其他链接格式暂不支持；未使用浏览器绕过")


def _locator(value, fallback):
    if not isinstance(value, str):
        return fallback
    parsed = urlsplit(value)
    if parsed.scheme == "https" and parsed.hostname == "alidocs.dingtalk.com" and not parsed.username:
        # 仅保留受控稳定节点路径，不保存临时签名、访问口令或追踪参数。
        if re.fullmatch(r"/i/nodes/[^/]+/?", parsed.path):
            return urlunsplit(("https", "alidocs.dingtalk.com", parsed.path, "", ""))
    return fallback


def _jsonml_text(raw):
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            raise ReadFailure("文档 JSONML 不是有效 JSON，未把原始结构当作正文") from None
    if not isinstance(raw, list) or not raw or not isinstance(raw[0], str):
        raise ReadFailure("文档 JSONML 结构无法识别")
    nontext = set()
    block_tags = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "table", "pre", "blockquote"}
    def walk(node, depth=0):
        if depth > 100:
            raise ReadFailure("文档嵌套层数超限，未读取完整正文")
        if isinstance(node, str):
            return node
        if not isinstance(node, list) or not node or not isinstance(node[0], str):
            return ""
        tag = node[0].lower()
        if tag in {"img", "image", "video", "audio", "drawing", "attachment", "embed", "iframe"}:
            nontext.add(tag)
        if tag == "br":
            return "\n"
        text = "".join(walk(child, depth + 1) for child in node[1:] if not isinstance(child, dict))
        return text + ("\t" if tag in {"td", "th"} else "\n" if tag in block_tags else "")
    content = walk(raw).strip()
    warnings = ["正文包含非文本内容（%s），未读取其内部内容" % "、".join(sorted(nontext))] if nontext else []
    return content, warnings


def _document(node, project, profile, config, cancelled):
    limits = config.get("limits", {})
    timeout = limits.get("timeout_seconds", 30)
    cap = limits.get("max_content_chars", 20000)
    max_bytes = config.get("local", {}).get("max_file_bytes", 3000000)
    item = {"id": stable_id("dingtalk", profile, node), "source": "dingtalk", "kind": "document",
            "project": safe_text(project), "title": "未读取标题", "locator": node, "event_time": None,
            "time_basis": "document_metadata_candidate", "attribution": "unknown", "content": "",
            "verification": "record_only", "warnings": [], "metadata": {"node_id": node}}
    if cancelled.is_set():
        item["warnings"].append("同一来源遇到认证或权限失败，未继续读取")
        item["metadata"].update(body_read=False, body_complete=False)
        return item
    try:
        inspect = _json_call(["drive", "+inspect", "--node", node], timeout, profile)
        item["warnings"].extend(_flags(inspect))
        body_complete = not item["warnings"]
        body_read = True
        file = next((layer["file"] for layer in _layers(inspect) if isinstance(layer.get("file"), dict)), None)
        if file is None or not isinstance(file.get("extension"), str):
            raise ReadFailure("节点元数据结构或文件类型无法识别")
        extension = file["extension"].lower().lstrip(".")
        item["title"] = safe_text(file.get("name") or "未命名文档")
        item["locator"] = _locator(file.get("docUrl"), node)
        modified = parse_time(file.get("modifyTime"))
        item["metadata"].update({"extension": extension, "modified_at": modified.isoformat() if modified else None,
                                  "size_bytes": file.get("fileSize"), "revision": None})
        if cancelled.is_set():
            raise ReadFailure("同一来源遇到认证或权限失败，未继续读取")
        if extension == "adoc":
            response = _json_call(["doc", "+fetch", "--node", node, "--scope", "full", "--detail", "full"], timeout, profile)
            item["warnings"].extend(_flags(response))
            body = next((layer["content"] for layer in _layers(response) if isinstance(layer.get("content"), dict)), None)
            if body is None or body.get("success") is False or "jsonml" not in body:
                raise ReadFailure("文档返回未包含可验证的 JSONML 正文")
            content, warnings = _jsonml_text(body["jsonml"])
            item["warnings"].extend(warnings)
            body_complete = body_complete and not item["warnings"]
            item["metadata"]["revision"] = body.get("revision")
            item["title"] = safe_text(body.get("title") or item["title"])
            item["locator"] = _locator(body.get("docUrl"), item["locator"])
        elif extension == "md":
            response = _json_call(["markdown", "fetch", "--node", node], timeout, profile)
            item["warnings"].extend(_flags(response))
            body_complete = body_complete and not item["warnings"]
            content = next((layer["content"] for layer in _layers(response) if isinstance(layer.get("content"), str)), None)
            if content is None:
                raise ReadFailure("Markdown 返回未包含纯文本正文")
        elif extension in {"txt", "csv", "json", "yaml", "yml", "html", "htm", "xml", "docx", "pdf"}:
            size = file.get("fileSize")
            if not isinstance(size, int) or isinstance(size, bool) or size <= 0 or size > max_bytes:
                raise ReadFailure("普通附件大小未知、为空或超限，未下载；需人工核查")
            from .local_source import extract_file
            with tempfile.TemporaryDirectory(prefix="work-summary-dws-") as directory:
                name = "document." + extension
                downloaded = _json_call(["drive", "+download", "--node", node, "--output", name], timeout, profile, directory)
                item["warnings"].extend(_flags(downloaded))
                body_complete = body_complete and not item["warnings"]
                reported = next((layer["sizeBytes"] for layer in _layers(downloaded) if "sizeBytes" in layer), None)
                path = Path(directory) / name
                if not isinstance(reported, int) or reported <= 0 or not path.is_file() or path.is_symlink() or not 0 < path.stat().st_size <= max_bytes:
                    raise ReadFailure("附件下载未通过大小或本地文件校验")
                if reported != path.stat().st_size:
                    raise ReadFailure("附件返回大小与实际文件不一致，未读取可能不完整的正文")
                extracted = extract_file(path, max_content_chars=cap, max_file_bytes=max_bytes, timeout=timeout)
                content = extracted.get("content", "")
                item["warnings"].extend(extracted.get("warnings", []))
                item["metadata"]["extraction"] = extracted.get("metadata", {}).get("extraction")
                item["metadata"]["sha256"] = extracted.get("metadata", {}).get("sha256")
                if extracted.get("metadata", {}).get("complete") is not True:
                    item["warnings"].append("附件正文未完整提取")
                    body_complete = False
                    body_read = bool(content)
        else:
            raise ReadFailure("暂不支持 %s 类型的正文；需对应产品 Skill 或人工补充，未将元数据当正文" % safe_text(extension or "未知"))
        if len(content) > cap:
            item["warnings"].append("正文超过字符上限，仅保留前 %d 字符" % cap)
            body_complete = False
        item["content"] = safe_text(content[:cap])
        item["metadata"]["body_read"] = body_read
        item["metadata"]["body_complete"] = body_complete
    except ReadFailure as exc:
        item["warnings"].append(str(exc))
        item["metadata"]["body_read"] = False
        item["metadata"]["body_complete"] = False
        if exc.fatal:
            cancelled.set()
    except (OSError, ValueError, TypeError) as exc:
        # 单篇文件异常不能使其他已经采集的证据丢失；不输出路径或原始异常。
        item["warnings"].append("文档解析或本地临时文件处理失败，需人工核查")
        item["metadata"]["body_read"] = False
        item["metadata"]["body_complete"] = False
    item["warnings"] = list(dict.fromkeys(safe_text(x) for x in item["warnings"]))
    return item


def collect(config, window):
    """返回已读证据和覆盖缺口；只在指定组织内检索，不登录、不写云端。"""
    result = {"source": "dingtalk", "status": "not_configured", "scope": [], "items": [], "gaps": []}
    settings = config.get("dingtalk", {})
    if not settings.get("enabled"):
        result["gaps"].append("钉钉采集未启用")
        return result
    queries = list(dict.fromkeys(str(q).strip() for q in settings.get("queries", []) if str(q).strip()))
    nodes = settings.get("nodes", [])
    if not queries and not nodes:
        result["gaps"].append("未配置钉钉检索词或明确节点，未进行无范围采集")
        return result
    timeout = config.get("limits", {}).get("timeout_seconds", 30)
    result["scope"] = ["公司：" + safe_text(config.get("company", {}).get("name", ""))]
    result["scope"] += ["检索词：" + safe_text(q) for q in queries]
    result["scope"].append("明确节点 %d 个；检索按修改时间筛选，正文时间与个人贡献需另行核对" % len(nodes))
    try:
        profile = _select_profile(config, timeout)
    except ReadFailure as exc:
        result.update(status="unavailable", gaps=[str(exc)])
        return result
    start, end = parse_time(window.get("start")), parse_time(window.get("end"))
    if not start or not end or start >= end:
        result.update(status="unavailable", gaps=["时间区间无效，必须提供带时区且递增的起止时间"])
        return result
    # DWS 上下界均为含；本工具统一使用 [start, end)，毫秒精度向内收敛。
    begin_ms, end_ms = math.ceil(start.timestamp() * 1000), math.ceil(end.timestamp() * 1000) - 1
    limit = max(1, min(int(settings.get("page_size", 20)), 30))
    max_pages = max(1, int(settings.get("max_pages", 10)))
    max_documents = max(1, int(settings.get("max_documents", 50)))
    candidates = {}
    company = config.get("company", {}).get("name", "本公司")
    for raw in nodes:
        try:
            candidates.setdefault(_node(raw), company)
        except ReadFailure as exc:
            result["gaps"].append(str(exc))
    if len(candidates) > max_documents:
        candidates = dict(list(candidates.items())[:max_documents])
        result["gaps"].append("明确节点数量超过 max_documents，部分节点未读取")
    searched = 0
    fatal = False
    for query in queries:
        cursor, seen = None, set()
        for page in range(max_pages):
            args = ["drive", "+search", "--query", query, "--modified-from", str(begin_ms),
                    "--modified-to", str(end_ms), "--limit", str(limit)]
            if cursor:
                args += ["--cursor", cursor]
            try:
                response = _json_call(args, timeout, profile)
                result["gaps"].extend(_flags(response, pagination=True))
                payload = next((layer for layer in _layers(response) if isinstance(layer.get("files"), list)), None)
                if payload is None:
                    raise ReadFailure("文件搜索返回结构无法识别，未将其当作零命中")
                searched += 1
                for entry in payload["files"]:
                    if not isinstance(entry, dict):
                        result["gaps"].append("搜索返回无法识别的文件条目")
                        continue
                    raw = entry.get("nodeId") or entry.get("dentryUuid")
                    try:
                        node = _node(raw)
                    except ReadFailure:
                        result["gaps"].append("搜索条目缺少可用稳定节点 ID")
                        continue
                    if node in candidates:
                        continue
                    if len(candidates) >= max_documents:
                        result["gaps"].append("命中文档数量超过 max_documents，部分正文未读取")
                        continue
                    candidates[node] = query
                has_more = payload.get("hasMore")
                next_cursor = payload.get("nextCursor")
                if has_more is False:
                    break
                if has_more is not True and not next_cursor:
                    if "hasMore" not in payload and "nextCursor" not in payload:
                        result["gaps"].append("搜索返回缺少分页终态，无法确认范围完整")
                    break
                if not isinstance(next_cursor, str) or not next_cursor:
                    result["gaps"].append("搜索仍有下一页但未返回可用游标")
                    break
                if next_cursor in seen:
                    result["gaps"].append("搜索分页游标重复，已停止，后续范围未覆盖")
                    break
                seen.add(next_cursor)
                cursor = next_cursor
                if page + 1 >= max_pages:
                    result["gaps"].append("搜索达到 max_pages，仍有后续页面未读取")
            except ReadFailure as exc:
                result["gaps"].append(str(exc))
                fatal = exc.fatal
                break
        if fatal:
            break
    if fatal:
        result["gaps"].append("认证或权限失败后已停止该来源，未继续读取其他文档")
    elif candidates:
        cancelled = threading.Event()
        with ThreadPoolExecutor(max_workers=3) as executor:
            result["items"] = list(executor.map(lambda pair: _document(pair[0], pair[1], profile, config, cancelled), candidates.items()))
        for item in result["items"]:
            if item["metadata"].get("body_complete") is not True:
                result["gaps"].extend("%s：%s" % (item["id"], warning) for warning in item["warnings"])
    result["gaps"] = list(dict.fromkeys(safe_text(gap) for gap in result["gaps"]))
    result["status"] = "partial" if result["gaps"] else "complete"
    if result["gaps"] and not result["items"] and not searched:
        result["status"] = "unavailable"
    return result
