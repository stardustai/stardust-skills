"""只读采集授权目录中的候选材料；文件时间不构成工作日期或作者证明。"""

import fnmatch
import hashlib
import io
import json
import os
import re
import shutil
import stat
import tempfile
import time
import zipfile
import zlib
from contextlib import contextmanager
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

from .common import in_window, parse_time, run, safe_text, stable_id


MAX_DEPTH = 32
MAX_DOCX_UNCOMPRESSED_BYTES = 16 * 1024 * 1024
MAX_ZIP_ENTRIES = 2048
TEXT_FORMATS = {"txt", "md", "markdown", "csv", "json", "html", "htm", "xml"}
IMAGE_FORMATS = {"png", "jpg", "jpeg", "gif", "webp", "bmp", "tif", "tiff", "heic", "svg"}
PRIVATE_DIRS = {
    ".git", ".hg", ".svn", "node_modules", ".ssh", ".gnupg", ".aws", ".azure",
    ".kube", ".docker", ".config", ".local", ".cache", ".npm", ".venv", "venv",
    "__pycache__", ".trash", ".codex", ".claude", "library", "appdata",
}
PRIVATE_NAME = re.compile(
    r"(?:^|[.\s_-])(?:keys?|tokens?|credentials?|secrets?|passwords?|passwd|"
    r"apikey|api[_-]key|access[_-]token|refresh[_-]token|private[_-]key|"
    r"id_rsa|id_dsa|id_ecdsa|id_ed25519|keychain)(?:$|[.\s_-])", re.I
)
PRIVATE_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".kdbx", ".keychain", ".keychain-db"}
TIME_WARNING = "文件系统时间仅用于候选筛选，不能证明作者、实际工作日期或本人当日产出。"
WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _positive(value, default):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0 else default


def _iso(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def _sensitive(name):
    lowered = name.casefold()
    return (lowered in PRIVATE_DIRS or lowered == ".env" or lowered.startswith(".env.")
            or lowered in {".netrc", ".npmrc", ".pypirc", ".ds_store"}
            or Path(lowered).suffix in PRIVATE_SUFFIXES or bool(PRIVATE_NAME.search(lowered)))


def _matches(relative, patterns):
    """让 **/*.md 同时匹配根目录文件，目录排除可使用 folder/**。"""
    for pattern in patterns:
        if not isinstance(pattern, str):
            continue
        while True:
            if fnmatch.fnmatchcase(relative, pattern) or fnmatch.fnmatchcase(relative + "/", pattern):
                return True
            if pattern.endswith("/**") and relative == pattern[:-3]:
                return True
            if not pattern.startswith("**/"):
                break
            pattern = pattern[3:]
    return False


class _HtmlText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        elif tag in {"p", "div", "br", "li", "tr", "h1", "h2", "h3"} and not self.hidden:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.hidden:
            self.hidden -= 1
        elif tag in {"p", "div", "li", "tr"} and not self.hidden:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


class _ExtractionError(Exception):
    pass


def _xml(raw):
    # ElementTree 无需外部实体；主动拒绝 DTD，防止内部实体膨胀。
    declarations = raw.replace(b"\x00", b"").lower()
    if b"<!doctype" in declarations or b"<!entity" in declarations:
        raise _ExtractionError("XML 含 DTD 或实体声明，未解析。")
    return ElementTree.fromstring(raw)


def _word_paragraph(node):
    parts = []
    for child in node.iter():
        if child.tag == WORD_NS + "t":
            parts.append(child.text or "")
        elif child.tag == WORD_NS + "tab":
            parts.append("\t")
        elif child.tag in {WORD_NS + "br", WORD_NS + "cr"}:
            parts.append("\n")
    return "".join(parts)


def _word_blocks(node):
    blocks = []
    for child in node:
        if child.tag == WORD_NS + "p":
            blocks.append(_word_paragraph(child))
        elif child.tag == WORD_NS + "tbl":
            for row in child.findall(WORD_NS + "tr"):
                blocks.append("\t".join(_word_blocks(cell) for cell in row.findall(WORD_NS + "tc")))
        elif child.tag == WORD_NS + "sdt":
            content = child.find(WORD_NS + "sdtContent")
            if content is not None:
                blocks.append(_word_blocks(content))
    return "\n".join(blocks)


def _docx(raw, uncompressed_limit):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        if len(entries) > MAX_ZIP_ENTRIES:
            raise _ExtractionError("DOCX 压缩包条目数超过安全上限。")
        if sum(entry.file_size for entry in entries) > uncompressed_limit:
            raise _ExtractionError("DOCX 声明解压大小超过安全上限。")
        if any(entry.file_size > 1024 * 1024 and entry.file_size > max(1, entry.compress_size) * 200 for entry in entries):
            raise _ExtractionError("DOCX 压缩比超过安全上限。")
        names = [entry.filename for entry in entries]
        if len(names) != len(set(names)):
            raise _ExtractionError("DOCX 含重复压缩包条目，未解析。")

        def xml_member(name):
            with archive.open(name) as handle:
                data = handle.read(uncompressed_limit + 1)
            if len(data) > uncompressed_limit:
                raise _ExtractionError("DOCX 实际解压大小超过安全上限。")
            return _xml(data)

        document = xml_member("word/document.xml")
        body = document.find(WORD_NS + "body")
        if body is None:
            raise _ExtractionError("DOCX 未找到 Word 正文。")
        properties = {}
        if "docProps/core.xml" in names:
            for child in xml_member("docProps/core.xml"):
                key = child.tag.rsplit("}", 1)[-1]
                if key in {"creator", "lastModifiedBy", "created", "modified", "title", "subject", "revision"}:
                    properties[key] = safe_text(child.text or "")
        return _word_blocks(body), properties


@contextmanager
def _directory_handle(path):
    """在支持 openat 的系统逐段拒绝链接，扫描和读取不受父目录链接替换影响。"""
    supported = (os.open in os.supports_dir_fd and os.scandir in os.supports_fd
                 and hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY"))
    if not supported:
        yield None
        return
    absolute = Path(os.path.abspath(path))
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open(absolute.anchor, flags)
    try:
        for part in absolute.parts[1:]:
            following = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = following
        yield descriptor
    finally:
        os.close(descriptor)


def _read_file(path, max_file_bytes):
    """最终路径不跟链接，打开后再次核对类型/身份，避免普通文件被替换。"""
    with _directory_handle(path.parent) as parent_descriptor:
        before = path.lstat() if parent_descriptor is None else os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode):
            raise _ExtractionError("路径不是普通文件，未读取。")
        if before.st_size > max_file_bytes:
            return None, before
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        descriptor = (os.open(str(path), flags) if parent_descriptor is None
                      else os.open(path.name, flags, dir_fd=parent_descriptor))
        with os.fdopen(descriptor, "rb") as handle:
            opened = os.fstat(handle.fileno())
            if (not stat.S_ISREG(opened.st_mode)
                    or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)):
                raise _ExtractionError("文件在读取前发生替换，未读取。")
            raw = handle.read(max_file_bytes + 1)
            after = os.fstat(handle.fileno())
    if len(raw) > max_file_bytes:
        return None, after
    if (after.st_size, after.st_mtime_ns, after.st_ctime_ns) != (opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns):
        raise _ExtractionError("文件在读取期间发生变化，本次内容未采用。")
    return raw, after


def _extract_file(path, max_content_chars, max_file_bytes, timeout, docx_limit):
    path = Path(path)
    file_format = path.suffix.lower().lstrip(".") or "unknown"
    metadata = {"format": file_format, "sha256": None, "extraction": "read_error", "complete": False}
    warnings = []
    content = ""
    try:
        raw, file_stat = _read_file(path, max_file_bytes)
        metadata.update(mtime=_iso(file_stat.st_mtime), ctime=_iso(file_stat.st_ctime), size_bytes=file_stat.st_size)
        if raw is None:
            metadata["extraction"] = "size_limit"
            warnings.append("文件超过读取大小上限，仅保留文件元数据。")
        else:
            metadata["sha256"] = hashlib.sha256(raw).hexdigest()
            if file_format in TEXT_FORMATS:
                content = raw.decode("utf-8-sig")
                if "\x00" in content:
                    raise _ExtractionError("文本含 NUL 字节，可能为二进制或非 UTF-8 内容，未解析。")
                if file_format == "json":
                    json.loads(content)
                elif file_format == "xml":
                    _xml(raw)
                elif file_format in {"html", "htm"}:
                    parser = _HtmlText()
                    parser.feed(content)
                    parser.close()
                    content = "".join(parser.parts).strip()
                metadata.update(extraction="text", complete=True)
            elif file_format == "docx":
                content, properties = _docx(raw, docx_limit)
                metadata.update(extraction="docx", complete=True, document_properties=properties)
                warnings.append("文档内作者和日期属于文件自报元数据，未核验本人身份或实际工作时间。")
            elif file_format == "pdf":
                executable = shutil.which("pdftotext")
                if executable:
                    # 工具读取已检查的私有临时副本，避免再次沿源路径读取，也不改写源文件。
                    with tempfile.TemporaryDirectory(prefix="work-summary-pdf-") as temporary:
                        source = Path(temporary) / "input.pdf"
                        source.write_bytes(raw)
                        result = run([executable, "-enc", "UTF-8", "-nopgbrk", str(source), "-"],
                                     timeout=timeout, max_output_bytes=max(4096, max_content_chars * 4))
                    if result.returncode and not result.truncated:
                        raise _ExtractionError("PDF 文本提取失败，可能需要解密、OCR 或 PDF Skill。")
                    content = result.stdout
                    metadata.update(extraction="pdftotext", complete=not result.truncated)
                    if result.truncated:
                        warnings.append("PDF 提取输出超过上限，内容已截断。")
                    if not content.strip():
                        metadata.update(extraction="requires_skill", complete=False, required_reader="PDF Skill 或 OCR")
                        warnings.append("PDF 未提取到文本，需 Agent 配合 PDF Skill 或 OCR 读取。")
                else:
                    metadata.update(extraction="unsupported", required_reader="PDF Skill")
                    warnings.append("未发现 pdftotext；PDF 正文尚未读取，需 Agent 配合 PDF Skill 读取。")
            else:
                readers = {"pptx": "Presentations Skill", "ppt": "Presentations Skill",
                           "xlsx": "Spreadsheets Skill", "xls": "Spreadsheets Skill"}
                reader = "Agent 图像读取或 OCR" if file_format in IMAGE_FORMATS else readers.get(file_format)
                metadata["extraction"] = "requires_skill" if reader else "unsupported"
                if reader:
                    metadata["required_reader"] = reader
                warnings.append("附件正文尚未读取，需 " + (reader or "支持此格式的 Agent/Skill") + " 读取。")
    except UnicodeDecodeError:
        metadata["extraction"] = "parse_error"
        warnings.append("文件不是有效 UTF-8 文本，未解析。")
        content = ""
    except (ElementTree.ParseError, json.JSONDecodeError, zipfile.BadZipFile, zlib.error,
            KeyError, EOFError, NotImplementedError, RecursionError):
        metadata["extraction"] = "parse_error"
        warnings.append("文件结构无法解析，仅保留可取得的元数据。")
        content = ""
    except _ExtractionError as exc:
        metadata["extraction"] = "parse_error"
        warnings.append(str(exc))
        content = ""
    except RuntimeError:
        metadata["extraction"] = "extraction_error"
        warnings.append("提取工具不可用、超时或文件不支持提取，仅保留可取得的元数据。")
        content = ""
    except OSError:
        metadata["extraction"] = "read_error"
        warnings.append("文件不可访问或读取失败，仅保留可取得的元数据。")
        content = ""
    content = safe_text(content)
    if len(content) > max_content_chars:
        content = content[:max_content_chars]
        metadata.update(complete=False, content_truncated=True)
        warnings.append("正文超过字符上限，内容已截断。")
    return {"content": content, "warnings": warnings, "metadata": metadata}


def extract_file(path, max_content_chars=20000, max_file_bytes=3000000, timeout=30):
    """提取已获授权的单个文件；不检查日期，供普通附件采集复用。"""
    path = Path(path)
    # 调用方明确授权的单个文件允许系统临时目录别名，例如 macOS 的 /var。
    # 最终文件本身仍不得为符号链接；collect 直接使用已核验的目录内路径。
    try:
        path = path.parent.resolve(strict=True) / path.name
    except (OSError, RuntimeError):
        pass
    return _extract_file(path, int(_positive(max_content_chars, 20000)),
                         int(_positive(max_file_bytes, 3000000)), _positive(timeout, 30),
                         MAX_DOCX_UNCOMPRESSED_BYTES)


def _walk_files(root, max_depth, deadline, exclusions, gaps):
    pending = [(root, 0)]
    while pending:
        directory, depth = pending.pop()
        if time.monotonic() >= deadline:
            gaps.append("本地扫描达到时间上限，尚有目录或文件未扫描。")
            return
        try:
            if directory.is_symlink() or directory.resolve() != directory:
                gaps.append("扫描期间目录路径发生变化，已跳过该目录。")
                continue
            with _directory_handle(directory) as descriptor, os.scandir(directory if descriptor is None else descriptor) as entries:
                for entry in entries:
                    if time.monotonic() >= deadline:
                        gaps.append("本地扫描达到时间上限，尚有目录或文件未扫描。")
                        return
                    if entry.is_symlink() or _sensitive(entry.name):
                        continue
                    path = directory / entry.name
                    relative = path.relative_to(root).as_posix()
                    if _matches(relative, exclusions):
                        continue
                    try:
                        file_stat = entry.stat(follow_symlinks=False)
                        if stat.S_ISDIR(file_stat.st_mode):
                            if depth >= max_depth:
                                gaps.append("目录达到递归深度上限：" + safe_text(str(path)))
                            else:
                                pending.append((path, depth + 1))
                        elif stat.S_ISREG(file_stat.st_mode):
                            yield path, relative, file_stat
                    except OSError:
                        gaps.append("无法读取文件或目录元数据：" + safe_text(str(path)))
        except OSError:
            gaps.append("目录不可访问，未完成扫描：" + safe_text(str(directory)))


def collect(config, window):
    result = {"source": "local", "status": "not_configured", "scope": [], "items": [], "gaps": []}
    local = config.get("local") or {}
    roots = local.get("roots") or []
    if not roots:
        return result
    gaps, items = result["gaps"], result["items"]
    start, end = parse_time(window.get("start")), parse_time(window.get("end"))
    if not start or not end or start >= end:
        result.update(status="unavailable", gaps=["本地采集的时间窗口无效。"])
        return result
    limits = config.get("limits") or {}
    timeout = _positive(limits.get("timeout_seconds"), 30)
    deadline = time.monotonic() + timeout
    max_files = int(_positive(local.get("max_files"), 500))
    max_bytes = int(_positive(local.get("max_file_bytes"), 3000000))
    max_chars = int(_positive(limits.get("max_content_chars"), 20000))
    max_depth = min(MAX_DEPTH, int(_positive(local.get("max_depth"), MAX_DEPTH)))
    docx_limit = min(MAX_DOCX_UNCOMPRESSED_BYTES,
                     int(_positive(local.get("max_docx_uncompressed_bytes"), MAX_DOCX_UNCOMPRESSED_BYTES)))
    inclusions = local.get("include_globs", ["**/*"])
    exclusions = local.get("exclude_globs", [])
    accepted, count, by_path, by_hash = 0, 0, {}, {}
    capped = False
    home = Path.home().resolve()
    for setting in roots:
        if not isinstance(setting, dict) or not isinstance(setting.get("path"), str):
            gaps.append("本地目录配置无效，需要明确的绝对路径。")
            continue
        path = Path(setting["path"]).expanduser()
        mode = setting.get("mode", "mixed")
        keywords = [word.strip().casefold() for word in setting.get("keywords", []) if isinstance(word, str) and word.strip()]
        if mode not in {"workspace", "mixed"} or (mode == "mixed" and not keywords):
            gaps.append("混合目录须提供公司或项目关键词，且 mode 须为 workspace 或 mixed。")
            continue
        try:
            if not path.is_absolute() or path.is_symlink():
                gaps.append("本地根目录必须为非符号链接的绝对路径。")
                continue
            root = path.resolve(strict=True)
            if root == Path(root.anchor) or (mode == "workspace" and (root == home or root in home.parents)):
                gaps.append("拒绝将文件系统根目录、整个家目录或其父目录作为工作区扫描。")
                continue
            if any(_sensitive(part) for part in root.parts[1:]):
                gaps.append("本地根目录处于默认隐私排除范围，未扫描。")
                continue
            with os.scandir(root):
                pass
        except (OSError, RuntimeError):
            gaps.append("本地根目录不可访问：" + safe_text(str(path)))
            continue
        accepted += 1
        if str(root) not in result["scope"]:
            result["scope"].append(str(root))
        project = safe_text(setting.get("project") or root.name)
        for candidate, relative, file_stat in _walk_files(root, max_depth, deadline, exclusions, gaps):
            if not _matches(relative, inclusions) or (mode == "mixed" and not any(word in relative.casefold() for word in keywords)):
                continue
            time_fields = [name for name, value in (("mtime", file_stat.st_mtime), ("ctime", file_stat.st_ctime)) if in_window(value, window)]
            if not time_fields:
                continue
            if str(candidate) in by_path:
                projects = by_path[str(candidate)]["metadata"]["projects"]
                if project not in projects:
                    projects.append(project)
                continue
            if count >= max_files:
                gaps.append("本地候选文件数量超过上限，尚有匹配文件未读取。")
                capped = True
                break
            count += 1
            try:
                if candidate.is_symlink() or candidate.resolve() != candidate:
                    gaps.append("候选文件路径发生变化，已跳过。")
                    continue
            except OSError:
                gaps.append("候选文件路径无法核验，已跳过。")
                continue
            extracted = _extract_file(candidate, max_chars, max_bytes,
                                      max(0.01, deadline - time.monotonic()), docx_limit)
            metadata = extracted["metadata"]
            metadata.setdefault("mtime", _iso(file_stat.st_mtime))
            metadata.setdefault("ctime", _iso(file_stat.st_ctime))
            metadata.setdefault("size_bytes", file_stat.st_size)
            metadata.update(candidate_time_fields=time_fields, paths=[str(candidate)], projects=[project])
            if not metadata["complete"]:
                gaps.append("正文未完整读取：" + safe_text(str(candidate)) + "（" + metadata["extraction"] + "）")
            digest = metadata.get("sha256")
            if digest and digest in by_hash:
                previous = by_hash[digest]
                previous["metadata"]["paths"].append(str(candidate))
                if project not in previous["metadata"]["projects"]:
                    previous["metadata"]["projects"].append(project)
                previous["warnings"] = list(dict.fromkeys(previous["warnings"] + extracted["warnings"]))
                # 相同字节可能以不同扩展名出现；保留能读出的正文与全部原始路径。
                if not previous["content"] and extracted["content"]:
                    paths, projects = previous["metadata"]["paths"], previous["metadata"]["projects"]
                    previous.update(content=extracted["content"], title=safe_text(candidate.name), locator=str(candidate),
                                    kind="document" if metadata["format"] in TEXT_FORMATS | {"docx", "pdf"} else "attachment")
                    previous["metadata"] = metadata
                    previous["metadata"].update(paths=paths, projects=projects)
                by_path[str(candidate)] = previous
                continue
            item = {
                "id": stable_id("local", digest or str(candidate)), "source": "local",
                "kind": "document" if metadata["format"] in TEXT_FORMATS | {"docx", "pdf"} else "attachment",
                "project": project, "title": safe_text(candidate.name), "locator": str(candidate),
                "event_time": None, "time_basis": "filesystem_mtime_candidate", "attribution": "unknown",
                "content": extracted["content"], "verification": "record_only",
                "warnings": [TIME_WARNING] + extracted["warnings"], "metadata": metadata,
            }
            items.append(item)
            by_path[str(candidate)] = item
            if digest:
                by_hash[digest] = item
        if capped or time.monotonic() >= deadline:
            if time.monotonic() >= deadline:
                gaps.append("本地采集达到时间上限，未保证全部范围完成。")
            break
    result["gaps"] = list(dict.fromkeys(gaps))
    result["items"] = sorted(items, key=lambda item: item["locator"])
    result["status"] = "unavailable" if not accepted else ("partial" if result["gaps"] else "complete")
    return result
