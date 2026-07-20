# Stardust Skills

星尘公用 Agent Skills 仓库，用来沉淀公司内部可复用的 Agent 工作流、判断标准、输出格式和工具调用边界。

这个项目不是钉钉官方 SDK，也不是 `dws`、小青 MCP 或任何业务系统的替代品。它的定位是让 Agent 在星尘的真实业务里按统一规则工作：先读事实源，再按业务判断标准分析，最后在用户确认后执行高影响操作。

当前仓库覆盖 Friday Memory 初始化、钉钉、叮当 OKR、DingTalk/Alidocs、OA 审批、知识库整理、AI 听记权限、纷享销客 CRM、PRD 测试用例生成、需求规格访谈、Vibe Coding 工程交付、候选人面试、高级技术候选人产品经历评估、小青面试系统、SRE 部署交付和等保代码安全审计。具体原子操作仍交给对应工具完成：Memory 导入优先走已安装的 Friday Memory MCP，钉钉能力优先走 `dws`，纷享销客数据优先走官方 `sharecrm` CLI，候选人和面评业务事实优先走 `xiaoqing_interview` MCP，浏览器只作为明确授权后的兜底路径；`vibe-coding` 以 `spec-intake` 的工程就绪 Spec 为输入，自动编排项目初始化、架构治理、计划、TDD、业务 E2E/Eval、Review 和 Git 交付；部署类 skill 主要生成可审计的部署包、发布门禁和变更材料，不替代正式生产变更审批；安全审计类 skill 主要读取本地项目源码、配置、部署文件和项目文档，不替代正式等保测评。

## 包含的 Skills

| Skill | 作用 |
| --- | --- |
| `build-work-memory` | 引导用户首次初始化 Friday Memory：按用户确认的范围读取本地文档、钉钉知识库 / 文档、钉钉 AI 听记和其他指定钉钉数据，标准化来源信息后提交到 Memory 后台处理。 |
| `dengbao-code-audit` | 从等保三级 / MLPS 2.0 视角检查源码、配置、部署文件和项目文档，覆盖登录认证、权限控制、安全审计、数据安全、接口安全、传输安全、运维暴露面、备份恢复、发布变更和文档材料，并输出 Markdown 风险报告和整改路线图。 |
| `dingtang-okr-review` | 从叮当 OKR 页面导出 OKR Excel，并按 CEO 视角在 KR 层级做证据核实、打分和超时折扣。 |
| `dingtalk-browser-export` | 从已登录 Chrome 当前打开的 DingTalk/Alidocs 文档导出为 docx、PDF 或 Markdown，用作网页导出兜底。 |
| `dingtalk-knowledge-organize` | 对钉钉知识库做盘点、分类、移动、重命名、去重和 CSV 审批式整理。底层操作优先走 `dws doc` / `dws wiki`。 |
| `dingtalk-minutes-access-request` | 只处理钉钉 AI 听记权限申请、权限复查和阻塞诊断。听记正文、摘要、转写读取应走 `dws minutes`。 |
| `dingtalk-oa-approval` | 审阅钉钉 OA 审批，要求读完整审批详情、流水、附件、链接文档和依据材料后再给审批意见。 |
| `fxiaoke-crm-cli` | 使用官方 `sharecrm` CLI 查询纷享销客 CRM 合同、商机、客户、联系人、交付、回款和跟进，按明确口径输出指标，并在 CRM 写操作前要求最终确认。 |
| `qa-generated-test-case` | 根据 PRD 生成标准 7 列 QA 测试用例，支持外部历史材料索引的 top N 检索、CSV/XLSX 导出和格式校验。 |
| `senior-technical-product-evaluation` | 评估 CTO、技术总监、架构师、资深 AI/工程负责人等高级技术候选人的产品经历，要求互联网调研、产品事实卡、候选人责任边界推断、技术深度评分和目标岗位匹配判断。 |
| `spec-intake` | 把一句话业务需求访谈成 Spec Driven JSON，要求逐步澄清业务证据、交付边界、验收标准、测试标准、运维标准和评审门禁。 |
| `stardust-interview` | 星尘候选人面试工作流：读取小青候选人材料和岗位画像，按需结合 DWS AI 听记，按 Derek 的证据链标准准备面试建议、结构化面评，并在确认后 dry run + 提交小青面评。 |
| `stardust-sre` | 为星尘 Web/API/worker 服务生成生产部署包、发布门禁、Kubernetes/Docker 模板、变更单和域名申请材料，并执行部署前安全与运维基线检查。 |
| `vibe-coding` | 将 `spec-intake` 产出的工程就绪 Spec 自动编排成稳定代码：初始化项目合同，按风险治理架构和技术债，执行 TDD、业务场景 E2E/Eval、独立 Review、Git 交付和可选 SRE 部署。 |

## 适用场景

- 你已经用 Codex、Claude Code 或类似 Agent 运行本地 skills。
- 你使用 `~/.agents/skills` 作为本机 skills 安装目录。
- 你希望把星尘内部反复使用的业务流程版本化，而不是每次临时写提示词。
- 你希望 Agent 能继承统一的审阅规则、证据标准、提交协议和输出格式。
- 你希望对内部系统做源码级安全审计，并沉淀可复查的风险证据和整改验收标准。
- 你已经有可用的业务工具授权，例如 `dws`、官方 `sharecrm` CLI 登录会话、`xiaoqing_interview` MCP、浏览器登录态或本地开放平台配置。

## 安装

克隆仓库后运行：

```bash
./install.sh
```

安装脚本会把 `skills/*` 同步到：

```text
~/.agents/skills
```

使用 `fxiaoke-crm-cli` 前，需要另行安装官方 `sharecrm` CLI 和用于本地结构化聚合的 `jq`，并由每位使用者在本机完成登录：

```bash
sharecrm auth login
sharecrm auth status
```

CLI 登录会话保留在使用者本机，不由安装脚本复制，也不得提交到本仓库。

安装时会排除本地状态文件，例如：

- `config.json`
- `.env`
- `node_modules`
- `__pycache__`
- `.storage_state.json`
- `.chrome-profile`
- 导出的 Excel、JSONL、日志和输出目录
- 运行产物目录 `runs`

## 从本机 Skills 更新仓库

当你在本机 `~/.agents/skills` 里修改了本仓库已有的同名 skill，可以运行：

```bash
./scripts/sync-from-agents.sh
```

脚本只会更新仓库 `skills/` 里已经存在的同名目录，不会把本机其他 skill 自动加入仓库。同步时会排除 `config.json`、`.env`、浏览器状态、输出目录、日志和导出文件。

## 从 GitHub 更新本机 Skills

当 GitHub 上的 `main` 有新 skill 更新，需要同步到本机 `~/.agents/skills`，可以运行：

```bash
./scripts/sync-to-agents.sh
```

脚本会先 `fetch origin/main`。只有当前仓库是干净的 `main` 且可以安全 fast-forward 时，才会更新本地仓库，并把 GitHub 上的新 skill 版本同步到 `~/.agents/skills`。如果本机 skill 只是落后于 GitHub，会直接更新；如果本机 skill 也有修改，脚本会用上次同步的 repo 版本、本机版本和 GitHub 版本尝试三方合并；只有同一文件发生无法自动合并的冲突时才会停止。同步到本机时同样会排除 `config.json`、`.env`、浏览器状态、输出目录、日志和导出文件。

## 使用方式

安装后，在支持 skills 的 Agent 中直接提出任务即可。例如：

```text
帮我把已有工作上下文导入 Friday Memory
```

```text
导出 2026 Q2 叮当 OKR，整理成每个人一个 tab 的 Excel，并审核韩露的 KR 完成情况
```

```text
这个钉钉 AI 听记链接打不开，帮我申请访问权限
```

```text
盘点这个钉钉知识库，先给我一个 CSV 整理建议，不要直接移动文件
```

```text
看一下这个钉钉 OA 审批材料是否足够，给出审批意见
```

```text
根据 AI 听记和小青候选人材料，帮我准备这个候选人的三面结构化面评
```

```text
用 dengbao-code-audit 扫描当前项目，输出一份等保代码安全检测报告和优先整改清单
```

```text
把这个一句话需求访谈成工程可以评审的 Spec Driven JSON
```

```text
使用 vibe-coding 按这个 engineering_ready Spec 完成开发、测试、Eval、Review 并推送；需要改变业务、架构或计划时再给我选择题。
```

```text
统计今年已签约合同金额、平均成单周期、商机转换率、交付量和回款额，列出每项指标的口径
```

```text
查询这个客户及其联系人、当前商机和最近跟进；不要修改 CRM
```

## 权限和凭证

不同 skill 的权限来源不一样。仓库只保存流程和规则，不保存 token、cookie、浏览器状态或私有导出数据。

| Skill | 是否需要开放平台 AppKey/AppSecret |
| --- | --- |
| `build-work-memory` | 不需要开放平台 key。它需要已安装并鉴权的 Friday Memory MCP，以及已安装并登录的 `dws`；本地文档只有在用户明确指定路径并确认后才读取。 |
| `dengbao-code-audit` | 不需要开放平台 key。它读取用户授权范围内的本地源码、配置、部署文件和项目文档；报告中不得暴露 token、密码、私钥、连接串等敏感值。 |
| `dingtang-okr-review` | 当前导出不需要。它使用已登录 Chrome 中的叮当 OKR 页面，前提是当前浏览器账号本身有 OKR 查看权限。CEO review 阶段会按用户授权读取本地文件、`memory_recall` 和 `dws` 资料核实 KR。 |
| `dingtalk-browser-export` | 当前不需要。它使用已登录 Chrome 中当前打开的 DingTalk/Alidocs 页面。 |
| `dingtalk-minutes-access-request` | 当前不需要开放平台 key。它使用浏览器登录态申请或复查 AI 听记访问权限；正文读取走 `dws minutes`。 |
| `dingtalk-knowledge-organize` | 通常需要可用的 `dws` 授权，部分旧脚本也支持读取本机 `~/.dingtalk-skills/config`。不要把配置提交到仓库。 |
| `dingtalk-oa-approval` | 优先使用 `dws oa` 授权；只有在 DWS 详情缺字段且用户已授权时，才会用本机开放平台配置补读。 |
| `fxiaoke-crm-cli` | 需要官方 `sharecrm` CLI 及当前使用者在本机建立的有效登录会话。CLI 会话不进入仓库，Agent 不索要、不读取、不共享 token、cookie 或其他凭证；查询、写入权限和审计继承当前登录的 CRM 用户。 |
| `qa-generated-test-case` | 默认不需要业务系统凭证。若需要历史 PRD 上下文，应从用户授权的 memory/document store、私有数据目录或单独数据包检索 top N 片段，不把历史材料提交到仓库。 |
| `senior-technical-product-evaluation` | 默认不需要业务系统凭证。它需要互联网调研公开资料；简历、内部汇总或候选人陈述只作为线索，不能单独证明产品领先性或候选人贡献。 |
| `spec-intake` | 默认不需要业务系统凭证。若需求涉及现有系统、repo、API、MCP、Memory、Friday 或客户系统，应读取用户授权范围内的本地代码/文档来确认边界；不要提交访谈产物或客户资料。 |
| `stardust-interview` | 需要可用的 `xiaoqing_interview` MCP OAuth 授权；读取 AI 听记时还需要可用的 `dws minutes` 授权。 |
| `stardust-sre` | 默认不需要业务系统凭证。它读取用户授权范围内的仓库源码、部署配置和需求材料；生成的发布包、变更单、域名申请和安全检查结果仍需按生产变更流程确认后执行。 |
| `vibe-coding` | 默认不需要业务系统凭证，但需要用户授权读取和修改目标仓库、运行其测试/Eval 命令并访问已确认的远程仓库。生产数据、Secret、部署和外部系统写入仍由项目权限及 `production-devops-sre` 门禁控制。 |

`dingtang-okr-review` 的 OKR 导出目前不是纯 API 实现。未来如果 `dws okr` 或叮当 OKR 官方 API 可用，才需要根据对应 API 的企业权限、应用授权或服务开通方式配置凭证。

## 设计原则

1. **事实源优先。** 先用对应业务系统读取事实，再分析；不要用本地缓存、浏览器页面或猜测替代正式事实源。
2. **一个业务边界一个 skill。** OKR、审批、知识库整理、听记权限、浏览器导出、候选人面试不要合并成一个宽泛 skill。
3. **高影响动作先确认。** 审批同意/拒绝、面评提交、批量移动文件、删除内容等动作必须先展示依据和预期影响，用户确认后再执行。
4. **不保存敏感状态。** 仓库不应包含 token、cookie、浏览器 profile、storage state、真实导出数据或本地配置。
5. **可审计输出。** 涉及批量整理、审批、OKR 导出、面评提交或安全审计时，保留可复查的证据、字段、链接、revision、风险分级或质量说明。

## 目录结构

```text
.
├── install.sh
├── skills/
│   ├── build-work-memory/
│   ├── dengbao-code-audit/
│   ├── dingtang-okr-review/
│   ├── dingtalk-browser-export/
│   ├── dingtalk-knowledge-organize/
│   ├── dingtalk-minutes-access-request/
│   ├── dingtalk-oa-approval/
│   ├── fxiaoke-crm-cli/
│   ├── qa-generated-test-case/
│   ├── senior-technical-product-evaluation/
│   ├── spec-intake/
│   ├── stardust-interview/
│   ├── stardust-sre/
│   └── vibe-coding/
└── README.md
```

## 安全说明

公开仓库前请确认：

```bash
rg -n "(secret|token|cookie|authorization|storage_state|config\\.json|password)" .
```

如果需要本地配置，请使用各 skill 的 `config.example.json` 作为模板，在安装后的本机 skill 目录中创建 `config.json`，不要提交到仓库。

## License

MIT
