# DingTalk Knowledge Organize Skill

`dingtalk-knowledge-organize` 用于用 CSV 审批流整理钉钉知识库文件，包括盘点、分类、重命名、移动、去重候选和归档建议。

## 适用场景

- 盘点一个钉钉知识库或文档空间。
- 根据路径、文件名、类型和元数据生成整理建议。
- 让管理员通过 CSV 审批每一项动作。
- 只深读不确定文件，而不是默认读取全部内容。
- 执行已审批的移动、重命名和归档操作。

## 核心流程

1. 快速扫描所有文件，不读取正文。
2. 生成初始 remediation CSV。
3. 由管理员审阅 CSV。
4. 结合管理员反馈，仅深读不确定文件。
5. 对已批准的 CSV 执行变更并输出报告。

## 常用命令

扫描知识库：

```bash
python3 /Users/derek/.agents/skills/dingtalk-knowledge-organize/scripts/scan_dingtalk_workspace_inventory.py \
  --workspace-name "Global BD/国际业务部"
```

生成 remediation CSV：

```bash
python3 /Users/derek/.agents/skills/dingtalk-knowledge-organize/scripts/build_remediation_csv.py \
  --inventory-json "/path/to/inventory.json"
```

带历史 CSV 重新生成：

```bash
python3 /Users/derek/.agents/skills/dingtalk-knowledge-organize/scripts/build_remediation_csv.py \
  --inventory-json "/path/to/inventory.json" \
  --existing-csv "/path/to/prior.csv"
```

执行前先 dry run：

```bash
python3 /Users/derek/.agents/skills/dingtalk-knowledge-organize/scripts/execute_remediation_csv_dws.py \
  --inventory-json "/path/to/inventory.json" \
  --csv-path "/path/to/remediation.csv" \
  --dry-run
```

管理员确认后执行：

```bash
python3 /Users/derek/.agents/skills/dingtalk-knowledge-organize/scripts/execute_remediation_csv_dws.py \
  --inventory-json "/path/to/inventory.json" \
  --csv-path "/path/to/remediation.csv" \
  --execute
```

## CSV 合同

CSV header 必须保持：

```text
workspace_name,file_path,size_mb,file_type,source_url,modified_time,proposed_category,name_based_confidence,needs_content_review,review_reason,content_summary,duplicate_group,proposed_action,rename_to,move_to,admin_decision,notes
```

`admin_decision` 是执行阶段的事实源。为空的行必须跳过。

## 执行边界

- 未经管理员确认，不移动、不重命名、不删除。
- 归档候选移入 `待归档`，不直接删除。
- 执行 DingTalk 操作优先使用 `dws doc`，并加 `--format json`。
- 不确定命令语法时先跑 `--help`。

## 目录结构

```text
dingtalk-knowledge-organize/
├── SKILL.md
└── scripts/
    ├── build_remediation_csv.py
    ├── deep_review_uncertain_rows.py
    ├── downgrade_cross_format_duplicates.py
    ├── execute_remediation_csv_dws.py
    ├── resolve_aggressive_duplicate_candidates.py
    ├── resolve_obvious_duplicate_candidates.py
    └── scan_dingtalk_workspace_inventory.py
```
