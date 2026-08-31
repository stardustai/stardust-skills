# Vibe Coding Rescue Skill

`vibe-coding-rescue` 用于抢救 AI 生成、Vibe Coding 产出或历史遗留项目里的工程烂尾状态：本地启动失败、测试红、README 不可信、环境变量缺失、前后端契约漂移、数据库迁移失败、CI/部署失败，或代码里存在“看起来完成但没有真实闭环”的假实现。

它的目标不是替代完整 `vibe-coding` 交付流程，而是在项目已经坏掉、卡住或新人跑不起来时，先恢复一个可验证的工程基线。

## 适用场景

- README 写着能跑，但新同事按步骤启动失败。
- `npm/pnpm/yarn install`、`build`、`test`、`dev`、`start` 或 CI 报错。
- 前端 API 调用、后端路由、DTO/OpenAPI、数据库 schema 或迁移之间对不上。
- `.env.example`、README、Docker/K8s、CI 和代码里的环境变量不一致。
- AI 生成代码混入 mock、TODO、硬编码路径、吞异常、假数据或未验证的完成声明。
- 需要在修复前输出根因链、最小修复计划和验证命令。

## 不适用场景

- 从 engineering-ready Spec 正常开发新需求：用 `vibe-coding`。
- 做内部系统技术栈或生产标准评审：用 `internal-app-standards`。
- 做等保/MLPS 安全审计：用 `dengbao-code-audit`。
- 没有失败现象，只想泛泛优化代码结构：先明确目标和验收信号。

## 推荐流程

1. 先保护工作区，读取 README、manifest、lockfile、env 模板、CI、部署和迁移文件。
2. 运行只读体检脚本收集仓库信号：

```bash
python3 <skill-dir>/scripts/collect_rescue_context.py <project-root> --output <workdir>/rescue-context.json
```

3. 复现原始失败，记录命令、退出码和关键日志。
4. 按 `failure-taxonomy.md` 把问题归到环境、依赖、契约、代码、测试、数据、文档或部署边界。
5. 按 `rescue-workflow.md` 一次只修一个已证明的失败链。
6. 用原失败命令和相关 install/build/test/start/health 命令重新验证。
7. 按 `output-contract.md` 输出修复结论、证据、剩余风险和 Git 状态。

## 输出

- 救援结论：`fixed`、`partially fixed` 或 `blocked`。
- 原始失败命令和失败边界。
- 根因链：症状 -> 失败边界 -> 根因 -> 修复。
- 修改文件和原因。
- 已运行验证命令、退出码和剩余失败。
- README / 新人启动闭环状态。
- 剩余风险、未执行检查和需要 owner 决策的事项。

## 目录结构

```text
vibe-coding-rescue/
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── failure-taxonomy.md
│   ├── output-contract.md
│   └── rescue-workflow.md
└── scripts/
    └── collect_rescue_context.py
```

## 安全边界

- 脚本只读取仓库文件和 Git 状态，不执行 install/build/test/start/deploy。
- `.env`、token、cookie、私有 URL、数据库内容、浏览器状态和生产凭证不得进入报告、测试 fixture 或提交。
- 不能把本机跑通直接等同于新人环境、CI、生产或部署就绪；必须说明验证范围。
