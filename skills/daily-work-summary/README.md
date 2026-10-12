# 公司每日工作总结 Skill

综合公司 Git 仓库、钉钉文档正文和授权本地文件，生成能追溯来源的工作总结。它不是按提交数拼日报：**脚本采集证据，Agent 核对贡献、时间与成果后整理报告。**

适合每日总结、跨项目工作回顾和指定日期区间核对。不自动填工时、改 OKR 或发送消息。

## 已实现

| 能力 | 实现与边界 |
| --- | --- |
| 多仓库 Git | 本地引用、作者/共同作者/提交者、实际差异、授权工作树、去重；不自动拉取远端 |
| 钉钉 | 公司组织校验、固定账号、搜索分页、在线文档正文、原生 Markdown、受限普通附件下载 |
| 本地材料 | 明确目录范围、混合目录关键词过滤、文本/DOCX、可选 PDF 提取、内容去重 |
| 证据核对 | 区分历史与本期、代码与验证、本人开发与协助合并；证据编号及引用检查 |
| 报告输出 | Markdown 表格、风险与下一步、来源覆盖和缺口；未整理前仅输出待核对索引 |
| 安全边界 | 业务只读、凭证过滤、参数数组子进程、符号链接限制、超时与上限、仓库外私有输出 |

电子表格、多维表、截图、扫描 PDF 等不能自动提取正文时会显示缺口，由 Agent 使用已授权的对应工具补核。详见 [钉钉边界](references/dingtalk.md) 和 [证据规则](references/evidence-policy.md)，不声称支持所有格式或全组织普查。

## 安装

需要 macOS/Linux、Python 3.9+、Git；钉钉采集另外需要已登录的 dws。无第三方 Python 依赖，无模型密钥配置。

在公司仓库根目录执行 `./install.sh`，会与其他 Skill 一起安装到 `~/.agents/skills/`。仅安装本 Skill 时，可在本目录执行：

```bash
python3 scripts/install_skill.py
```

默认安装到 `~/.agents/skills/daily-work-summary`；Codex 专属目录可用 `--dest ~/.codex/skills`。已有安装不会被覆盖。安装只复制规则、程序和测试，不复制个人配置或运行结果。

## 初次配置

在安装后的 Skill 目录或本仓库目录执行：

```bash
python3 scripts/daily_summary.py init --config ~/.config/daily-work-summary/config.json --company "你的公司完整名称"
```

按 [配置文档](references/configuration.md) 填写本人 Git 邮箱、公司仓库、本地授权目录、钉钉项目关键词；[示例配置](config.example.json) 只含虚构占位范围。首次需要明确范围，后续复用本机配置。

```bash
python3 scripts/daily_summary.py doctor --config ~/.config/daily-work-summary/config.json
python3 scripts/daily_summary.py collect --config ~/.config/daily-work-summary/config.json
```

运行结果默认保存在仓库外的 `~/.local/state/daily-work-summary/runs/`，终端会给出准确路径。退出码 2 表示有缺口但保留已取得证据，不是全部失败。

## 日常使用

安装后向 Agent 提出：

> 使用 daily-work-summary，按已经配置的公司范围总结今天工作，核对 Git、钉钉文档和本地材料，输出表格，明确证据和遗漏。

也可以指定区间：

```bash
python3 scripts/daily_summary.py collect --config ~/.config/daily-work-summary/config.json --start 2026-09-21 --end 2026-09-28
```

Agent 按 [SKILL.md](SKILL.md) 阅读证据并生成 findings.json，再执行 check/render。单独运行 collect 只会得到证据索引，**不会自动把候选记录写成已完成成果**。完整协议见 [报告协议](references/report-contract.md)。

## 验证

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_release.py
```

测试使用临时 Git 仓库、合成文件和脱敏模拟 CLI 返回，不读取使用者的公司数据。钉钉在线文档通路曾在 dws v1.0.58 上进行真实只读冒烟；其他版本、其他组织权限及附件通路需按实际环境核查。CI 不使用公司凭证、不采集真实资料。

## 公司规范对齐

按本仓库的设计原则组织：事实源优先、单一业务边界、额外写操作另行授权、不存敏感状态、输出可审计。实际运行产生的配置、报告、日志和工作材料只保存在使用者本机，不提交到仓库。
