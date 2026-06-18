# PR 说明模板

## 背景/目标

- 这个 skill 解决什么问题：
- 目标用户：

## 变更范围

- 新增/修改的 skill：
- 新增/修改的脚本：
- 新增/修改的 references：
- 新增/修改的 tests：

## 安装结构

- skill root：`skills/qa-generated-test-case/SKILL.md`
- 是否符合 `skills/*/SKILL.md` 约定：

## 数据边界

- 可提交的 workflow/templates/scripts/tests：
- 不提交的历史 PRD、运行产物、客户/项目私有数据：
- 私有数据存放或 memory/document store 边界：

## 检索设计

- 索引字段：
- 字段过滤规则：
- 关键词或语义召回方式：
- top N 约束：
- 验证方法：

## 使用方式

```bash
python3 scripts/prd_memory_retrieval.py search-memory --index /path/to/index.jsonl --query "关键词" --top-n 5
python3 scripts/testcase_table_tools.py validate-markdown --markdown /tmp/qa-testcase-run/03-testcases.md --module "/需求名称"
```

## 验证结果

- 运行命令：
- 结果：

## 风险/待确认

- Derek 或业务方需要确认的材料边界：
- 敏感信息边界：
- 未解决问题：
