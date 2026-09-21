#!/usr/bin/env python3
"""Generate large brand-name candidate sets from curated seed families.

Usage:
  python3 generate_brand_candidates.py \
    --output /path/to/candidates.csv \
    --limit 1200
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


ROOT_FAMILIES = {
    "cortex-inspired": {
        "roots": ["cort", "corte", "corti", "corto"],
        "meanings": "智能、结构化认知、企业级 AI 感",
    },
    "synapse-inspired": {
        "roots": ["syn", "syne", "syna", "sync"],
        "meanings": "连接、协同、智能流动",
    },
    "cognition-inspired": {
        "roots": ["cogn", "cogne", "cogni", "cog"],
        "meanings": "认知、理解、判断质量",
    },
    "context-inspired": {
        "roots": ["cont", "conte", "contex", "con"],
        "meanings": "上下文、业务现场、状态连续性",
    },
    "recall-inspired": {
        "roots": ["reca", "recal", "rec", "trac"],
        "meanings": "记忆、回溯、延续、知识可复用",
    },
    "loom-inspired": {
        "roots": ["loom", "lume", "luma", "lum"],
        "meanings": "编织、沉淀、共享资产",
    },
    "atlas-inspired": {
        "roots": ["atl", "atlas", "atla", "atel"],
        "meanings": "全景、地图、组织视野",
    },
    "graph-inspired": {
        "roots": ["graf", "graph", "grap", "tess"],
        "meanings": "关系网络、知识结构、业务图谱",
    },
    "forge-inspired": {
        "roots": ["forg", "forge", "fora", "foro"],
        "meanings": "把碎片知识锻造成组织资产",
    },
    "trace-inspired": {
        "roots": ["trace", "trac", "line", "lin"],
        "meanings": "来源脉络、过程连续、知识轨迹",
    },
}

SUFFIX_GROUPS = {
    "soft-platform": ["ara", "era", "ora", "iva", "avo", "ena", "ella", "essa"],
    "enterprise-polished": ["etra", "etrax", "elis", "elle", "essa", "ivo", "aro"],
    "ai-leaning": ["iq", "ix", "ium", "yn", "is", "ive", "iqa"],
}

SECONDARY_MORPHEMES = {
    "memory-layer": ["trace", "line", "loom", "mesh", "state", "span", "flow"],
    "intelligence-layer": ["syn", "cogn", "sense", "atlas", "graph", "tess"],
    "coordination-layer": ["weave", "relay", "cad", "lane", "rail", "forge"],
}

AVOID_SUBSTRINGS = {
    "brain",
    "team",
    "org",
    "agent",
    "assist",
    "copilot",
    "chat",
    "task",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="Output CSV path.")
    parser.add_argument(
        "--limit",
        type=int,
        default=1200,
        help="Maximum number of candidates to write. Default: 1200",
    )
    return parser.parse_args()


def normalize(candidate: str) -> str:
    return "".join(ch for ch in candidate.lower() if ch.isalpha())


def title_case(stem: str) -> str:
    return stem[:1].upper() + stem[1:]


def looks_reasonable(stem: str) -> bool:
    if len(stem) < 6 or len(stem) > 12:
        return False
    if any(bad in stem for bad in AVOID_SUBSTRINGS):
        return False
    if stem.count("x") > 1 or stem.count("q") > 1:
        return False
    if any(doubled in stem for doubled in ["aaa", "eee", "iii", "ooo", "uuu"]):
        return False
    if len(set(stem)) < 4:
        return False
    return True


def generation_priority(stem: str, family: str, pattern: str) -> float:
    score = 6.0
    if 7 <= len(stem) <= 9:
        score += 1.6
    elif len(stem) <= 11:
        score += 1.0
    if family in {"cortex-inspired", "synapse-inspired", "cognition-inspired"}:
        score += 0.8
    if family in {"loom-inspired", "trace-inspired", "atlas-inspired"}:
        score += 0.5
    if pattern == "root+suffix":
        score += 0.7
    elif pattern == "root+bridge+suffix":
        score += 0.4
    if stem.endswith(("ara", "ora", "era", "iva", "ena", "elle")):
        score += 0.5
    if any(cluster in stem for cluster in ["syn", "cort", "cogn", "loom", "trac"]):
        score += 0.4
    return min(round(score, 1), 9.9)


def rationale(family: str, pattern: str, root_a: str, root_b: str, suffix: str) -> str:
    meaning = ROOT_FAMILIES[family]["meanings"]
    if pattern == "root+suffix":
        return f"{root_a}+{suffix}，保留 {meaning} 的联想，同时维持品牌词读感。"
    if pattern == "root+bridge+suffix":
        return f"{root_a}+{root_b}+{suffix}，把 {meaning} 和第二层产品隐喻拼在一起。"
    return f"{root_a}+{root_b} 的变体，强调 {meaning}。"


def concern(stem: str, pattern: str) -> str:
    notes = []
    if len(stem) >= 11:
        notes.append("略长")
    if stem.endswith(("iq", "ix", "ium")):
        notes.append("偏 AI 工具名")
    if pattern != "root+suffix":
        notes.append("造词感更强")
    return "，".join(notes) if notes else "需要后续域名和商标筛选。"


def build_family_rows() -> dict[str, list[dict[str, object]]]:
    family_rows: dict[str, list[dict[str, object]]] = {}
    seen: set[str] = set()

    suffix_items = [
        (group, suffix)
        for group, suffixes in SUFFIX_GROUPS.items()
        for suffix in suffixes
    ]
    secondary_items = [
        (group, morph)
        for group, morphemes in SECONDARY_MORPHEMES.items()
        for morph in morphemes
    ]

    for family, meta in ROOT_FAMILIES.items():
        family_rows[family] = []
        for root in meta["roots"]:
            for suffix_group, suffix in suffix_items:
                stem = normalize(root + suffix)
                if not looks_reasonable(stem) or stem in seen:
                    continue
                seen.add(stem)
                family_rows[family].append(
                    {
                        "candidate": title_case(stem),
                        "theme": family,
                        "brand_score_10": "",
                        "generation_priority": generation_priority(stem, family, "root+suffix"),
                        "generation_priority_note": "仅用于候选生成顺序的形态启发式，不代表品牌质量评分。",
                        "what_works": rationale(
                            family, "root+suffix", root, "", suffix
                        ),
                        "concern": concern(stem, "root+suffix"),
                        "pattern": "root+suffix",
                        "root_a": root,
                        "root_b": "",
                        "suffix": suffix,
                        "seed_meaning": meta["meanings"],
                    }
                )

            for morph_group, morph in secondary_items:
                for suffix_group, suffix in suffix_items:
                    stem = normalize(root + morph + suffix)
                    if not looks_reasonable(stem) or stem in seen:
                        continue
                    seen.add(stem)
                    family_rows[family].append(
                        {
                            "candidate": title_case(stem),
                            "theme": family,
                            "brand_score_10": "",
                            "generation_priority": generation_priority(
                                stem, family, "root+bridge+suffix"
                            ),
                            "generation_priority_note": "仅用于候选生成顺序的形态启发式，不代表品牌质量评分。",
                            "what_works": rationale(
                                family, "root+bridge+suffix", root, morph, suffix
                            ),
                            "concern": concern(stem, "root+bridge+suffix"),
                            "pattern": "root+bridge+suffix",
                            "root_a": root,
                            "root_b": morph,
                            "suffix": suffix,
                            "seed_meaning": meta["meanings"],
                        }
                    )
    return family_rows


def generate_rows(limit: int) -> list[dict[str, object]]:
    family_rows = build_family_rows()
    ordered_families = list(ROOT_FAMILIES.keys())
    indices = {family: 0 for family in ordered_families}
    rows: list[dict[str, object]] = []

    while len(rows) < limit:
        emitted = False
        for family in ordered_families:
            idx = indices[family]
            bucket = family_rows.get(family, [])
            if idx >= len(bucket):
                continue
            rows.append(bucket[idx])
            indices[family] += 1
            emitted = True
            if len(rows) >= limit:
                break
        if not emitted:
            break

    return rows


def write_candidates(output: Path, limit: int) -> list[dict[str, object]]:
    rows = generate_rows(limit)
    output = Path(output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "candidate",
        "theme",
        "brand_score_10",
        "generation_priority",
        "generation_priority_note",
        "what_works",
        "concern",
        "pattern",
        "root_a",
        "root_b",
        "suffix",
        "seed_meaning",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def main() -> int:
    args = parse_args()
    output = Path(args.output).expanduser()
    rows = write_candidates(output, args.limit)
    print(f"Saved {len(rows)} candidates to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
