#!/usr/bin/env python3
"""Validate sealed naming-origin cards by reconstructing every output character.

This validates provenance record consistency only. It does not judge brand
quality, etymological truth beyond the supplied pools, or commercial clearance.
"""

import argparse
import json
from pathlib import Path


def _span(value, field, length):
    if (not isinstance(value, list) or len(value) != 2
            or any(not isinstance(v, int) or isinstance(v, bool) for v in value)):
        raise ValueError(f"{field} must be [start,end] integers")
    start, end = value
    if not 0 <= start < end <= length:
        raise ValueError(f"{field} out of range")
    return start, end


def validate_card(card):
    errors = []
    if not isinstance(card, dict):
        return ["card must be an object"]
    name = card.get("name")
    construction = card.get("construction")
    if not isinstance(name, str) or not name.strip():
        return ["name must be a nonempty string"]
    if not isinstance(construction, dict):
        return ["construction must be an object"]
    output = construction.get("output")
    if not isinstance(output, str) or not output:
        return ["construction.output must be a nonempty string"]
    if output.casefold() != name.strip().casefold():
        errors.append("name and construction.output differ")

    roots = {}
    for item in card.get("source_roots", []):
        if not isinstance(item, dict) or not isinstance(item.get("word"), str):
            errors.append("invalid source_roots entry")
            continue
        roots[item["word"]] = item["word"]

    coverage = [[] for _ in output]

    def cover(span, label):
        start, end = span
        for index in range(start, end):
            coverage[index].append(label)

    for index, item in enumerate(construction.get("retained_spans", [])):
        label = f"retained_spans[{index}]"
        if not isinstance(item, dict):
            errors.append(label + " must be an object")
            continue
        source = item.get("source")
        text = item.get("text")
        if source not in roots:
            errors.append(label + " refers to an undeclared source")
            continue
        try:
            source_span = _span(item.get("span"), label + ".span", len(source))
            output_span = _span(item.get("output_span"), label + ".output_span", len(output))
        except ValueError as exc:
            errors.append(str(exc)); continue
        if source[source_span[0]:source_span[1]] != text:
            errors.append(label + " text does not match source span")
        if output[output_span[0]:output_span[1]] != text:
            errors.append(label + " text does not match output span")
        cover(output_span, label)

    for index, item in enumerate(construction.get("inserted_spans", [])):
        label = f"inserted_spans[{index}]"
        if not isinstance(item, dict):
            errors.append(label + " must be an object")
            continue
        text = item.get("text")
        try:
            output_span = _span(item.get("output_span"), label + ".output_span", len(output))
        except ValueError as exc:
            errors.append(str(exc)); continue
        if not isinstance(text, str) or len(text) != output_span[1] - output_span[0]:
            errors.append(label + " text length does not match output span")
        elif output[output_span[0]:output_span[1]] != text:
            errors.append(label + " text does not match output span")
        cover(output_span, label)

    for index, item in enumerate(construction.get("mutated_spans", [])):
        label = f"mutated_spans[{index}]"
        if not isinstance(item, dict):
            errors.append(label + " must be an object")
            continue
        source = item.get("source")
        if source not in roots:
            errors.append(label + " refers to an undeclared source")
            continue
        try:
            source_span = _span(item.get("source_span"), label + ".source_span", len(source))
            output_span = _span(item.get("output_span"), label + ".output_span", len(output))
        except ValueError as exc:
            errors.append(str(exc)); continue
        source_text = item.get("source_text")
        output_text = item.get("output_text")
        if source[source_span[0]:source_span[1]] != source_text:
            errors.append(label + " source_text does not match source span")
        if not isinstance(output_text, str) or len(output_text) != output_span[1] - output_span[0]:
            errors.append(label + " output_text length does not match output span")
        elif output[output_span[0]:output_span[1]] != output_text:
            errors.append(label + " output_text does not match output span")
        cover(output_span, label)

    for index, item in enumerate(construction.get("overlap_spans", [])):
        label = f"overlap_spans[{index}]"
        if not isinstance(item, dict):
            errors.append(label + " must be an object")
            continue
        text = item.get("text")
        try:
            output_span = _span(item.get("output_span"), label + ".output_span", len(output))
        except ValueError as exc:
            errors.append(str(exc)); continue
        if output[output_span[0]:output_span[1]] != text:
            errors.append(label + " text does not match output span")
        # An overlap explains shared provenance; retained/mutated/inserted spans
        # still own the output characters, so overlap does not add coverage.

    for index, owners in enumerate(coverage):
        if not owners:
            errors.append(f"output character {index} ({output[index]!r}) has no provenance")
        elif len(owners) > 1:
            errors.append(f"output character {index} ({output[index]!r}) is double-counted by {owners}")
    return errors


def validate_cards(cards):
    if not isinstance(cards, list):
        raise ValueError("origin-card file must be a JSON array")
    results = []
    for index, card in enumerate(cards):
        errors = validate_card(card)
        results.append({
            "index": index,
            "name": card.get("name") if isinstance(card, dict) else None,
            "status": "VALID" if not errors else "SOURCE_RECORD_INCONSISTENT",
            "errors": errors,
        })
    return {"complete": all(item["status"] == "VALID" for item in results), "cards": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("origin_cards")
    parser.add_argument("--output")
    args = parser.parse_args()
    cards = json.loads(Path(args.origin_cards).read_text(encoding="utf-8"))
    result = validate_cards(cards)
    content = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(content, encoding="utf-8")
    print(content, end="")
    return 0 if result["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
