# Stardust Skills

星尘公用 Agent Skills 仓库，用来沉淀公司内部可复用的 Agent 工作流、判断标准、输出格式和工具调用边界。

这个项目不是钉钉官方 SDK，也不是 `dws`、小青 MCP 或任何业务系统的替代品。它的定位是让 Agent 在星尘的真实业务里按统一规则工作：先读事实源，再按业务判断标准分析，最后在用户确认后执行高影响操作。

当前仓库覆盖 Friday Memory 初始化、每日技术前沿发现、钉钉、叮当 OKR、DingTalk/Alidocs、OA 审批、知识库整理、AI 听记权限、纷享销客 CRM、OCR、TTS 语音合成、ASR 转写、在线视频转写、内部任务上下文、融资会议、PRD 测试用例生成、需求规格访谈、项目交付结项资料收集、PM 数据适配和 Conflux 问答、Startask/Stardust I/O 契约审计、Vibe Coding 工程交付、Vibe Coding 项目救援、候选人面试、高级技术候选人产品经历评估、小青面试系统、SRE 部署交付、等保代码安全审计和内部系统工程标准。具体原子操作仍交给对应工具完成：Memory 导入优先走已安装的 Friday Memory MCP，每日技术前沿发现先扫描可信聚合源和一手技术资料，再结合内部人物、会议和项目上下文筛选并归档；钉钉能力优先走 `dws`，纷享销客数据优先走官方 `sharecrm` CLI，图片和扫描 PDF 的文字识别走 Stardust 对外 OCR 服务，文本转 MP3 走 Stardust 对外 Qwen3-TTS 服务，音视频文件转写走 OpenAI 转写模型，在线视频转写走 Stardust Video Transcribe 服务，融资事实优先走 FundFlow MCP，候选人和面评业务事实优先走 `xiaoqing_interview` MCP，浏览器只作为明确授权后的兜底路径；项目交付结项类 skill 主要盘点、核验和组织资料，不替代财务、法务、数据安全或正式结项审批；PM 数据适配问答类 skill 主要用项目经理能理解的语言解释导入/导出、平台错误、PM-check、交付校验和 Conflux 概念，不替代开发根因确认或客户交付审批；Startask/Stardust 契约审计类 skill 主要核对客户规格、真实样例、operator/schema、平台记录、适配代码和校验器，不替代平台端或客户验收；`task-management` 只读取已部署 CEO agent service 的本地任务上下文，不能修改任务；`vibe-coding` 以 `spec-intake` 的工程就绪 Spec 为输入，自动编排项目初始化、架构治理、计划、TDD、业务 E2E/Eval、Review 和 Git 交付；`vibe-coding-rescue` 面向 AI 生成或遗留项目的启动、构建、测试、环境、契约、迁移、CI/部署和 README 漂移救援，不替代正式需求交付或生产变更审批；内部系统标准类 skill 主要约束技术栈选型、工程设计、代码结构和生产门禁；部署类 skill 主要生成可审计的部署包、发布门禁和变更材料，不替代正式生产变更审批；安全审计类 skill 主要读取本地项目源码、配置、部署文件和项目文档，不替代正式等保测评。

## 包含的 Skills

| Skill | 作用 |
| --- | --- |
| `build-work-memory` | 引导用户首次初始化 Friday Memory：按用户确认的范围读取本地文档、钉钉知识库 / 文档、钉钉 AI 听记和其他指定钉钉数据，标准化来源信息后提交到 Memory 后台处理。 |
| `daily-frontier-tech-discovery` | 扫描最近 72 小时的技术聚合源、一手博客、GitHub、评测与高影响论文，结合内部人物、会议和项目上下文筛选，归档完整候选分析，并生成可直接发送到钉钉的中文技术日报。 |
| `dengbao-code-audit` | 从等保三级 / MLPS 2.0 视角检查源码、配置、部署文件和项目文档，覆盖登录认证、权限控制、安全审计、数据安全、接口安全、传输安全、运维暴露面、备份恢复、发布变更和文档材料，并输出 Markdown 风险报告和整改路线图。 |
| `dingtang-okr-review` | 从叮当 OKR 页面导出 OKR Excel，并按 CEO 视角在 KR 层级做证据核实、打分和超时折扣。 |
| `dingtalk-browser-export` | 从已登录 Chrome 当前打开的 DingTalk/Alidocs 文档导出为 docx、PDF 或 Markdown，用作网页导出兜底。 |
| `dingtalk-knowledge-organize` | 对钉钉知识库做盘点、分类、移动、重命名、去重和 CSV 审批式整理。底层操作优先走 `dws doc` / `dws wiki`。 |
| `dingtalk-minutes-access-request` | 只处理钉钉 AI 听记权限申请、权限复查和阻塞诊断。听记正文、摘要、转写读取应走 `dws minutes`。 |
| `dingtalk-oa-approval` | 审阅钉钉 OA 审批，要求读完整审批详情、流水、附件、链接文档和依据材料后再给审批意见。 |
| `fundflow-investor-meeting` | 准备 FundFlow/融管通投资人会议、会后复盘、投资人问题和风格分析、跟进建议，以及融资群更新。 |
| `fxiaoke-crm-cli` | 使用官方 `sharecrm` CLI 查询纷享销客 CRM 合同、商机、客户、联系人、交付、回款和跟进，按明确口径输出指标，并在 CRM 写操作前要求最终确认。 |
| `internal-app-standards` | 统一 AI 编码生成的企业内部系统标准，覆盖技术栈选型、工程设计、React + Ant Design 前端、TypeScript/NestJS 后端、PostgreSQL/Prisma、迁移、Docker/Kubernetes 部署、生产就绪检查和代码评审门禁。 |
| `ocr` | 调用 Stardust 对外 OCR 服务识别图片、截图和扫描 PDF，支持中英文、批量输入、指定 PDF 页码，以及 text、Markdown 和 JSON 输出。 |
| `pm-data-adaptation-assistant` | 面向项目经理回答多模态数据适配、平台导入/导出错误、PM-check、交付校验和 Conflux 使用问题，说明 PM 应收集的信息、下一步动作和是否需要开发确认。 |
| `project-delivery-document-collection` | 面向已交付或待结项项目，自动盘点、补充、核验并归档结项资料，输出项目结项文档目录、交付完成报告、缺口清单、复盘报告和知识库沉淀清单。 |
| `qa-generated-test-case` | 根据 PRD 生成标准 7 列 QA 测试用例，支持外部历史材料索引的 top N 检索、CSV/XLSX 导出和格式校验。 |
| `senior-technical-product-evaluation` | 评估 CTO、技术总监、架构师、资深 AI/工程负责人等高级技术候选人的产品经历，要求互联网调研、产品事实卡、候选人责任边界推断、技术深度评分和目标岗位匹配判断。 |
| `spec-intake` | 把一句话业务需求访谈成 Spec Driven JSON，要求逐步澄清业务证据、交付边界、验收标准、测试标准、运维标准和评审门禁。 |
| `startask-io-contract-audit` | 在 Startask/Stardust 导入、预标、导出、回流或交付前，核对客户规格、真实样例、operator/schema、平台记录、适配代码和校验器，输出字段契约矩阵、冲突归属和 G0-G6 就绪结论。 |
| `stardust-interview` | 星尘候选人面试工作流：读取小青候选人材料和岗位画像，按需结合 DWS AI 听记，按 Derek 的证据链标准准备面试建议、结构化面评，并在确认后 dry run + 提交小青面评。 |
| `stardust-sre` | 为星尘 Web/API/worker 服务生成生产部署包、发布门禁、Kubernetes/Docker 模板、变更单和域名申请材料，并执行部署前安全与运维基线检查。 |
| `stardust-tts` | 调用 Stardust 对外 Qwen3-TTS CustomVoice 服务，把文本生成 MP3；支持 9 个预设音色和自然语言风格指令，并在本地校验音色、长度和文件格式。 |
| `task-management` | 从本机 CEO agent service 只读查询内部项目、TODO、负责人、截止日期、阻塞项和跟进上下文；不通过该 skill 创建或修改任务。 |
| `transcribe` | 使用 OpenAI 转写模型把音频/视频转成文本，按需支持说话人区分和已知说话人参考音频。 |
| `veyra-timesheet` | 把一段时间的真实活动核对并补齐到 Veyra 睿策工时系统：采集钉钉侧证据（日程、消息、听记、日志）并与已填记录对账，逐日推断项目归属，小时数以数值·依据·置信度形式提案，经用户确认后写入。支持请假与加班，仅 macOS。 |
| `video-transcribe` | 通过 Stardust Video Transcribe 服务提取 YouTube 或 Bilibili 视频的字幕或 ASR 文本；视频 URL 与转写内容发送到该服务，服务凭证仅保留在本机。 |
| `vibe-coding` | 将 `spec-intake` 产出的工程就绪 Spec 自动编排成稳定代码：初始化项目合同，按风险治理架构和技术债，执行 TDD、业务场景 E2E/Eval、独立 Review、Git 交付和可选 SRE 部署。 |
| `vibe-coding-rescue` | 抢救 AI 生成、Vibe Coding 产出或历史遗留项目的启动、构建、测试、环境、API 契约、数据库迁移、CI/部署和 README 漂移问题，输出根因链、最小修复计划和新鲜验证证据。 |

## 适用场景

- 你已经用 Codex、Claude Code 或类似 Agent 运行本地 skills。
- 你使用 `~/.agents/skills` 作为本机 skills 安装目录。
- 你希望把星尘内部反复使用的业务流程版本化，而不是每次临时写提示词。
- 你希望 Agent 能继承统一的审阅规则、证据标准、提交协议和输出格式。
- 你希望在项目交付后自动盘点结项资料、识别缺口、生成结项报告，并把可复用经验沉淀到知识库。
- 你希望项目经理能用统一口径理解数据适配导入/导出、平台报错、PM-check、交付校验和 Conflux 使用边界。
- 你希望在 Startask/Stardust 导入、预标、导出、回流或交付前审计客户契约、字段映射、平台记录、适配代码和验证边界。
- 你希望把 AI 生成或遗留项目从“跑不起来 / 测试红 / README 不可信 / CI 失败”救回到可验证工程基线。
- 你希望对内部系统做源码级安全审计，并沉淀可复查的风险证据和整改验收标准。
- 你希望 AI 生成或改造的内部管理系统遵循统一的技术栈、工程设计、目录边界、数据库迁移、部署脚本和生产就绪门禁。
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
- `api_key`
- `.chrome-profile`
- 导出的 Excel、JSONL、日志和输出目录
- 运行产物目录 `runs`

如果希望本机已安装 skills 每天自动跟随 GitHub/main 更新，可以安装每日同步任务：

```bash
./install.sh --daily-sync
```

每日同步会在本机安装一个 macOS LaunchAgent，默认每天本地时间 09:00 运行：

```bash
./scripts/sync-to-agents.sh --repo <当前仓库> --dest ~/.agents/skills --remote origin --branch main
```

它只把 GitHub/main 中的仓库 skill 同步到本机 `~/.agents/skills`，不会把本机修改同步回仓库，也不会提交或 push。同步脚本会先检查仓库分支、未提交变更和 fast-forward 安全性；如果本机 installed skill 与 GitHub 更新发生无法自动合并的冲突，会停止并保留本机内容。

可以指定每日同步时间：

```bash
./install.sh --daily-sync --daily-sync-hour 3 --daily-sync-minute 30
```

同步日志写入：

```text
~/.agents/logs/stardust-skills/daily-sync.log
~/.agents/logs/stardust-skills/daily-sync.err.log
```

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

每次过滤同步的 `rsync` 默认最多等待 120 秒；如果本机文件系统或 `rsync --checksum` 异常卡住，脚本会停止并报告卡住的源目录和目标目录。需要临时调整时，可设置 `SYNC_RSYNC_TIMEOUT_SECONDS` 为正整数秒数。

## 使用方式

安装后，在支持 skills 的 Agent 中直接提出任务即可。例如：

```text
帮我把已有工作上下文导入 Friday Memory
```

```text
生成今天的每日技术前沿洞察，重点关注 agent memory、评测和企业私有 AI；结合内部会议与项目说明推荐原因，归档后发到钉钉技术群
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
用 internal-app-standards 评审这个后台管理系统，指出不符合生产标准的地方和整改顺序
```

```text
用 internal-app-standards 为这个内部系统做技术选型和工程设计，先输出模块、API、数据模型、部署和测试方案
```

```text
用 project-delivery-document-collection 盘点这个已交付项目的结项资料，先输出文档清单和缺口清单
```

```text
用 pm-data-adaptation-assistant 解释这个平台导入报错，告诉 PM 需要补哪些材料、能否自助处理、什么时候必须找开发
```

```text
把这个一句话需求访谈成工程可以评审的 Spec Driven JSON
```

```text
用 startask-io-contract-audit 审计这次 Startask 导入/导出契约，输出字段契约矩阵、冲突归属和 G0-G6 就绪结论
```

```text
使用 vibe-coding 按这个 engineering_ready Spec 完成开发、测试、Eval、Review 并推送；需要改变业务、架构或计划时再给我选择题。
```

```text
用 vibe-coding-rescue 抢救这个 AI 生成项目，先复现 README 启动失败和测试失败，再输出根因链、最小修复计划和验证命令
```

```text
统计今年已签约合同金额、平均成单周期、商机转换率、交付量和回款额，列出每项指标的口径
```

```text
查询这个客户及其联系人、当前商机和最近跟进；不要修改 CRM
```

```text
把这段产品介绍生成 MP3，使用 Vivian，语气温暖自然、语速稍慢
```

## 权限和凭证

不同 skill 的权限来源不一样。仓库只保存流程和规则，不保存 token、cookie、浏览器状态或私有导出数据。

| Skill | 是否需要开放平台 AppKey/AppSecret |
| --- | --- |
| `build-work-memory` | 不需要开放平台 key。它需要已安装并鉴权的 Friday Memory MCP，以及已安装并登录的 `dws`；本地文档只有在用户明确指定路径并确认后才读取。 |
| `daily-frontier-tech-discovery` | 互联网发现需要可用的搜索/抓取能力；内部关联需要用户授权读取本机 memory 目录。钉钉机器人发送需要安装后在 `config/config.json` 配置 webhook 和 secret，并限制为 `600` 权限；真实配置、日报归档和发送历史都不进入仓库。 |
| `dengbao-code-audit` | 不需要开放平台 key。它读取用户授权范围内的本地源码、配置、部署文件和项目文档；报告中不得暴露 token、密码、私钥、连接串等敏感值。 |
| `dingtang-okr-review` | 当前导出不需要。它使用已登录 Chrome 中的叮当 OKR 页面，前提是当前浏览器账号本身有 OKR 查看权限。CEO review 阶段会按用户授权读取本地文件、`memory_recall` 和 `dws` 资料核实 KR。 |
| `dingtalk-browser-export` | 当前不需要。它使用已登录 Chrome 中当前打开的 DingTalk/Alidocs 页面。 |
| `dingtalk-minutes-access-request` | 当前不需要开放平台 key。它使用浏览器登录态申请或复查 AI 听记访问权限；正文读取走 `dws minutes`。 |
| `dingtalk-knowledge-organize` | 通常需要可用的 `dws` 授权，部分旧脚本也支持读取本机 `~/.dingtalk-skills/config`。不要把配置提交到仓库。 |
| `dingtalk-oa-approval` | 优先使用 `dws oa` 授权；只有在 DWS 详情缺字段且用户已授权时，才会用本机开放平台配置补读。 |
| `fundflow-investor-meeting` | 需要可用的 FundFlow MCP 授权；融资阶段、投资人状态、会议记录和跟进事实以 FundFlow 为准。DingTalk 群更新只在用户授权后执行，且发送前需要验证群和命令 schema。 |
| `fxiaoke-crm-cli` | 需要官方 `sharecrm` CLI 及当前使用者在本机建立的有效登录会话。CLI 会话不进入仓库，Agent 不索要、不读取、不共享 token、cookie 或其他凭证；查询、写入权限和审计继承当前登录的 CRM 用户。 |
| `internal-app-standards` | 不需要开放平台 key。它读取用户授权范围内的本地内部系统源码、配置、数据库迁移、Docker/K8s 文件和 CI/部署脚本，用于技术选型、工程设计和生产就绪评审；不得提交或报告明文密钥、连接串、token、私有域名等敏感值。 |
| `ocr` | 需要可访问 `https://ocr.preseen.ai/v1`。员工端通过公司邮箱完成 Cloudflare Access 登录；headless 工作负载使用成对的 `CF_ACCESS_CLIENT_ID/CF_ACCESS_CLIENT_SECRET`。本机 provider registry 只提供模型和语言默认值；识别文件只发送到该 OCR 服务。 |
| `pm-data-adaptation-assistant` | 默认不需要开放平台 key。它按已有沉淀回答 PM 的数据适配、平台错误和 Conflux 使用问题；若要判断当前生产行为、客户交付结论、脚本改动或平台配置，应由用户授权读取相应样例、平台记录、配置或代码并交开发确认，不得提交客户隐私数据、凭证、内网地址或完整私有路径。 |
| `project-delivery-document-collection` | 默认不需要开放平台 key。若需要读取或归档钉钉文档、知识库、云盘、审批、项目群或在线表格，应使用用户已授权的 `dws`、浏览器登录态或指定平台工具；不得把涉密数据、客户敏感附件、明文下载链接或受控数据包提交到仓库。 |
| `qa-generated-test-case` | 默认不需要业务系统凭证。若需要历史 PRD 上下文，应从用户授权的 memory/document store、私有数据目录或单独数据包检索 top N 片段，不把历史材料提交到仓库。 |
| `senior-technical-product-evaluation` | 默认不需要业务系统凭证。它需要互联网调研公开资料；简历、内部汇总或候选人陈述只作为线索，不能单独证明产品领先性或候选人贡献。 |
| `spec-intake` | 默认不需要业务系统凭证。若需求涉及现有系统、repo、API、MCP、Memory、Friday 或客户系统，应读取用户授权范围内的本地代码/文档来确认边界；不要提交访谈产物或客户资料。 |
| `startask-io-contract-audit` | 默认不需要开放平台 key。若需要读取 Startask/Stardust 平台记录、operator/schema、真实样例、适配代码或校验器，应使用用户授权的仓库、平台、样例目录或指定工具；不得提交客户敏感数据、签名 URL、平台凭证、私有对象定位或未脱敏样例。 |
| `stardust-interview` | 需要可用的 `xiaoqing_interview` MCP OAuth 授权；读取 AI 听记时还需要可用的 `dws minutes` 授权。 |
| `stardust-sre` | 默认不需要业务系统凭证。它读取用户授权范围内的仓库源码、部署配置和需求材料；生成的发布包、变更单、域名申请和安全检查结果仍需按生产变更流程确认后执行。 |
| `stardust-tts` | 需要可访问 `https://tts-api.preseen.ai/v1/audio/speech`。员工端必须通过公司邮箱 (`@stardust.ai`) 完成 Cloudflare Access 登录（OTP + PKCE）；工作负载端使用成对配置的 `CF_ACCESS_CLIENT_ID/CF_ACCESS_CLIENT_SECRET`。公开仓库不保存任何凭据；文本和风格指令只用于当前合成请求。 |
| `task-management` | 不需要开放平台 key。需要本机已运行的 CEO agent service 审计 Web API；该 skill 只读查询服务数据库中的任务上下文，不创建或修改任务。 |
| `transcribe` | 需要本机环境变量 `OPENAI_API_KEY`。仓库不保存 OpenAI API key；音视频文件只在用户指定任务中读取并发送给 OpenAI 转写接口。 |
| `veyra-timesheet` | 不需要开放平台 key。需要已登录的 `dws`，以及 opencli daemon + Browser Bridge 扩展（Chrome Web Store 安装），且挂扩展的 Chrome profile 已登录 Veyra。首次使用跑 skill 的 init 引导安装；登录态全部留在本机，不进仓库。 |
| `video-transcribe` | 需要可访问 `https://video-transcribe.preseen.ai`。员工端通过公司邮箱完成 Cloudflare Access 登录；headless 工作负载使用成对的 `CF_ACCESS_CLIENT_ID/CF_ACCESS_CLIENT_SECRET`。视频 URL 和服务返回的转写文本只用于当前用户任务。 |
| `vibe-coding` | 默认不需要业务系统凭证，但需要用户授权读取和修改目标仓库、运行其测试/Eval 命令并访问已确认的远程仓库。生产数据、Secret、部署和外部系统写入仍由项目权限及 `production-devops-sre` 门禁控制。 |
| `vibe-coding-rescue` | 默认不需要业务系统凭证。它读取用户授权范围内的目标仓库、README、manifest、lockfile、env 模板、CI/部署、迁移和测试材料；运行 install/build/test/start/deploy 或推送前遵循用户授权和项目风险边界，不得提交 `.env`、token、cookie、私有 URL、数据库内容、日志敏感片段或本机状态。 |

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
│   ├── daily-frontier-tech-discovery/
│   ├── dengbao-code-audit/
│   ├── dingtang-okr-review/
│   ├── dingtalk-browser-export/
│   ├── dingtalk-knowledge-organize/
│   ├── dingtalk-minutes-access-request/
│   ├── dingtalk-oa-approval/
│   ├── fundflow-investor-meeting/
│   ├── fxiaoke-crm-cli/
│   ├── internal-app-standards/
│   ├── ocr/
│   ├── pm-data-adaptation-assistant/
│   ├── project-delivery-document-collection/
│   ├── qa-generated-test-case/
│   ├── senior-technical-product-evaluation/
│   ├── spec-intake/
│   ├── startask-io-contract-audit/
│   ├── stardust-interview/
│   ├── stardust-sre/
│   ├── stardust-tts/
│   ├── task-management/
│   ├── transcribe/
│   ├── veyra-timesheet/
│   ├── video-transcribe/
│   ├── vibe-coding/
│   └── vibe-coding-rescue/
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
