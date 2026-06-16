---
name: caseforge-prd-testcases
description: Generate high-coverage Chinese functional and business-flow test cases from Web admin PRDs, especially Word .docx PRDs. Use when Codex is asked to write, review, regenerate, export, or improve PRD-based test cases; convert PRDs into standardized 7-column Excel-ready cases; use accumulated product business memory; persist the current requirement into reusable memory; sync project memories into the skill; identify missing confirmations; or package outputs as Markdown, CSV, and XLSX for test teams.
---

# CaseForge PRD Testcases

## Core Rule

Act as a senior test analyst for Web 管理后台需求. Generate usable functional and business-flow test cases from PRD content, not generic QA checklists.

Always prioritize:

1. 功能点覆盖
2. 主流程、分支流程、状态流转
3. 异常场景
4. 边界值和多条件组合
5. 角色权限
6. 上下游依赖和历史业务记忆

Current PRD always overrides historical memory. When they conflict, state the conflict and ask it as a 待确认问题 instead of inventing rules.

## Quick Workflow

1. Extract PRD text.
   Use `scripts/extract_prd.py <prd.docx> --out <run_dir>/00-extracted-prd.txt` for Word files.
2. Load business memory.
   Read `references/business-memory.md` first. If the PRD touches a known area, also read `references/requirement-memory-index.md`; for platform-wide history or unfamiliar modules, read `references/historical-prd-archive-map.md`.
3. Produce process artifacts.
   Create these files in a new non-overwriting run directory:
   `01-normalized-prd.md`, `02-test-design.md`, `03-testcases.md`, `04-testcases-excel.csv`, `05-testcases.xlsx`.
4. Follow the workflow prompt structure.
   See `references/workflow.md` for the required analysis stages and prompts.
5. Enforce the fixed final output format.
   See `references/output-format.md`. The official final table has exactly 7 columns.
6. Validate and export.
   Use `scripts/testcase_table_tools.py` to parse, validate, create CSV, and create XLSX.
7. Persist requirement memory.
   After generating and validating test cases, create or update the requirement memory entry and sync project memory into the skill. Use `scripts/requirement_memory_tools.py`; see `references/memory-maintenance.md`.

## Final Output Contract

The final testcase table must have this exact header and order:

`用例名称 | 所属模块 | 前置条件 | 步骤描述 | 预期结果 | 用例等级 | 编辑模式`

Hard constraints:

1. `所属模块` is fixed for all rows as `/<需求名称>`.
2. `编辑模式` is always `STEP`.
3. `用例等级` is `P0`, `P1`, `P2`, or `P3`.
4. `步骤描述` uses numbered steps like `[1]...；[2]...`.
5. `预期结果` uses the same step numbers as `步骤描述`; do not add more expected-result step numbers than action step numbers.
6. Do not include literal `\n`, `<br>`, or `<br/>` inside case text.
7. Keep case names unique and concrete. Avoid vague names like `创建成功`.
8. Put uncertain or missing PRD information under `待确认问题`, not into formal cases.

## Script Usage

Extract a Word PRD:

```bash
python3 scripts/extract_prd.py "/path/to/需求.docx" --out "/path/to/run/00-extracted-prd.txt"
```

Parse Markdown table, validate, and generate CSV/XLSX:

```bash
python3 scripts/testcase_table_tools.py from-markdown \
  --markdown "/path/to/run/03-testcases.md" \
  --csv "/path/to/run/04-testcases-excel.csv" \
  --xlsx "/path/to/run/05-testcases.xlsx" \
  --module "/需求名称"
```

Validate an existing CSV:

```bash
python3 scripts/testcase_table_tools.py validate-csv \
  --csv "/path/to/run/04-testcases-excel.csv" \
  --module "/需求名称"
```

If a script reports a format error, fix the source Markdown/CSV and rerun validation before reporting completion.

Create a memory entry from the current run and sync it into the skill:

```bash
python3 scripts/requirement_memory_tools.py create-from-run \
  --run-dir "/path/to/run" \
  --memory-dir "/path/to/testcase-agent-kit/memory" \
  --skill-dir "/path/to/testcase-agent-kit/skills/caseforge-prd-testcases" \
  --requirement-name "需求名称" \
  --source-file "需求文档.docx" \
  --date "2026-06-05"
```

Sync existing project memories into the skill references:

```bash
python3 scripts/requirement_memory_tools.py sync-skill \
  --memory-dir "/path/to/testcase-agent-kit/memory" \
  --skill-dir "/path/to/testcase-agent-kit/skills/caseforge-prd-testcases"
```

## Process Artifact Expectations

`01-normalized-prd.md` should include:

1. 背景与目标
2. 角色与对象
3. 功能范围
4. 业务规则和字段映射
5. 测试假设与待确认

`02-test-design.md` should include:

1. 测试目标
2. 覆盖分层
3. 关键业务规则转测试规则
4. 高风险点
5. 测试数据建议
6. 待确认问题
7. 覆盖说明

`03-testcases.md` should include:

1. Final 7-column Markdown testcase table
2. 待确认问题
3. 覆盖说明

`04-testcases-excel.csv` and `05-testcases.xlsx` must be generated from the same final table.

## Quality Gate

Before final response, verify:

1. The PRD was actually read or extracted.
2. Business memory was considered where relevant.
3. Main flow, branches, exceptions, boundaries, permissions, and dependencies are represented.
4. Final table validates with `errors=none`.
5. XLSX opens structurally, or at least passes zip integrity validation.
6. The current requirement is persisted as a memory entry, unless it truly contains no reusable business rule.
7. Skill references are synced after memory changes when working inside the CaseForge project.

Use `references/quality-scorecard.md` when the user asks for scoring, benchmarking, or improvement over manual writing efficiency.

## Historical PRD Archive

For Rosetta/MorningStar/Phoenix platform tasks, prefer historical context before generating cases:

1. Read `references/historical-prd-archive-map.md` for the module map and global historical rules.
2. Read `references/historical-prd-evolution-groups.md` when the requirement mentions 一期、二期、三期、V3.x, 后续修改, 废弃, 待讨论, or 未实现.
3. Search `references/historical-prd-source-digests.md` with keywords from the current PRD to find exact historical rules by file.
4. Use `references/historical-prd-source-index.csv` when you need a structured list of all historical PRD files, modules, tags, and key-rule snippets.
5. If the local project has `memory/historical-prd-archive/source-file-digests.md`, prefer it as the latest local archive because it may include newer files than the packaged skill.
