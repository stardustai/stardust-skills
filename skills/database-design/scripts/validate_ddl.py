#!/usr/bin/env python3
"""生成式 SQL 的轻量级 DDL 质量护栏。

该脚本只检查一组范围明确、容易解释的规则。它不是完整 SQL 解析器，
也不能替代目标数据库、迁移工具或查询执行计划测试。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


IDENT_PART = r'(?:"[^"]+"|`[^`]+`|\[[^\]]+\]|[A-Za-z_][A-Za-z0-9_$]*)'
QUALIFIED_IDENT = rf'{IDENT_PART}(?:\s*\.\s*{IDENT_PART})*'
CREATE_TABLE_RE = re.compile(
    rf'\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?P<name>{QUALIFIED_IDENT})\s*\(',
    re.IGNORECASE,
)
CREATE_INDEX_RE = re.compile(
    rf'\bCREATE\s+(?P<unique>UNIQUE\s+)?INDEX\s+(?:CONCURRENTLY\s+)?'
    rf'(?:IF\s+NOT\s+EXISTS\s+)?(?P<name>{QUALIFIED_IDENT})\s+ON\s+'
    rf'(?P<table>{QUALIFIED_IDENT})(?:\s+USING\s+[A-Za-z_][A-Za-z0-9_$]*)?\s*\(',
    re.IGNORECASE,
)
TABLE_CONSTRAINT_PREFIXES = (
    'constraint ',
    'primary key',
    'foreign key',
    'unique ',
    'unique(',
    'check ',
    'check(',
    'exclude ',
)
GENERIC_NAMES = {'data', 'value', 'type', 'status', 'info', 'extra', 'ext', 'flag', 'field'}
MONEY_HINTS = ('amount', 'price', 'cost', 'balance', 'salary', 'wage', 'fee', 'money', 'total')


@dataclass(frozen=True)
class Diagnostic:
    severity: str
    code: str
    message: str


@dataclass
class Column:
    name: str
    sql: str


@dataclass
class Table:
    name: str
    body: str
    tail: str
    start: int
    columns: list[Column]


@dataclass
class Index:
    name: str
    table: str
    columns: tuple[str, ...]
    start: int
    unique: bool


class ChineseArgumentParser(argparse.ArgumentParser):
    """将 argparse 自带的帮助标题翻译为中文。"""

    def format_help(self) -> str:
        return (
            super()
            .format_help()
            .replace('usage:', '用法：')
            .replace('positional arguments:', '位置参数：')
            .replace('options:', '选项：')
            .replace('show this help message and exit', '显示帮助并退出')
        )


def normalize_ident(value: str) -> str:
    parts = re.split(r'\s*\.\s*', value.strip())
    cleaned = []
    for part in parts:
        if len(part) >= 2 and ((part[0], part[-1]) in {('"', '"'), ('`', '`'), ('[', ']')}):
            part = part[1:-1]
        cleaned.append(part.lower())
    return '.'.join(cleaned)


def short_name(value: str) -> str:
    return normalize_ident(value).split('.')[-1]


def is_snake_case(value: str) -> bool:
    return bool(re.fullmatch(r'[a-z][a-z0-9]*(?:_[a-z0-9]+)*', short_name(value)))


def find_matching_paren(sql: str, opening: int) -> int:
    depth = 0
    quote: str | None = None
    line_comment = False
    block_comment = False
    i = opening
    while i < len(sql):
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < len(sql) else ''
        if line_comment:
            if ch == '\n':
                line_comment = False
            i += 1
            continue
        if block_comment:
            if ch == '*' and nxt == '/':
                block_comment = False
                i += 2
            else:
                i += 1
            continue
        if quote:
            if ch == quote:
                if nxt == quote and quote in {"'", '"'}:
                    i += 2
                    continue
                quote = None
            elif ch == '\\' and quote == "'":
                i += 2
                continue
            i += 1
            continue
        if ch == '-' and nxt == '-':
            line_comment = True
            i += 2
            continue
        if ch == '/' and nxt == '*':
            block_comment = True
            i += 2
            continue
        if ch in {"'", '"', '`'}:
            quote = ch
            i += 1
            continue
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError(f'从第 {opening} 个字符开始的括号没有闭合')


def split_top_level(text: str) -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    quote: str | None = None
    line_comment = False
    block_comment = False
    i = 0
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ''
        if line_comment:
            if ch == '\n':
                line_comment = False
            i += 1
            continue
        if block_comment:
            if ch == '*' and nxt == '/':
                block_comment = False
                i += 2
            else:
                i += 1
            continue
        if quote:
            if ch == quote:
                if nxt == quote and quote in {"'", '"'}:
                    i += 2
                    continue
                quote = None
            elif ch == '\\' and quote == "'":
                i += 2
                continue
            i += 1
            continue
        if ch == '-' and nxt == '-':
            line_comment = True
            i += 2
            continue
        if ch == '/' and nxt == '*':
            block_comment = True
            i += 2
            continue
        if ch in {"'", '"', '`'}:
            quote = ch
        elif ch == '(':
            depth += 1
        elif ch == ')':
            depth = max(0, depth - 1)
        elif ch == ',' and depth == 0:
            parts.append(text[start:i].strip())
            start = i + 1
        i += 1
    final = text[start:].strip()
    if final:
        parts.append(final)
    return parts


def parse_column(segment: str) -> Column | None:
    cleaned = re.sub(r'^\s*(?:--[^\n]*\n\s*)+', '', segment)
    lowered = cleaned.lower().lstrip()
    if not lowered or lowered.startswith(TABLE_CONSTRAINT_PREFIXES):
        return None
    match = re.match(rf'\s*(?P<name>{IDENT_PART})\s+', cleaned)
    if not match:
        return None
    return Column(normalize_ident(match.group('name')), segment.strip())


def parse_tables(sql: str) -> list[Table]:
    tables: list[Table] = []
    for match in CREATE_TABLE_RE.finditer(sql):
        opening = match.end() - 1
        closing = find_matching_paren(sql, opening)
        semicolon = sql.find(';', closing)
        if semicolon == -1:
            semicolon = len(sql)
        body = sql[opening + 1:closing]
        columns = [column for segment in split_top_level(body) if (column := parse_column(segment))]
        tables.append(
            Table(
                name=normalize_ident(match.group('name')),
                body=body,
                tail=sql[closing + 1:semicolon],
                start=match.start(),
                columns=columns,
            )
        )
    return tables


def parse_index_columns(sql: str, opening: int) -> tuple[str, ...]:
    closing = find_matching_paren(sql, opening)
    values = []
    for value in split_top_level(sql[opening + 1:closing]):
        value = re.sub(r'\s+(ASC|DESC)(\s+NULLS\s+(FIRST|LAST))?\s*$', '', value, flags=re.I)
        value = re.sub(r'\s+COLLATE\s+\S+', '', value, flags=re.I)
        values.append(re.sub(r'\s+', ' ', value.strip()).lower())
    return tuple(values)


def parse_indexes(sql: str) -> list[Index]:
    indexes: list[Index] = []
    for match in CREATE_INDEX_RE.finditer(sql):
        opening = match.end() - 1
        indexes.append(
            Index(
                name=normalize_ident(match.group('name')),
                table=normalize_ident(match.group('table')),
                columns=parse_index_columns(sql, opening),
                start=match.start(),
                unique=bool(match.group('unique')),
            )
        )
    return indexes


def infer_dialect(sql: str) -> str:
    if re.search(r'\bCOMMENT\s+ON\s+(TABLE|COLUMN)\b', sql, re.I):
        return 'postgresql'
    if re.search(r'\bAUTO_INCREMENT\b|\bENGINE\s*=|\bCOMMENT\s*=', sql, re.I):
        return 'mysql'
    if re.search(r'\bAUTOINCREMENT\b|\bPRAGMA\b|\bWITHOUT\s+ROWID\b', sql, re.I):
        return 'sqlite'
    return 'unknown'


def load_catalog(path: Path | None) -> dict[str, dict]:
    if path is None:
        return {}
    raw = json.loads(path.read_text(encoding='utf-8'))
    tables = raw.get('tables', raw)
    if not isinstance(tables, dict):
        raise ValueError('数据字典必须包含 tables 对象')
    return {normalize_ident(name): value for name, value in tables.items() if isinstance(value, dict)}


def catalog_has_table(catalog: dict[str, dict], table: str) -> bool:
    entry = catalog.get(table) or catalog.get(short_name(table))
    return bool(entry and str(entry.get('description', '')).strip())


def catalog_has_column(catalog: dict[str, dict], table: str, column: str) -> bool:
    entry = catalog.get(table) or catalog.get(short_name(table)) or {}
    columns = entry.get('columns', {})
    value = columns.get(column) if isinstance(columns, dict) else None
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return bool(str(value.get('description', '')).strip())
    return False


def pg_comment_sets(sql: str) -> tuple[set[str], set[tuple[str, str]]]:
    table_comments = {
        normalize_ident(m.group('name'))
        for m in re.finditer(
            rf'\bCOMMENT\s+ON\s+TABLE\s+(?P<name>{QUALIFIED_IDENT})\s+IS\s+\'(?!\s*\')',
            sql,
            re.I,
        )
    }
    column_comments: set[tuple[str, str]] = set()
    for match in re.finditer(
        rf'\bCOMMENT\s+ON\s+COLUMN\s+(?P<name>{QUALIFIED_IDENT})\s+IS\s+\'(?!\s*\')',
        sql,
        re.I,
    ):
        parts = normalize_ident(match.group('name')).split('.')
        if len(parts) >= 2:
            column_comments.add(('.'.join(parts[:-1]), parts[-1]))
    return table_comments, column_comments


def sqlite_table_source_comment(sql: str, table: Table) -> bool:
    prefix = sql[max(0, table.start - 300):table.start]
    name = re.escape(short_name(table.name))
    return bool(re.search(rf'--\s*(?:Table|表)\s+[`"\[]?{name}[`"\]]?\s*[:：]\s*\S+', prefix, re.I))


def has_column_description(
    dialect: str,
    sql: str,
    table: Table,
    column: Column,
    pg_columns: set[tuple[str, str]],
    catalog: dict[str, dict],
) -> bool:
    if dialect == 'sqlite' and catalog_has_column(catalog, table.name, column.name):
        return True
    if dialect == 'postgresql':
        candidates = {(table.name, column.name), (short_name(table.name), column.name)}
        return bool(candidates & pg_columns)
    if dialect == 'mysql':
        return bool(re.search(r"\bCOMMENT\s+'(?:''|[^'])+?'", column.sql, re.I | re.S))
    if dialect == 'sqlite':
        name = re.escape(column.name)
        line_marker = rf'--\s*(?:(?:Column|字段)\s+)?[`"\[]?{name}[`"\]]?\s*[:：]\s*\S+'
        block_marker = rf'/\*\s*(?:(?:Column|字段)\s+)?[`"\[]?{name}[`"\]]?\s*[:：]\s*\S.*?\*/'
        leading_line = r'^\s*--\s*\S[^\n]*\n'
        leading_block = r'^\s*/\*\s*\S.*?\*/\s*'
        return bool(
            re.search(line_marker, column.sql, re.I)
            or re.search(block_marker, column.sql, re.I | re.S)
            or re.search(leading_line, column.sql)
            or re.search(leading_block, column.sql, re.S)
        )
    return False


def table_has_description(
    dialect: str,
    sql: str,
    table: Table,
    pg_tables: set[str],
    catalog: dict[str, dict],
) -> bool:
    if dialect == 'sqlite' and catalog_has_table(catalog, table.name):
        return True
    if dialect == 'postgresql':
        return table.name in pg_tables or short_name(table.name) in pg_tables
    if dialect == 'mysql':
        return bool(re.search(r"\bCOMMENT\s*(?:=\s*)?'(?:''|[^'])+?'", table.tail, re.I | re.S))
    if dialect == 'sqlite':
        return sqlite_table_source_comment(sql, table)
    return False


def extract_constraint_column_sets(table: Table, keyword: str) -> list[tuple[str, ...]]:
    result: list[tuple[str, ...]] = []
    pattern = re.compile(rf'\b{keyword}\s*\((?P<cols>[^)]+)\)', re.I | re.S)
    for match in pattern.finditer(table.body):
        cols = tuple(
            normalize_ident(re.sub(r'\s+(ASC|DESC)\b.*$', '', part.strip(), flags=re.I))
            for part in split_top_level(match.group('cols'))
        )
        result.append(cols)
    for column in table.columns:
        if re.search(rf'\b{keyword}\b', column.sql, re.I):
            result.append((column.name,))
    return result


def nearby_index_reason(sql: str, start: int) -> bool:
    prefix = sql[max(0, start - 400):start]
    after_previous_statement = prefix.rsplit(';', 1)[-1]
    return bool(re.search(r'--\s*(Supports|Query|Reason|支持|查询|原因)\s*[:：]\s*\S+', after_previous_statement, re.I))


def validate_text(sql: str, dialect: str, level: str, catalog: dict[str, dict] | None = None) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    catalog = catalog or {}
    if dialect == 'auto':
        dialect = infer_dialect(sql)
    if dialect == 'unknown':
        diagnostics.append(Diagnostic('ERROR', 'DIALECT', '无法推断 SQL 方言，请显式传入 --dialect。'))
    try:
        tables = parse_tables(sql)
        indexes = parse_indexes(sql)
    except ValueError as exc:
        return [Diagnostic('ERROR', 'PARSE', str(exc))]
    if not tables:
        diagnostics.append(Diagnostic('ERROR', 'NO_TABLES', '没有找到 CREATE TABLE 语句。'))
        return diagnostics

    pg_tables, pg_columns = pg_comment_sets(sql) if dialect == 'postgresql' else (set(), set())
    table_map = {table.name: table for table in tables}
    table_map.update({short_name(table.name): table for table in tables})

    for table in tables:
        if not is_snake_case(table.name):
            diagnostics.append(Diagnostic('WARN', 'TABLE_NAME', f'{table.name}：建议统一使用 snake_case 命名。'))
        if not table_has_description(dialect, sql, table, pg_tables, catalog):
            diagnostics.append(Diagnostic('ERROR', 'TABLE_COMMENT', f'{table.name}：缺少非空表说明。'))
        if not table.columns:
            diagnostics.append(Diagnostic('ERROR', 'NO_COLUMNS', f'{table.name}：没有解析到字段。'))
            continue
        primary_sets = extract_constraint_column_sets(table, r'PRIMARY\s+KEY')
        if not primary_sets:
            diagnostics.append(Diagnostic('ERROR', 'PRIMARY_KEY', f'{table.name}：缺少主键。'))
        for column in table.columns:
            if not is_snake_case(column.name):
                diagnostics.append(Diagnostic('WARN', 'COLUMN_NAME', f'{table.name}.{column.name}：建议使用 snake_case 命名。'))
            if column.name in GENERIC_NAMES:
                diagnostics.append(Diagnostic('WARN', 'AMBIGUOUS_NAME', f'{table.name}.{column.name}：名称过于通用，必须提供特别明确的业务语义。'))
            if not has_column_description(dialect, sql, table, column, pg_columns, catalog):
                diagnostics.append(Diagnostic('ERROR', 'COLUMN_COMMENT', f'{table.name}.{column.name}：缺少非空字段说明。'))
            if not re.search(r'\bNOT\s+NULL\b|\bNULL\b|\bPRIMARY\s+KEY\b', column.sql, re.I):
                diagnostics.append(Diagnostic('WARN', 'NULLABILITY', f'{table.name}.{column.name}：可空性没有显式声明。'))
            if any(hint in column.name for hint in MONEY_HINTS) and re.search(r'\b(FLOAT|REAL|DOUBLE)\b', column.sql, re.I):
                severity = 'WARN' if level == 'demo' else 'ERROR'
                diagnostics.append(Diagnostic(severity, 'MONEY_FLOAT', f'{table.name}.{column.name}：疑似金额字段使用了浮点类型。'))
            if dialect == 'postgresql' and column.name.endswith('_at'):
                has_timestamp = bool(re.search(r'\bTIMESTAMP\b|\bTIMESTAMPTZ\b', column.sql, re.I))
                has_timezone = bool(re.search(r'\bTIMESTAMPTZ\b|\bWITH\s+TIME\s+ZONE\b', column.sql, re.I))
                if has_timestamp and not has_timezone:
                    diagnostics.append(Diagnostic('WARN', 'TIMESTAMP_TZ', f'{table.name}.{column.name}：请确认时区语义。'))
            if level in {'production', 'critical'} and re.search(r'\b(JSON|JSONB)\b', column.sql, re.I):
                diagnostics.append(Diagnostic('WARN', 'JSON_BOUNDARY', f'{table.name}.{column.name}：请确认 JSON 结构、校验、大小和查询边界。'))

    seen_index_defs: dict[tuple[str, tuple[str, ...]], str] = {}
    table_indexes: dict[str, list[Index]] = {}
    for index in indexes:
        table_indexes.setdefault(index.table, []).append(index)
        table_indexes.setdefault(short_name(index.table), []).append(index)
        definition = (index.table, index.columns)
        if definition in seen_index_defs:
            diagnostics.append(Diagnostic('WARN', 'DUP_INDEX', f'{index.name}：与 {seen_index_defs[definition]} 的字段顺序重复。'))
        else:
            seen_index_defs[definition] = index.name
        table = table_map.get(index.table) or table_map.get(short_name(index.table))
        if table:
            constraint_sets = extract_constraint_column_sets(table, r'PRIMARY\s+KEY') + extract_constraint_column_sets(table, 'UNIQUE')
            if index.columns in constraint_sets:
                diagnostics.append(Diagnostic('WARN', 'CONSTRAINT_INDEX', f'{index.name}：重复创建了主键或唯一约束已经提供的索引。'))
        if not nearby_index_reason(sql, index.start):
            diagnostics.append(Diagnostic('WARN', 'INDEX_REASON', f'{index.name}：请在附近增加“-- 支持：具体查询”说明。'))

    for table in tables:
        foreign_sets = extract_constraint_column_sets(table, r'FOREIGN\s+KEY')
        for column in table.columns:
            if re.search(r'\bREFERENCES\b', column.sql, re.I):
                foreign_sets.append((column.name,))
        candidates = table_indexes.get(table.name, []) + table_indexes.get(short_name(table.name), [])
        constraint_sets = extract_constraint_column_sets(table, r'PRIMARY\s+KEY') + extract_constraint_column_sets(table, 'UNIQUE')
        for fk_columns in foreign_sets:
            covered = any(keys[:len(fk_columns)] == fk_columns for keys in constraint_sets)
            covered = covered or any(index.columns[:len(fk_columns)] == fk_columns for index in candidates)
            if not covered:
                diagnostics.append(Diagnostic('WARN', 'FK_INDEX', f'{table.name}{fk_columns}：外键没有明显的前导列索引，请结合查询负载和父记录变更行为审查。'))

    if re.search(r"(?i)(password|secret|api[_ -]?key|bearer[_ -]?token)\s*[:=]\s*['\"]?\S+", sql):
        diagnostics.append(Diagnostic('ERROR', 'SECRET_TEXT', 'DDL 中疑似包含凭据值。'))

    return diagnostics


def print_diagnostics(diagnostics: Iterable[Diagnostic]) -> tuple[int, int]:
    errors = warnings = 0
    severity_labels = {'ERROR': '错误', 'WARN': '警告'}
    for item in diagnostics:
        if item.severity == 'ERROR':
            errors += 1
        elif item.severity == 'WARN':
            warnings += 1
        print(f'{severity_labels.get(item.severity, item.severity)} [{item.code}] {item.message}')
    print(f'汇总：{errors} 个错误，{warnings} 个警告')
    return errors, warnings


def run_self_test() -> int:
    good_postgres = """
CREATE TABLE app_user (
  id BIGINT PRIMARY KEY NOT NULL,
  email TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_app_user_email UNIQUE (email)
);
COMMENT ON TABLE app_user IS '已注册的应用账号。';
COMMENT ON COLUMN app_user.id IS '账号内部标识。';
COMMENT ON COLUMN app_user.email IS '标准化后的登录邮箱。';
COMMENT ON COLUMN app_user.created_at IS '账号创建时间点。';
-- 支持：按创建时间倒序查询账号。
CREATE INDEX idx_app_user_created_at ON app_user (created_at DESC);
"""
    bad_postgres = """
CREATE TABLE payment (
  amount FLOAT,
  data JSONB
);
"""
    good_mysql = """
CREATE TABLE app_user (
  id BIGINT NOT NULL COMMENT '账号内部标识。',
  email VARCHAR(320) NOT NULL COMMENT '标准化后的登录邮箱。',
  PRIMARY KEY (id),
  CONSTRAINT uq_app_user_email UNIQUE (email)
) COMMENT='已注册的应用账号。';
"""
    good_sqlite = """
-- 表 app_user：已注册的应用账号。
CREATE TABLE app_user (
  -- 账号内部标识。
  id INTEGER PRIMARY KEY NOT NULL,
  -- 标准化后的登录邮箱。
  email TEXT NOT NULL UNIQUE
);
"""
    cases = [
        ('正确的 PostgreSQL', good_postgres, 'postgresql', True),
        ('错误的 PostgreSQL', bad_postgres, 'postgresql', False),
        ('正确的 MySQL', good_mysql, 'mysql', True),
        ('正确的 SQLite', good_sqlite, 'sqlite', True),
    ]
    failed = 0
    for name, sql, dialect, should_pass in cases:
        diagnostics = validate_text(sql, dialect, 'production')
        passed = not any(item.severity == 'ERROR' for item in diagnostics)
        if passed != should_pass:
            failed += 1
            print(f'自测失败：{name}')
            print_diagnostics(diagnostics)
        else:
            print(f'自测通过：{name}')
    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    parser = ChineseArgumentParser(description=__doc__)
    parser.add_argument('sql_file', nargs='?', type=Path, help='需要检查的 DDL 文件')
    parser.add_argument('--dialect', choices=('auto', 'postgresql', 'mysql', 'sqlite'), default='auto')
    parser.add_argument('--level', choices=('demo', 'prototype', 'production', 'critical'), default='production')
    parser.add_argument('--catalog', type=Path, help='可选的 JSON 数据字典，用于补充说明')
    parser.add_argument('--strict-warnings', action='store_true', help='存在警告时也返回失败')
    parser.add_argument('--self-test', action='store_true', help='运行内置回归测试')
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.self_test:
        return run_self_test()
    if args.sql_file is None:
        print('错误：除非使用 --self-test，否则必须提供 sql_file', file=sys.stderr)
        return 2
    try:
        sql = args.sql_file.read_text(encoding='utf-8')
        catalog = load_catalog(args.catalog)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f'错误：{exc}', file=sys.stderr)
        return 2
    diagnostics = validate_text(sql, args.dialect, args.level, catalog)
    errors, warnings = print_diagnostics(diagnostics)
    return 1 if errors or (warnings and args.strict_warnings) else 0


if __name__ == '__main__':
    raise SystemExit(main())
