# Build Work Memory Skill

`build-work-memory` 用于首次把 Derek 的既有工作上下文导入 Friday Memory。它覆盖本地文件、钉钉文档/知识库、钉钉 AI 听记，以及用户明确选择的其他钉钉数据。

## 适用场景

- 初始化 Friday Memory 的工作上下文。
- 从本地文档、会议纪要或钉钉知识库导入资料。
- 为后续日常工作召回、项目背景补全或组织知识沉淀做准备。

不要默认扫描全部资料。只有用户明确给出范围并确认后，才读取私有内容并上传到 Memory。

## 前置条件

- Friday Memory MCP 可用，并暴露 `document_upload`。
- `dws` 已安装并已登录钉钉工作区。
- 本地文件只在用户明确选择本地导入时读取。

如果 MCP 或 `dws` 不可用，先让用户完成授权或安装，不要编造安装命令、token 或下载地址。

## 工作流程

1. 说明四步导入流程：本地文档、钉钉知识库/文档、钉钉 AI 听记、其他钉钉数据。
2. 逐项收集用户想导入的范围。
3. 汇总计划读取和上传的范围。
4. 等用户明确确认后再读取内容。
5. 将每个来源转换为带 provenance 的 Markdown。
6. 通过 Friday Memory MCP `document_upload` 提交，`ingest_mode=graph`，`wait_for_processing=false`。
7. 汇总成功、失败和后台处理中数量。

## 来源格式

每份导入材料都应包含来源信息：

```md
# <title>

source_type: <local_file | dingtalk_doc | dingtalk_wiki | dingtalk_minutes | other>
source_id: <id if available>
source_url: <url if available>
source_path: <path if available>
source_time: <original time if available>
participants: <participants if available>
imported_from: <local | dws doc | dws wiki | dws minutes | ...>

---

<content>
```

长资料按标题、章节、议程、说话人时间段、日期或表格视图拆分，每个拆分块都保留 provenance。

## 安全边界

- 不读取用户没有确认的范围。
- 不暴露 `graph_id`、`user_id`、内部队列或抽取实现细节。
- 不上传 token、cookie、密钥、临时签名 URL 或未授权私有内容。
- 上传成功只表示“已提交后台处理”，不表示图谱抽取已完成。

## 目录结构

```text
build-work-memory/
└── SKILL.md
```
