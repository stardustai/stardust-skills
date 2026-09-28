"""时间、受限子进程、脱敏和私有输出基础能力。"""

import hashlib
import json
import os
import re
import selectors
import signal
import subprocess
import time
from dataclasses import dataclass
from datetime import date, datetime, time as daytime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str
    truncated: bool = False


def safe_text(value):
    """尽力屏蔽常见凭证；不是完整 DLP，也不据此允许公开报告。"""
    text = str(value)
    text = re.sub(r"-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?-----END [^-]*PRIVATE KEY-----", "[REDACTED PRIVATE KEY]", text)
    text = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1[REDACTED]", text)
    text = re.sub(r"\b(?:gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{16,}|sk-[A-Za-z0-9_-]{16,})\b", "[REDACTED]", text)
    text = re.sub(r"(?i)((?:api[_-]?key|access[_-]?token|refresh[_-]?token|app[_-]?secret|password|passwd|client[_-]?secret|authorization|cookie|token|secret)\s*[\"']?\s*[:=]\s*[\"']?)[^\s\"',;<>]+", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)(https?://)[^/\s:@]+:[^/\s@]+@", r"\1[REDACTED]@", text)
    text = re.sub(r"(?i)([?&](?:token|signature|sig|key|secret|x-amz-[^=&\s]+|x-oss-[^=&\s]+|access_token)=)[^&\s\"<>]+", r"\1[REDACTED]", text)
    return text


def sanitize(value):
    if isinstance(value, dict):
        sensitive = {"token", "accesstoken", "refreshtoken", "apikey", "appsecret", "clientsecret", "password", "passwd", "cookie", "authorization", "secret"}
        return {str(k): "[REDACTED]" if re.sub(r"[_-]", "", str(k)).lower() in sensitive else sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    return safe_text(value) if isinstance(value, str) else value


def stable_id(prefix, *values):
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, default=str)
    return prefix + "-" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def parse_time(value):
    try:
        if isinstance(value, datetime):
            return value if value.tzinfo else None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return datetime.fromtimestamp(value / 1000 if abs(value) > 100000000000 else value, timezone.utc)
        if not value:
            return None
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return result if result.tzinfo else None
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def in_window(value, window):
    instant = parse_time(value)
    start, end = parse_time(window["start"]), parse_time(window["end"])
    return bool(instant and start and end and start <= instant < end)


def make_window(start=None, end=None, timezone_name="Asia/Shanghai", now=None):
    tz = ZoneInfo(timezone_name)
    now = (now or datetime.now(timezone.utc)).astimezone(tz)
    def boundary(value, upper=False):
        if value is None:
            return None
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            day = date.fromisoformat(value) + timedelta(days=int(upper))
            return datetime.combine(day, daytime.min, tzinfo=tz)
        parsed = parse_time(value)
        if parsed is None:
            raise ValueError("时间须为 YYYY-MM-DD 或带时区的 ISO 时间")
        return parsed.astimezone(tz)
    begin = boundary(start) or datetime.combine(now.date(), daytime.min, tzinfo=tz)
    requested_end = boundary(end, True)
    if requested_end is None:
        requested_end = datetime.combine(begin.date() + timedelta(days=1), daytime.min, tzinfo=tz)
    finish = min((requested_end, now), key=lambda value: value.timestamp())
    if begin.timestamp() >= finish.timestamp():
        raise ValueError("时间范围为空、倒置或全部位于未来")
    return {"start": begin.isoformat(), "end": finish.isoformat(), "timezone": timezone_name,
            "observed_at": now.isoformat(), "end_exclusive": True,
            "requested_end": requested_end.isoformat(), "capped_at_now": requested_end.timestamp() > now.timestamp()}


def run(args, cwd=None, timeout=30, max_output_bytes=2000000):
    """无 shell，环境白名单，双流限量；超时终止本次子进程组。"""
    if not isinstance(args, (list, tuple)) or not args or not all(isinstance(a, str) for a in args):
        raise ValueError("子进程参数必须是非空字符串数组")
    if timeout <= 0 or max_output_bytes < 1:
        raise ValueError("子进程超时和输出上限必须为正数")
    allowed = {"PATH", "HOME", "USER", "LOGNAME", "TMPDIR", "TEMP", "TMP", "LANG", "LC_ALL",
               "LC_CTYPE", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "SSL_CERT_FILE", "SSL_CERT_DIR"}
    env = {k: v for k, v in os.environ.items() if k in allowed}
    env.update({"GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0", "GIT_PAGER": "cat", "PAGER": "cat"})
    try:
        process = subprocess.Popen(args, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    except OSError as exc:
        raise RuntimeError("无法启动工具：" + Path(args[0]).name) from None
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    deadline, total, truncated = time.monotonic() + timeout, 0, False
    def stop():
        # 主进程退出后，子进程仍可能持有输出管道；终止我们创建的整个会话组。
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ, "stdout")
            selector.register(process.stderr, selectors.EVENT_READ, "stderr")
            while selector.get_map():
                if time.monotonic() >= deadline:
                    raise RuntimeError("工具执行超时：" + Path(args[0]).name)
                for key, _ in selector.select(min(0.1, max(0, deadline - time.monotonic()))):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    available = max_output_bytes - total
                    buffers[key.data].extend(chunk[:max(0, available)])
                    total += min(len(chunk), max(0, available))
                    if len(chunk) > available:
                        truncated = True
                        stop()
                        break
                if truncated:
                    break
        remaining = max(0.01, deadline - time.monotonic())
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            raise RuntimeError("工具执行超时：" + Path(args[0]).name) from None
    finally:
        stop()
        process.stdout.close()
        process.stderr.close()
    return CommandResult(process.returncode, buffers["stdout"].decode("utf-8", "replace"),
                         buffers["stderr"].decode("utf-8", "replace"), truncated)


def private_write(path, text):
    """独占创建，禁止静默覆盖或沿符号链接写入。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(str(path), flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)


def json_text(value):
    return json.dumps(sanitize(value), ensure_ascii=False, indent=2) + "\n"
