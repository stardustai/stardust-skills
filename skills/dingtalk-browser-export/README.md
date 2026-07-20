# DingTalk Browser Export Skill

`dingtalk-browser-export` 用于从已登录 Chrome 中导出当前打开的钉钉/Alidocs 文档，避免浏览器保存弹窗阻塞自动化。

## 适用场景

- 用户要求导出、下载、保存或备份当前钉钉文档。
- 需要得到和钉钉网页 UI 一致的 Word、PDF 或 Markdown 导出结果。
- Chrome 已经登录并打开目标文档。

该 skill 不用于编辑文档内容，也不替代 OpenAPI 文档读写能力。

## 前置条件

- OpenClaw Chrome 扩展已安装并连接。
- 本机可用 `openclaw` CLI。
- Chrome 当前活动页是目标钉钉/Alidocs 文档。
- relay profile 可能不是 `chrome`，需要按实际 profile 处理。

## 使用方式

默认导出 `.docx` 到 `/Users/derek/output/doc`：

```bash
python3 /Users/derek/.agents/skills/dingtalk-browser-export/scripts/export_current_dingtalk.py
```

指定 browser profile：

```bash
python3 /Users/derek/.agents/skills/dingtalk-browser-export/scripts/export_current_dingtalk.py --browser-profile chrome-relay
```

指定格式：

```bash
python3 /Users/derek/.agents/skills/dingtalk-browser-export/scripts/export_current_dingtalk.py --format pdf
python3 /Users/derek/.agents/skills/dingtalk-browser-export/scripts/export_current_dingtalk.py --format md
```

支持格式：

- `docx`
- `pdf`
- `md`

## 输出要求

完成后向用户报告：

- 文档标题
- 导出格式
- 保存路径

失败时说明卡在哪一步：找活动标签页、打开导出菜单、等待导出任务结果，还是下载生成文件。

## 目录结构

```text
dingtalk-browser-export/
├── SKILL.md
└── scripts/
    └── export_current_dingtalk.py
```
