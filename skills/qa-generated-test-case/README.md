# QA Generated Test Case

这个 skill 用于把 PRD 转成可执行的中文 QA 测试用例，并生成固定 7 列的 Markdown/CSV/XLSX 输出。它只保存可复用 workflow、规则、脚本和轻量测试，不随 skill 安装历史 PRD、客户资料、运行产物或大体量业务记忆。

## 安装结构

本 skill 的 root 是：

```text
skills/qa-generated-test-case/
├── SKILL.md
├── README.md
├── agents/
├── references/
├── scripts/
└── tests/
```

仓库安装脚本按 `skills/*` 同步，因此 `SKILL.md` 必须直接位于 `skills/qa-generated-test-case/SKILL.md`。

## 数据边界

可提交：

1. `SKILL.md`、README、workflow、输出格式、评分规则、PR 模板等轻量规则。
2. `scripts/extract_prd.py`、`scripts/testcase_table_tools.py`、`scripts/prd_memory_retrieval.py` 等可复用脚本。
3. 单测和合成 fixture。

不可提交：

1. `runs/`、生成的 CSV/XLSX、提取后的 PRD 文本、一次性测试设计草稿。
2. 历史 PRD 原文、完整 digest/index、大体量业务归档、客户/项目私有资料。
3. token、cookie、浏览器状态、本地配置。

历史材料如确实需要，应放在 memory/document store、私有数据目录或单独数据包里，并通过检索脚本返回 top N 片段后再给 skill 使用。

## 外部检索设计

索引字段包括：

| 字段 | 说明 |
| --- | --- |
| `product_line` | 产品线，例如 Rosetta、MorningStar、Phoenix |
| `module` | 模块或二级路径，例如 任务列表、标注工具 |
| `requirement_title` | 需求标题 |
| `version` | 版本或阶段，例如 v3.1、一期、二期 |
| `date` | 日期，建议 ISO 格式 |
| `page_or_api` | 页面、入口或接口 |
| `role` | 角色 |
| `tags` | 关键词标签，分号分隔 |
| `source_path` | 私有数据包内的相对来源路径 |
| `section` | 片段所在章节 |
| `content` | 可召回的短片段，不是完整历史归档 |

检索顺序：

1. 先按确定字段过滤，例如产品线、模块、版本、页面/接口、角色、标签。
2. 再对过滤后的候选片段按关键词相似度排序。
3. 只返回 `--top-n` 条，默认 5 条。
4. skill 运行时只读取检索结果文件，不读取完整历史归档。

## 最小可运行命令

抽取 PRD：

```bash
python3 scripts/extract_prd.py "/path/to/需求.docx" --out "/tmp/qa-testcase-run/00-extracted-prd.txt"
```

构建外部索引：

```bash
python3 scripts/prd_memory_retrieval.py build-index \
  --source-dir "/path/to/private-prd-memory" \
  --out-index "/path/to/private-prd-memory/index.jsonl" \
  --out-csv "/path/to/private-prd-memory/index.csv"
```

检索 top N：

```bash
python3 scripts/prd_memory_retrieval.py search-memory \
  --index "/path/to/private-prd-memory/index.jsonl" \
  --module "任务列表" \
  --tags "筛选,导出" \
  --query "跨页选中 导出筛选结果" \
  --top-n 5 \
  --out "/tmp/qa-testcase-run/retrieved-memory.md"
```

生成 CSV/XLSX：

```bash
python3 scripts/testcase_table_tools.py from-markdown \
  --markdown "/tmp/qa-testcase-run/03-testcases.md" \
  --csv "/tmp/qa-testcase-run/04-testcases-excel.csv" \
  --xlsx "/tmp/qa-testcase-run/05-testcases.xlsx" \
  --module "/需求名称"
```

## 验证

```bash
python3 -m unittest discover -s skills/qa-generated-test-case/tests
python3 scripts/prd_memory_retrieval.py validate-retrieval --index "/path/to/private-prd-memory/index.jsonl"
```

PR 说明可参考 `references/pr-description-template.md`。
