#!/usr/bin/env python3
"""Parse, validate, and export CaseForge 7-column testcase tables."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import re
import sys
import zipfile
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape


HEADERS = ["用例名称", "所属模块", "前置条件", "步骤描述", "预期结果", "用例等级", "编辑模式"]
LEVELS = {"P0", "P1", "P2", "P3"}


def normalize_header(value: str) -> str:
    return re.sub(r"\s+", "", value.strip().strip("`"))


def split_markdown_table_row(line: str) -> list[str]:
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|"):
        text = text[:-1]

    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in text:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "|":
            cells.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    if escaped:
        current.append("\\")
    cells.append("".join(current).strip())
    return cells


def is_separator(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def parse_markdown_table(markdown_text: str) -> list[list[str]]:
    expected = [normalize_header(header) for header in HEADERS]
    lines = markdown_text.splitlines()
    for index, line in enumerate(lines):
        if "|" not in line:
            continue
        cells = split_markdown_table_row(line)
        if [normalize_header(cell) for cell in cells] != expected:
            continue

        rows: list[list[str]] = []
        for row_line in lines[index + 1 :]:
            if "|" not in row_line:
                if rows:
                    break
                continue
            row_cells = split_markdown_table_row(row_line)
            if len(row_cells) != len(HEADERS):
                if rows:
                    break
                continue
            if is_separator(row_cells):
                continue
            rows.append(row_cells)
        if rows:
            return rows
    raise RuntimeError("No fixed 7-column testcase Markdown table found.")


def read_csv_rows(path: Path) -> list[list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.reader(file))
    if not rows:
        raise RuntimeError("CSV is empty.")
    if rows[0] != HEADERS:
        raise RuntimeError(f"CSV header mismatch: {rows[0]}")
    return rows[1:]


def write_csv_rows(path: Path, rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(HEADERS)
        writer.writerows(rows)


def validate_rows(rows: list[list[str]], module: str | None = None) -> list[str]:
    errors: list[str] = []
    seen_names: set[str] = set()
    for row_index, row in enumerate(rows, 2):
        if len(row) != len(HEADERS):
            errors.append(f"row {row_index}: expected 7 columns, got {len(row)}")
            continue
        record = dict(zip(HEADERS, row))
        if not all(value.strip() for value in row):
            errors.append(f"row {row_index}: empty cell exists")
        name = record["用例名称"]
        if name in seen_names:
            errors.append(f"row {row_index}: duplicate case name {name}")
        seen_names.add(name)
        if module and record["所属模块"] != module:
            errors.append(f"row {row_index}: module {record['所属模块']} != {module}")
        if record["用例等级"] not in LEVELS:
            errors.append(f"row {row_index}: invalid level {record['用例等级']}")
        if record["编辑模式"] != "STEP":
            errors.append(f"row {row_index}: 编辑模式 must be STEP")
        joined = "".join(row)
        if "\\n" in joined or "<br" in joined.lower():
            errors.append(f"row {row_index}: contains forbidden line break marker")
        step_nums = re.findall(r"\[(\d+)\]", record["步骤描述"])
        expected_nums = re.findall(r"\[(\d+)\]", record["预期结果"])
        if step_nums != expected_nums:
            errors.append(f"row {row_index}: step numbers {step_nums} != expected numbers {expected_nums}")
    return errors


def col_name(index: int) -> str:
    name = ""
    number = index + 1
    while number:
        number, remainder = divmod(number - 1, 26)
        name = chr(65 + remainder) + name
    return name


def cell_xml(row_index: int, column_index: int, value: Any, style_id: int) -> str:
    ref = f"{col_name(column_index)}{row_index}"
    text = escape("" if value is None else str(value))
    return f'<c r="{ref}" t="inlineStr" s="{style_id}"><is><t xml:space="preserve">{text}</t></is></c>'


def build_sheet_xml(rows: list[list[str]]) -> str:
    all_rows = [HEADERS, *rows]
    row_xml: list[str] = []
    for row_index, row in enumerate(all_rows, 1):
        style_id = 1 if row_index == 1 else 2
        height = ' ht="28" customHeight="1"' if row_index == 1 else ' ht="46" customHeight="1"'
        cells = "".join(cell_xml(row_index, column_index, value, style_id) for column_index, value in enumerate(row))
        row_xml.append(f'<row r="{row_index}"{height}>{cells}</row>')

    last_ref = f"{col_name(len(HEADERS) - 1)}{len(all_rows)}"
    widths = [36, 24, 44, 72, 72, 12, 12]
    cols = "".join(f'<col min="{i}" max="{i}" width="{width}" customWidth="1"/>' for i, width in enumerate(widths, 1))
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <dimension ref="A1:{last_ref}"/>
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/><selection pane="bottomLeft"/></sheetView></sheetViews>
  <cols>{cols}</cols>
  <sheetData>{''.join(row_xml)}</sheetData>
  <autoFilter ref="A1:{last_ref}"/>
</worksheet>'''


def build_xlsx(path: Path, rows: list[list[str]]) -> None:
    created = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    files = {
        "[Content_Types].xml": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>''',
        "_rels/.rels": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>''',
        "docProps/app.xml": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>CaseForge Skill</Application>
</Properties>''',
        "docProps/core.xml": f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>测试用例</dc:title>
  <dc:creator>CaseForge Skill</dc:creator>
  <cp:lastModifiedBy>CaseForge Skill</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified>
</cp:coreProperties>''',
        "xl/workbook.xml": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="测试用例" sheetId="1" r:id="rId1"/></sheets>
</workbook>''',
        "xl/_rels/workbook.xml.rels": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>''',
        "xl/styles.xml": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2"><font><sz val="11"/><name val="Microsoft YaHei"/></font><font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Microsoft YaHei"/></font></fonts>
  <fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF174E63"/><bgColor indexed="64"/></patternFill></fill></fills>
  <borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border><border><left style="thin"><color rgb="FFD7DEE8"/></left><right style="thin"><color rgb="FFD7DEE8"/></right><top style="thin"><color rgb="FFD7DEE8"/></top><bottom style="thin"><color rgb="FFD7DEE8"/></bottom><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf><xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>''',
        "xl/worksheets/sheet1.xml": build_sheet_xml(rows),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename, content in files.items():
            archive.writestr(filename, content.encode("utf-8"))
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f"XLSX zip validation failed at {bad}")


def print_validation(errors: list[str], count: int) -> int:
    print(f"cases={count}")
    if errors:
        print("errors:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("errors=none")
    return 0


def command_from_markdown(args: argparse.Namespace) -> int:
    rows = parse_markdown_table(args.markdown.read_text(encoding="utf-8"))
    errors = validate_rows(rows, args.module)
    if errors:
        return print_validation(errors, len(rows))
    if args.csv:
        write_csv_rows(args.csv, rows)
        print(f"csv={args.csv}")
    if args.xlsx:
        build_xlsx(args.xlsx, rows)
        print(f"xlsx={args.xlsx}")
    return print_validation(errors, len(rows))


def command_validate_csv(args: argparse.Namespace) -> int:
    rows = read_csv_rows(args.csv)
    return print_validation(validate_rows(rows, args.module), len(rows))


def command_validate_markdown(args: argparse.Namespace) -> int:
    rows = parse_markdown_table(args.markdown.read_text(encoding="utf-8"))
    return print_validation(validate_rows(rows, args.module), len(rows))


def command_csv_to_xlsx(args: argparse.Namespace) -> int:
    rows = read_csv_rows(args.csv)
    errors = validate_rows(rows, args.module)
    if errors:
        return print_validation(errors, len(rows))
    build_xlsx(args.xlsx, rows)
    print(f"xlsx={args.xlsx}")
    return print_validation(errors, len(rows))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CaseForge testcase table utilities.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    from_md = subparsers.add_parser("from-markdown", help="Parse Markdown table and export CSV/XLSX")
    from_md.add_argument("--markdown", type=Path, required=True)
    from_md.add_argument("--csv", type=Path)
    from_md.add_argument("--xlsx", type=Path)
    from_md.add_argument("--module")
    from_md.set_defaults(func=command_from_markdown)

    validate_csv = subparsers.add_parser("validate-csv", help="Validate a 7-column CSV")
    validate_csv.add_argument("--csv", type=Path, required=True)
    validate_csv.add_argument("--module")
    validate_csv.set_defaults(func=command_validate_csv)

    validate_md = subparsers.add_parser("validate-markdown", help="Validate a 7-column Markdown table")
    validate_md.add_argument("--markdown", type=Path, required=True)
    validate_md.add_argument("--module")
    validate_md.set_defaults(func=command_validate_markdown)

    csv_to_xlsx = subparsers.add_parser("csv-to-xlsx", help="Convert CSV to XLSX")
    csv_to_xlsx.add_argument("--csv", type=Path, required=True)
    csv_to_xlsx.add_argument("--xlsx", type=Path, required=True)
    csv_to_xlsx.add_argument("--module")
    csv_to_xlsx.set_defaults(func=command_csv_to_xlsx)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:  # noqa: BLE001
        print(f"error={exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
