# 历史材料检索设计

## 索引字段

每条检索记录至少包含：

| 字段 | 用途 |
| --- | --- |
| `id` | 稳定片段 ID |
| `product_line` | 产品线过滤 |
| `module` | 模块过滤 |
| `requirement_title` | 需求标题过滤和展示 |
| `version` | 版本/阶段过滤 |
| `date` | 日期过滤和排序参考 |
| `page_or_api` | 页面或接口过滤 |
| `role` | 角色过滤 |
| `tags` | 标签过滤 |
| `source_path` | 来源定位，不应指向仓库内历史原文 |
| `section` | 章节定位 |
| `content` | 可读取短片段 |

## 检索规则

1. 先按确定字段过滤：`product_line`、`module`、`requirement_title`、`version`、`date`、`page_or_api`、`role`、`tags`。
2. 对过滤后的候选记录按关键词相似度排序。
3. 只返回 `--top-n` 条，默认 5 条。
4. 返回内容应是短片段，不是完整 PRD 原文。
5. 当前 PRD 与检索结果冲突时，以当前 PRD 为准，并列入 `待确认问题`。

## 脚本入口

```bash
python3 scripts/prd_memory_retrieval.py build-index --source-dir /private/prds --out-index /private/index.jsonl
python3 scripts/prd_memory_retrieval.py search-memory --index /private/index.jsonl --module 任务列表 --query "跨页选中"
python3 scripts/prd_memory_retrieval.py validate-retrieval --index /private/index.jsonl
```

## 更新方式

1. 私有资料更新后重新运行 `build-index`。
2. 索引文件保存在私有目录或数据包，不提交到此仓库。
3. PR 中只说明索引字段、查询规则和验证命令，不附带真实历史材料。
