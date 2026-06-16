# 业务记忆维护

每生成完一份新需求，都要判断是否存在后续可复用的业务规则。只要存在，就沉淀一条简短记忆，并同步到 skill references。不要把整份 PRD 原文塞进记忆。

## 标准命令

从本次 run 目录生成需求记忆并同步 skill：

```bash
python3 scripts/requirement_memory_tools.py create-from-run \
  --run-dir "/path/to/run" \
  --memory-dir "/path/to/testcase-agent-kit/memory" \
  --skill-dir "/path/to/testcase-agent-kit/skills/caseforge-prd-testcases" \
  --requirement-name "需求名称" \
  --source-file "需求文档.docx" \
  --date "2026-06-05"
```

只同步已有项目记忆到 skill：

```bash
python3 scripts/requirement_memory_tools.py sync-skill \
  --memory-dir "/path/to/testcase-agent-kit/memory" \
  --skill-dir "/path/to/testcase-agent-kit/skills/caseforge-prd-testcases"
```

脚本会做三件事：

1. 在 `memory/entries/` 下创建或更新当前需求记忆条目。
2. 在 `memory/requirements-index.md` 中登记需求、关键词和记忆条目路径。
3. 将 `memory/entries/*.md`、`product-business-memory.md`、`requirements-index.md` 和历史 PRD 归档同步到 skill 的 `references/`。

## 记忆条目模板

```markdown
# 需求记忆：<需求名称>

## 来源

需求文档：`<文件名>`

## 核心业务目标

<一句话说明这条需求解决什么问题>

## 关键业务规则

1. <稳定规则>
2. <稳定规则>

## 测试风险沉淀

1. <容易漏测的点>
2. <容易漏测的点>
```

## 总表维护规则

1. 只把跨需求稳定成立的规则写入 `business-memory.md`。
2. 一次性页面文案、临时原型细节、未确认猜测不要写入总表。
3. 新 PRD 改写旧规则时，更新旧规则并记录冲突来源。
4. 每个需求在 `requirement-memory-index.md` 记录关键词，便于后续召回。
5. 记忆越短越好，但必须包含后续生成用例时能直接降低漏测率的信息。

## 必须同步到 skill 的文件

1. `references/business-memory.md`
2. `references/requirement-memory-index.md`
3. `references/requirement-memory-entries.md`
4. `references/historical-prd-source-digests.md`
5. `references/historical-prd-source-index.csv`
6. `references/historical-prd-module-knowledge-map.md`

## 适合沉淀的内容

1. 权限差异和角色行为。
2. 状态流转规则。
3. 字段映射和默认值。
4. 特殊失败处理。
5. 导出格式和兼容规则。
6. 上下游依赖。
7. 历史需求对新需求的影响。

## 不适合沉淀的内容

1. 一次性 PRD 原文。
2. 尚未确认的推测。
3. API Key、Token、账号密码。
4. 临时调试日志。
5. 只对单次生成有意义的过程分析。
