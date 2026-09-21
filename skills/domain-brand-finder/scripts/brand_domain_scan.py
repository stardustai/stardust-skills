#!/usr/bin/env python3
"""Check candidate domains against public RDAP registries.

The 10-column CSV is retained for existing workflows. Per-domain evidence is
written separately as JSONL; a registry no-record response is only a lead for
registrar verification, never a statement that the name is purchasable.
"""

from __future__ import annotations

import argparse
import csv
import email.utils
import json
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

import requests


USER_AGENT = "domain-brand-finder/2.0 (public RDAP lookup)"
IANA_RDAP_BOOTSTRAP_URL = "https://data.iana.org/rdap/dns.json"
DEFAULT_TLDS = ["ai", "com", "io", "dev", "chat", "tech"]
DEFAULT_CONTROLS = {
    "ai": "google.ai",
    "com": "example.com",
    "io": "google.io",
    "dev": "google.dev",
    "chat": "discord.chat",
    "tech": "google.tech",
}
DEFAULT_CACHE_JSONL = str(Path.home() / ".cache" / "domain-brand-finder" / "registry-cache.jsonl")
DEFAULT_HISTORY_CSV = str(
    Path.home()
    / "Documents"
    / "memory"
    / "product"
    / "domain name"
    / "results"
    / "master_domain_name_records.csv"
)
OUTPUT_FIELDS = [
    "域名",
    "类型",
    "思路",
    "词根",
    "含义",
    "分数",
    "是否available",
    "检查时间",
    "备注",
    "查询来源",
]
REGISTRY_STATUSES = {
    "REGISTERED",
    "NO_REGISTRY_RECORD",
    "UNKNOWN",
    "UNSUPPORTED",
}
_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_thread_state = threading.local()


@dataclass
class Candidate:
    candidate: str
    theme: str
    brand_score_10: str
    what_works: str
    concern: str
    root_a: str
    root_b: str
    seed_meaning: str
    generation_priority: str = ""

    @property
    def stem(self) -> str:
        return normalize_candidate(self.candidate)


@dataclass
class DomainEvidence:
    domain: str
    registry_status: str
    http_status: Optional[int]
    source: str
    endpoint: str
    checked_at: str
    error: str = ""
    control_domain: str = ""
    control_status: str = "UNKNOWN"
    raw_response: str = ""
    retry_after: str = ""
    cache_hit: bool = False


def normalize_key(value: str) -> str:
    """Legacy helper retained for import compatibility; scanner input does not use it."""
    return re.sub(r"[^a-z0-9]+", "", (value or "").strip().lower())


def normalize_candidate(value: str) -> str:
    candidate = (value or "").strip().lower()
    if not candidate or len(candidate) > 63 or not _LABEL_RE.fullmatch(candidate):
        raise ValueError(f"Invalid candidate label {value!r}; use one DNS label only.")
    return candidate


def normalize_tlds(tlds: Iterable[str]) -> List[str]:
    normalized: List[str] = []
    seen = set()
    for raw_tld in tlds:
        tld = (raw_tld or "").strip().lower()
        if tld.startswith("."):
            tld = tld[1:]
        if not tld:
            continue
        labels = tld.split(".")
        if any(not _LABEL_RE.fullmatch(label) for label in labels):
            raise ValueError(f"Invalid TLD suffix {raw_tld!r}.")
        if tld not in seen:
            normalized.append(tld)
            seen.add(tld)
    if not normalized:
        raise ValueError("At least one TLD is required.")
    return normalized


def require_supported_tlds(tlds: Iterable[str]) -> List[str]:
    """Compatibility wrapper; registry support is determined by IANA routing."""
    try:
        return normalize_tlds(tlds)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


def current_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Input candidate CSV path.")
    parser.add_argument("--output-all", required=True, help="Path for the full working CSV.")
    parser.add_argument("--output-shortlist", required=True, help="Path for the shortlist CSV.")
    parser.add_argument(
        "--output-evidence",
        help="Per-domain evidence JSONL path. Defaults to OUTPUT_ALL.evidence.jsonl.",
    )
    parser.add_argument("--cache-jsonl", default=DEFAULT_CACHE_JSONL, help="Full-domain evidence cache.")
    parser.add_argument("--cache-ttl-hours", type=float, default=24, help="Successful evidence TTL. Default: 24 hours.")
    parser.add_argument(
        "--controls-json",
        help="JSON object mapping TLD suffixes to known registered control domains.",
    )
    parser.add_argument(
        "--tlds",
        default=",".join(DEFAULT_TLDS),
        help="Comma-separated TLD priority list. Default: ai,com,io,dev,chat,tech",
    )
    parser.add_argument("--shortlist-limit", type=int, default=100, help="Maximum shortlist rows.")
    parser.add_argument("--timeout", type=float, default=4.0, help="Per-request timeout in seconds.")
    parser.add_argument("--workers", type=int, default=3, help="Concurrent lookup workers (capped at 3).")
    parser.add_argument("--retries", type=int, default=2, help="Retries for rate limits, server errors, and timeouts.")
    parser.add_argument(
        "--history-csv",
        default=DEFAULT_HISTORY_CSV,
        help="Deprecated legacy yes/no CSV; read only for interface compatibility and never used as evidence.",
    )
    parser.add_argument(
        "--ignore-history",
        action="store_true",
        help="Ignore legacy history and force fresh checks instead of using the JSONL cache.",
    )
    return parser.parse_args()


def load_candidates(path: Path) -> List[Candidate]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "candidate" not in reader.fieldnames:
            raise SystemExit("Input CSV must contain a `candidate` column.")

        candidates: List[Candidate] = []
        seen = set()
        for row_number, row in enumerate(reader, start=2):
            raw_name = (row.get("candidate") or "").strip()
            if not raw_name:
                continue
            try:
                normalized = normalize_candidate(raw_name)
            except ValueError as exc:
                raise SystemExit(f"Input CSV row {row_number}: {exc}") from exc
            if normalized in seen:
                continue
            seen.add(normalized)
            candidates.append(
                Candidate(
                    candidate=normalized,
                    theme=(row.get("theme") or "").strip(),
                    brand_score_10=(row.get("brand_score_10") or "").strip(),
                    what_works=(row.get("what_works") or "").strip(),
                    concern=(row.get("concern") or "").strip(),
                    root_a=(row.get("root_a") or "").strip(),
                    root_b=(row.get("root_b") or "").strip(),
                    seed_meaning=(row.get("seed_meaning") or "").strip(),
                    generation_priority=(row.get("generation_priority") or "").strip(),
                )
            )
        return candidates


def _retry_delay(response: Optional[requests.Response], attempt: int) -> Optional[float]:
    delay = min(2**attempt, 5)
    retry_after = response.headers.get("Retry-After") if response is not None else None
    if retry_after:
        try:
            delay = float(retry_after)
            if delay > 60:
                return None
        except ValueError:
            try:
                retry_at = email.utils.parsedate_to_datetime(retry_after)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                delay = max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
                if delay > 60:
                    return None
            except (TypeError, ValueError, OverflowError):
                pass
    return min(max(delay, 0.0), 60.0)


def _get_with_retries(
    session: requests.Session,
    url: str,
    timeout: float,
    retries: int,
) -> requests.Response:
    max_retries = min(max(int(retries), 0), 5)
    for attempt in range(max_retries + 1):
        try:
            response = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
        except requests.RequestException:
            if attempt >= max_retries:
                raise
            time.sleep(_retry_delay(None, attempt))
            continue
        if response.status_code == 429 or 500 <= response.status_code <= 599:
            if attempt >= max_retries:
                return response
            delay = _retry_delay(response, attempt)
            if delay is None:
                return response
            time.sleep(delay)
            continue
        return response
    raise RuntimeError("unreachable retry state")


def build_bootstrap_index(
    session: requests.Session,
    timeout: float,
    retries: int = 2,
) -> Dict[str, str]:
    """Build the IANA TLD-to-RDAP map; preserved for registry_audit.py callers."""
    response = _get_with_retries(session, IANA_RDAP_BOOTSTRAP_URL, timeout, retries)
    response.raise_for_status()
    data = response.json()
    index: Dict[str, str] = {}
    for tlds, urls in data.get("services", []):
        valid_urls = [url for url in urls if isinstance(url, str) and url.startswith(("https://", "http://"))]
        if not valid_urls:
            continue
        base = valid_urls[0]
        for tld in tlds:
            index[str(tld).lower()] = base
    return index


def rdap_url(domain: str, bootstrap_base: str) -> str:
    return f"{bootstrap_base.rstrip('/')}/domain/{domain.lower()}"


def check_via_rdap(
    session: requests.Session,
    domain: str,
    bootstrap_base: str,
    timeout: float,
    retries: int = 2,
) -> Tuple[Optional[int], str]:
    url = rdap_url(domain, bootstrap_base)
    try:
        response = _get_with_retries(session, url, timeout, retries)
        return response.status_code, url
    except requests.RequestException:
        return None, url


def _query_io_whois(
    domain: str, timeout: float, retries: int = 2
) -> Tuple[Optional[int], str, str, str]:
    source = "whois://whois.nic.io"
    attempts = min(max(int(retries), 0), 5) + 1
    for attempt in range(attempts):
        try:
            result = subprocess.run(
                ["whois", "-h", "whois.nic.io", domain],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            if attempt + 1 < attempts:
                time.sleep(_retry_delay(None, attempt))
                continue
            return None, source, "", "timeout"
        except (subprocess.SubprocessError, OSError):
            return None, source, "", "whois_network_error"
        body = (result.stdout or "") + (result.stderr or "")
        code, error = _parse_io_whois_body(domain, body)
        return code, source, body, error
    return None, source, "", "whois_query_error"


def check_via_io_whois(domain: str, timeout: float, retries: int = 2) -> Tuple[Optional[int], str]:
    """Compatibility tuple wrapper for the official .io WHOIS route."""
    code, source, _body, _error = _query_io_whois(domain, timeout, retries)
    return code, source


def check_domain(
    session: requests.Session,
    bootstrap_index: Dict[str, str],
    stem: str,
    tld: str,
    timeout: float,
    retries: int = 2,
) -> Tuple[Optional[int], str]:
    """Compatibility transport check returning (HTTP-like code, source URL).

    Callers that interpret a 404 as no registry record must first verify a
    positive registered control for the same TLD. The main scanner does this.
    """
    suffix = normalize_tlds([tld])[0]
    domain = f"{normalize_candidate(stem)}.{suffix}"
    registry_tld = suffix.rsplit(".", 1)[-1]
    bootstrap_base = bootstrap_index.get(registry_tld)
    if bootstrap_base:
        return check_via_rdap(session, domain, bootstrap_base, timeout, retries)
    if registry_tld == "io":
        return check_via_io_whois(domain, timeout, retries)
    return None, "bootstrap://unavailable"


def _valid_domain_payload(payload: object, domain: str) -> bool:
    if not isinstance(payload, dict):
        return False
    if str(payload.get("objectClassName", "")).lower() != "domain":
        return False
    returned_domain = payload.get("ldhName")
    return bool(returned_domain) and str(returned_domain).rstrip(".").lower() == domain.lower()


def _valid_domain_object(response: requests.Response, domain: str) -> bool:
    try:
        payload = response.json()
    except (ValueError, requests.RequestException):
        return False
    return _valid_domain_payload(payload, domain)


def _response_body(response: requests.Response) -> str:
    body = getattr(response, "text", None)
    if isinstance(body, str) and body:
        return body
    try:
        return json.dumps(response.json(), ensure_ascii=False, separators=(",", ":"))
    except (ValueError, requests.RequestException):
        return ""


def probe_domain(
    session: requests.Session,
    domain: str,
    bootstrap_base: str,
    timeout: float,
    control_registered: bool,
    retries: int = 2,
) -> DomainEvidence:
    url = rdap_url(domain, bootstrap_base)
    try:
        response = _get_with_retries(session, url, timeout, retries)
    except requests.Timeout:
        return DomainEvidence(domain, "UNKNOWN", None, "rdap", url, current_timestamp(), "timeout")
    except requests.RequestException as exc:
        return DomainEvidence(domain, "UNKNOWN", None, "rdap", url, current_timestamp(), type(exc).__name__.lower())

    status_code = response.status_code
    raw_response = _response_body(response)
    retry_after = str(getattr(response, "headers", {}).get("Retry-After", ""))
    if status_code == 404:
        if not _valid_not_found_response(response):
            status, error = "UNKNOWN", "invalid_rdap_not_found"
        elif not control_registered:
            status, error = "UNKNOWN", "control_unverified"
        else:
            status, error = "NO_REGISTRY_RECORD", ""
    elif 200 <= status_code < 300:
        if _valid_domain_object(response, domain):
            status, error = "REGISTERED", ""
        else:
            status, error = "UNKNOWN", "invalid_rdap_domain_object"
    elif status_code == 429:
        status = "UNKNOWN"
        error = "http_429_retry_after_exceeds_bound" if _retry_delay(response, 0) is None else "http_429"
    elif 500 <= status_code <= 599:
        status = "UNKNOWN"
        error = (
            f"http_{status_code}_retry_after_exceeds_bound"
            if _retry_delay(response, 0) is None
            else f"http_{status_code}"
        )
    else:
        status, error = "UNKNOWN", f"http_{status_code}"
    return DomainEvidence(
        domain, status, status_code, "rdap", url, current_timestamp(), error,
        raw_response=raw_response,
        retry_after=retry_after,
    )


def _valid_not_found_response(response: requests.Response) -> bool:
    try:
        payload = response.json()
    except (ValueError, requests.RequestException):
        return False
    return _valid_not_found_payload(payload)


def _valid_not_found_payload(payload: object) -> bool:
    return isinstance(payload, dict) and type(payload.get("errorCode")) is int and payload.get("errorCode") == 404


def _parse_io_whois_body(domain: str, body: str) -> Tuple[Optional[int], str]:
    normalized_domain = domain.strip().lower().rstrip(".")
    domain_field = re.search(r"(?im)^\s*Domain Name:\s*([^\s]+)\s*$", body)
    if domain_field:
        returned_domain = domain_field.group(1).rstrip(".").lower()
        if returned_domain == normalized_domain:
            return 200, ""
        return None, "whois_domain_mismatch"
    # An exact negative line is accepted only when the response contains no
    # registration fields that would contradict the no-record claim.
    record_fields = re.search(
        r"(?im)^\s*(Registrar|Creation Date|Updated Date|Registry Expiry Date|Name Server|nserver)\s*:",
        body,
    )
    if record_fields:
        return None, "whois_unparseable"
    negative_markers = (
        rf"(?im)^\s*Domain\s+{re.escape(normalized_domain)}\s+not found\.?\s*$",
        rf"(?im)^\s*No match for\s+{re.escape(normalized_domain)}\.?\s*$",
        r"(?im)^\s*Domain not found\.\s*$",
    )
    if any(re.search(pattern, body) for pattern in negative_markers):
        return 404, ""
    return None, "whois_unparseable"


def unsupported_result(domain: str, tld: str) -> DomainEvidence:
    return DomainEvidence(
        domain,
        "UNSUPPORTED",
        None,
        "iana-bootstrap",
        IANA_RDAP_BOOTSTRAP_URL,
        current_timestamp(),
        "unsupported_tld",
    )


def _whois_evidence(domain: str, timeout: float, retries: int, control_registered: bool) -> DomainEvidence:
    code, source, raw_response, query_error = _query_io_whois(domain, timeout, retries)
    if code == 200:
        status, error = "REGISTERED", ""
    elif code == 404 and control_registered:
        status, error = "NO_REGISTRY_RECORD", ""
    elif code == 404:
        status, error = "UNKNOWN", "control_unverified"
    else:
        status, error = "UNKNOWN", query_error or "whois_unparseable"
    return DomainEvidence(domain, status, code, "whois", source, current_timestamp(), error, raw_response=raw_response)


def load_jsonl_cache(path: Path, ttl_hours: float = 24) -> Dict[str, Dict[str, object]]:
    if not path.exists():
        return {}
    cutoff = datetime.now(timezone.utc).timestamp() - max(float(ttl_hours), 0) * 3600
    cache: Dict[str, Dict[str, object]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                record = json.loads(line)
                if not isinstance(record, dict):
                    continue
                domain = str(record.get("domain", "")).strip().lower()
                checked_at = str(record.get("checked_at", ""))
                parsed = datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    continue
                status = record.get("registry_status")
                raw_response = record.get("raw_response")
                source = record.get("source")
                receipt_status = _cache_receipt_status(source, domain, raw_response)
                if (
                    domain
                    and status in {"REGISTERED", "NO_REGISTRY_RECORD"}
                    and not record.get("error")
                    and isinstance(raw_response, str)
                    and raw_response
                    and receipt_status == status
                    and (
                        status != "NO_REGISTRY_RECORD"
                        or (record.get("control_status") == "REGISTERED" and record.get("control_domain"))
                    )
                    and cutoff <= parsed.timestamp() <= datetime.now(timezone.utc).timestamp()
                ):
                    cache[domain] = record
            except (ValueError, TypeError, json.JSONDecodeError):
                continue
    return cache


def _cache_receipt_status(source: object, domain: str, raw_response: object) -> Optional[str]:
    if not isinstance(raw_response, str) or not raw_response:
        return None
    if source == "rdap":
        try:
            payload = json.loads(raw_response)
        except json.JSONDecodeError:
            return None
        if _valid_domain_payload(payload, domain):
            return "REGISTERED"
        if _valid_not_found_payload(payload):
            return "NO_REGISTRY_RECORD"
        return None
    if source == "whois":
        code, error = _parse_io_whois_body(domain, raw_response)
        if not error and code == 200:
            return "REGISTERED"
        if not error and code == 404:
            return "NO_REGISTRY_RECORD"
    return None


def load_legacy_history(path: Path) -> Dict[str, Dict[str, str]]:
    """Legacy yes/no availability rows are intentionally not evidence."""
    return {}


def load_controls(path: Optional[Path] = None) -> Dict[str, str]:
    controls = dict(DEFAULT_CONTROLS)
    if path is None:
        return controls
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("controls JSON must be an object mapping TLD suffixes to domains")
    for raw_tld, raw_domain in data.items():
        tld = normalize_tlds([str(raw_tld)])[0]
        domain = str(raw_domain).strip().lower()
        labels = domain.split(".")
        if len(labels) < 2 or any(not _LABEL_RE.fullmatch(label) for label in labels):
            raise ValueError(f"Invalid control domain {raw_domain!r} for .{tld}.")
        if not domain.endswith("." + tld):
            raise ValueError(f"Control domain {domain!r} must end with .{tld}.")
        controls[tld] = domain
    return controls


def make_root_text(item: Candidate) -> str:
    if item.root_a and item.root_b:
        return f"{item.root_a}+{item.root_b}"
    return item.root_a or item.root_b or ""


def make_meaning_text(item: Candidate) -> str:
    return item.seed_meaning or item.what_works


def _evidence_value(entry: object, field: str, default: object = None) -> object:
    if isinstance(entry, DomainEvidence):
        return getattr(entry, field, default)
    if isinstance(entry, Mapping):
        return entry.get(field, default)
    return default


def build_live_row(
    item: Candidate,
    status_by_tld: Dict[str, object],
    tlds: List[str],
) -> Dict[str, str]:
    no_record_tld = next(
        (tld for tld in tlds if _evidence_value(status_by_tld[tld], "registry_status") == "NO_REGISTRY_RECORD"),
        "",
    )
    if no_record_tld:
        availability = "pending"
        domain_value = f"{item.stem}.{no_record_tld}"
        best_tld = no_record_tld
    else:
        best_tld = ""
        domain_value = item.candidate
        statuses = [_evidence_value(status_by_tld[tld], "registry_status") for tld in tlds]
        availability = "no" if statuses and all(value == "REGISTERED" for value in statuses) else "unknown"

    note = item.concern or ""
    if no_record_tld:
        note = (note + "；" if note else "") + "注册局未返回记录；仍需注册商结账与商标核查，不代表可购买"
        if no_record_tld != tlds[0]:
            note += f"（首选 .{tlds[0]} 未命中）"
    score = ""
    if item.brand_score_10:
        try:
            score = f"{float(item.brand_score_10):.1f}"
        except (TypeError, ValueError):
            score = ""
    evidence_times = [str(_evidence_value(value, "checked_at", "")) for value in status_by_tld.values()]
    checked_at = max(evidence_times, default=current_timestamp())
    sources = sorted({str(_evidence_value(value, "source", "")) for value in status_by_tld.values()} - {""})
    return {
        "域名": domain_value,
        "类型": best_tld,
        "思路": item.theme,
        "词根": make_root_text(item),
        "含义": make_meaning_text(item),
        "分数": score,
        "是否available": availability,
        "检查时间": checked_at,
        "备注": note,
        "查询来源": "+".join(sources) if sources else "unknown",
    }


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def validate_paths(input_path: Path, output_paths: Iterable[Path], cache_path: Path) -> None:
    outputs = list(output_paths)
    input_resolved = input_path.resolve()
    output_resolved = [path.resolve() for path in outputs]
    cache_resolved = cache_path.resolve()
    if (
        len(set(output_resolved)) != len(output_resolved)
        or input_resolved in output_resolved
        or cache_resolved in output_resolved
        or cache_resolved == input_resolved
    ):
        raise SystemExit("Input, outputs, and cache paths must not overlap.")
    existing = [path for path in outputs if path.exists()]
    if existing:
        raise SystemExit("Output path already exists; choose a new path: " + ", ".join(map(str, existing)))
    if cache_path.exists() and not cache_path.is_file():
        raise SystemExit(f"Cache path must be a file: {cache_path}")


def sort_key(row: Dict[str, str], tld_priority: Dict[str, int]) -> Tuple[int, int, float, str]:
    availability_rank = {"pending": 0, "no": 1, "unknown": 2}.get(row["是否available"], 3)
    try:
        score = float(row["分数"] or 0)
    except ValueError:
        score = 0
    return (
        availability_rank,
        tld_priority.get(row["类型"], 99),
        -score,
        row["域名"],
    )


def _thread_session() -> requests.Session:
    session = getattr(_thread_state, "session", None)
    if session is None:
        session = requests.Session()
        _thread_state.session = session
    return session


def _probe_one(
    session: requests.Session,
    domain: str,
    suffix: str,
    bootstrap_index: Mapping[str, str],
    timeout: float,
    retries: int,
    controls: Mapping[str, str],
    control_status: Mapping[str, str],
    bootstrap_ok: bool,
) -> DomainEvidence:
    registry_tld = suffix.rsplit(".", 1)[-1]
    if bootstrap_ok and registry_tld not in bootstrap_index and registry_tld != "io":
        return unsupported_result(domain, suffix)
    base = bootstrap_index.get(registry_tld)
    control_domain = controls.get(suffix) or controls.get(registry_tld) or ""
    verified = bool(control_domain and control_status.get(suffix, control_status.get(registry_tld)) == "REGISTERED")
    if base:
        evidence = probe_domain(session, domain, base, timeout, verified, retries)
    elif registry_tld == "io":
        evidence = _whois_evidence(domain, timeout, retries, verified)
    else:
        evidence = DomainEvidence(domain, "UNKNOWN", None, "iana-bootstrap", IANA_RDAP_BOOTSTRAP_URL, current_timestamp(), "bootstrap_unavailable")
    evidence.control_domain = control_domain
    evidence.control_status = control_status.get(suffix, control_status.get(registry_tld, "UNKNOWN"))
    return evidence


def main() -> int:
    args = parse_args()
    try:
        tlds = normalize_tlds(args.tlds.split(","))
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    input_path = Path(args.input).expanduser()
    output_all = Path(args.output_all).expanduser()
    output_shortlist = Path(args.output_shortlist).expanduser()
    output_evidence = Path(args.output_evidence).expanduser() if args.output_evidence else Path(str(output_all) + ".evidence.jsonl")
    cache_path = Path(args.cache_jsonl).expanduser()
    validate_paths(input_path, [output_all, output_shortlist, output_evidence], cache_path)
    candidates = load_candidates(input_path)
    cache = {} if args.ignore_history else load_jsonl_cache(cache_path, args.cache_ttl_hours)
    try:
        controls = load_controls(Path(args.controls_json).expanduser() if args.controls_json else None)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Unable to read control-domain configuration: {exc}") from exc

    bootstrap_session = requests.Session()
    try:
        bootstrap_index = build_bootstrap_index(bootstrap_session, args.timeout, args.retries)
        bootstrap_ok = True
        bootstrap_error = ""
    except (requests.RequestException, ValueError, json.JSONDecodeError) as exc:
        bootstrap_index = {}
        bootstrap_ok = False
        bootstrap_error = type(exc).__name__.lower()

    # A positive domain object is required from each registry before a 404 is
    # accepted as a no-record observation. This check is live on every run.
    control_status: Dict[str, str] = {}
    control_records: Dict[str, DomainEvidence] = {}
    for suffix in tlds:
        control_domain = controls.get(suffix) or controls.get(suffix.rsplit(".", 1)[-1])
        if not control_domain:
            control_status[suffix] = "UNKNOWN"
            control_records[suffix] = DomainEvidence(
                "", "UNKNOWN", None, "control", "", current_timestamp(), "control_not_configured"
            )
            continue
        registry_tld = suffix.rsplit(".", 1)[-1]
        if bootstrap_ok and registry_tld not in bootstrap_index and registry_tld != "io":
            control_status[suffix] = "UNKNOWN"
            control_records[suffix] = unsupported_result(control_domain, suffix)
            continue
        if not bootstrap_ok and registry_tld != "io":
            control_status[suffix] = "UNKNOWN"
            control_records[suffix] = DomainEvidence(
                control_domain, "UNKNOWN", None, "iana-bootstrap", IANA_RDAP_BOOTSTRAP_URL,
                current_timestamp(), bootstrap_error or "bootstrap_unavailable", control_domain, "UNKNOWN"
            )
            continue
        control_base = bootstrap_index.get(registry_tld)
        if control_base:
            record = probe_domain(bootstrap_session, control_domain, control_base, args.timeout, True, args.retries)
        elif registry_tld == "io":
            record = _whois_evidence(control_domain, args.timeout, args.retries, True)
        else:
            record = DomainEvidence(control_domain, "UNKNOWN", None, "control", "", current_timestamp(), "control_endpoint_unavailable")
        record.control_domain = control_domain
        record.control_status = record.registry_status
        control_status[suffix] = "REGISTERED" if record.registry_status == "REGISTERED" else "UNKNOWN"
        control_records[suffix] = record

    pairs = [(candidate, suffix) for candidate in candidates for suffix in tlds]
    workers = min(max(int(args.workers), 1), 3)

    def check_pair(pair: Tuple[Candidate, str]) -> DomainEvidence:
        item, suffix = pair
        domain = f"{item.stem}.{suffix}"
        cached = cache.get(domain)
        verified = control_status.get(suffix) == "REGISTERED"
        if cached and (cached.get("registry_status") == "REGISTERED" or verified):
            record = DomainEvidence(
                domain,
                str(cached["registry_status"]),
                cached.get("http_status"),
                str(cached.get("source", "cache")),
                str(cached.get("endpoint", "")),
                str(cached.get("checked_at", current_timestamp())),
                "",
                str(cached.get("control_domain", "")),
                str(cached.get("control_status", "UNKNOWN")),
                str(cached.get("raw_response", "")),
                str(cached.get("retry_after", "")),
                True,
            )
            return record
        # If cached absence is no longer control-verified, keep it explicitly
        # unknown instead of reusing an old 404 as a current absence claim.
        if cached and cached.get("registry_status") == "NO_REGISTRY_RECORD" and not verified:
            return DomainEvidence(
                domain,
                "UNKNOWN",
                cached.get("http_status"),
                str(cached.get("source", "cache")),
                str(cached.get("endpoint", "")),
                str(cached.get("checked_at", current_timestamp())),
                "control_unverified",
                controls.get(suffix, ""),
                "UNKNOWN",
                str(cached.get("raw_response", "")),
                str(cached.get("retry_after", "")),
                True,
            )
        if not bootstrap_ok and suffix.rsplit(".", 1)[-1] != "io":
            return DomainEvidence(domain, "UNKNOWN", None, "iana-bootstrap", IANA_RDAP_BOOTSTRAP_URL, current_timestamp(), bootstrap_error or "bootstrap_unavailable")
        return _probe_one(
            _thread_session(), domain, suffix, bootstrap_index, args.timeout, args.retries,
            controls, control_status, bootstrap_ok,
        )

    with ThreadPoolExecutor(max_workers=workers) as executor:
        evidence_rows = list(executor.map(check_pair, pairs))

    status_by_candidate: Dict[str, Dict[str, DomainEvidence]] = {item.stem: {} for item in candidates}
    evidence_records = [asdict(record) for record in control_records.values()]
    evidence_records.extend(asdict(record) for record in evidence_rows)
    for item, record in zip((candidate for candidate, _ in pairs), evidence_rows):
        suffix = record.domain[len(item.stem) + 1 :]
        status_by_candidate[item.stem][suffix] = record

    successful_to_cache = [
        record for record in evidence_rows
        if record.registry_status in {"REGISTERED", "NO_REGISTRY_RECORD"}
        and not record.error
        and not record.cache_hit
    ]
    if successful_to_cache:
        ensure_parent(cache_path)
        with cache_path.open("a", encoding="utf-8") as handle:
            for record in successful_to_cache:
                cache_record = asdict(record)
                handle.write(json.dumps(cache_record, ensure_ascii=False) + "\n")

    rows = [build_live_row(item, status_by_candidate[item.stem], tlds) for item in candidates]
    priority = {tld: index for index, tld in enumerate(tlds)}
    rows.sort(key=lambda row: sort_key(row, priority))
    shortlist = rows[: max(args.shortlist_limit, 0)]
    for path, contents in ((output_all, rows), (output_shortlist, shortlist)):
        ensure_parent(path)
        with path.open("x", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
            writer.writeheader()
            writer.writerows(contents)
    ensure_parent(output_evidence)
    with output_evidence.open("x", encoding="utf-8") as handle:
        for record in evidence_records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    pending = sum(row["是否available"] == "pending" for row in rows)
    print(f"Saved full results to {output_all}")
    print(f"Saved shortlist to {output_shortlist}")
    print(f"Saved domain evidence to {output_evidence}")
    print(f"Pending registrar verification: {pending}")
    if not bootstrap_ok:
        print(f"IANA bootstrap unavailable: {bootstrap_error}; results are UNKNOWN unless .io WHOIS responds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
