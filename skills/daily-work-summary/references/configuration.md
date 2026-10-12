# 配置与运行

## 环境

macOS 或 Linux，Python 3.9+、Git；钉钉需要已安装并登录的 `dws`。核心代码和测试只用 Python 标准库，PDF 可选已有 `pdftotext`。缺工具时报告缺口，不自动安装。无需模型 API 密钥，业务整理由运行 Skill 的 Agent 完成。

先运行 `init`，再按已确认范围编辑私有配置。[config.example.json](../config.example.json) 只有虚构示例，不代表任何人的授权。

| 字段 | 含义 |
| --- | --- |
| `company.name` | 明确公司名，用于钉钉组织校验 |
| `timezone` | IANA 时区，默认 Asia/Shanghai |
| `identity.git_emails` | 本人 Git 邮箱，可多个，不填全团队邮箱 |
| `git.repositories` | 仓库 `name`、绝对 `path` |
| `git.max_commits` | 每仓库历史扫描上限，默认 2000，不是当日提交上限 |
| `git.include_worktree` | 检查授权工作树的未提交改动 |
| `local.roots` | 目录 `path`、`project`、`mode`、`keywords` |
| `local.roots[].mode` | workspace：公司专属目录；mixed：桌面/下载等混合目录 |
| `local.roots[].keywords` | mixed 必填，先按相对路径匹配再读正文 |
| `local.include_globs` / `exclude_globs` | 相对路径筛选，内置敏感路径排除不能关闭 |
| `local.max_files` / `max_file_bytes` | 文件扫描/读取上限，触发则报告缺口 |
| `dingtalk.enabled` | 是否启用，关闭不等于云端已核查 |
| `dingtalk.profile` | 留空则按公司匹配唯一组织默认账号，多候选须指定 |
| `dingtalk.queries` / `nodes` | 项目关键词、已知文档真实节点或 URL |
| `dingtalk.max_pages` / `max_documents` / `page_size` | 分页与正文上限，页大小不超过 30 |
| `limits.timeout_seconds` / `max_content_chars` | 单命令超时、正文长度上限 |

拒绝未知配置字段，防止拼写错误静默改变范围。可选 local.max_depth 最高 32；max_docx_uncompressed_bytes 最高 16777216。

根目录和整个家目录不能作为范围。额外 worktree 须位于明确授权目录内；不通过符号链接扩大本地文件范围。

## 常用命令

```bash
python3 scripts/daily_summary.py doctor --config ~/.config/daily-work-summary/config.json
python3 scripts/daily_summary.py collect --config ~/.config/daily-work-summary/config.json --start 2026-09-21 --end 2026-09-28
python3 scripts/daily_summary.py collect --config ~/.config/daily-work-summary/config.json --offline
```

doctor 只检查本地配置与工具，不确认钉钉权限。offline 会明确记录云端未检查。裸日期两端均含当日；ISO 时间终点不含；结束时间自动截至现在。

## 输出与退出码

默认输出到用户目录 `.local/state/daily-work-summary/runs/`，也可指定新的 `--output-dir`。不得写入任何 Git 工作树或采集目录，不覆盖历史产物。

- evidence.json：正文、时间线索、证据编号、覆盖缺口。
- draft.md：待核对索引，不是已确认的成果日报。
- manifest.json：采集状态与位置，记录数不代表工作量。
- findings.json、report.md：Agent 整理并校验后生成，见 [报告协议](report-contract.md)。

输出目录 0700、文件 0600。退出码 0：命令完成，collect 表示三来源均处理完配置范围；2：存在缺口但保留可用产物；1：参数或结构等致命错误。不得隐藏缺口来取得 0。

不安装定时任务、不自动同步或清理报告。历史保留和删除由用户决定。
