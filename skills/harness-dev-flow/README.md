# Harness Dev Flow

从空仓库起步、靠分层 markdown 文档驱动 AI 编码、逐块可重复验收的轻量 agent-first 开发流程。适合隔离的低风险原型和正式立项前的需求梳理。

## 这是什么

一个 Codex skill，封装了一套从「空仓库」到「可验收原型」的开发流程：

- 人写 spec、契约、验收标准
- AI agent 写代码
- `docs/` 里的分层 markdown 文档是唯一事实来源
- 按 MVS 依赖链逐块推进，每块都带可重复验收

## 为什么做这个

灵感来自 OpenAI 工程博客 [《Harness Engineering: leveraging Codex in an agent-first world》](https://openai.com/index/harness-engineering/) ——核心一句话："Humans steer. Agents execute."

这套流程从实际项目中提炼，用于把原型按可验证的依赖关系逐步推进。

博客讲的是大团队工程化实践，这个 skill 把它压缩到**单人、轻量、不依赖大团队设施就能跑**的版本。

## 安装

在公司仓库根目录运行 `./install.sh`，将其安装到 `~/.agents/skills/harness-dev-flow/`。公司正式项目仍以 `spec-intake` 和 `vibe-coding` 为交付流程。

Skill 文件结构：

```
harness-dev-flow/
├── SKILL.md
├── agents/
│   └── openai.yaml
└── references/
    ├── prd-structure.md
    ├── tech-plan-structure.md
    ├── mvs-plan-structure.md
    ├── execplan-structure.md
    ├── acceptance-structure.md
    ├── architecture-overview.md
    └── doc-layout.md
```

## 用法

1. 新建一个空项目仓库。
2. 在 Codex 里描述你想做什么（模糊想法即可）。
3. skill 会自动触发，引导你按顺序产出：PRD → 技术 Plan → MVS-Plan → 逐 MVS 实现（ExecPlan + 可重复验收）→ 架构总览收口。
4. 全程：你写「要达成什么 + 怎么算成功」，agent 写代码。

## 流程一览

| 阶段 | 产出 | 模板 |
|------|------|------|
| Phase 0｜技术探针 SP-00 | 可丢弃的最小验证代码 | — |
| Phase 1｜PRD | What / Why / How well | `references/prd-structure.md` |
| Phase 2｜技术实现 Plan | 架构选型、技术栈、现场验证 | `references/tech-plan-structure.md` |
| Phase 3｜MVS-Plan | 有依赖顺序的最小可验证切片 | `references/mvs-plan-structure.md` |
| Phase 4｜逐 MVS 实现 | ExecPlan + 单元拆分 + 可重复验收 | `references/execplan-structure.md`、`references/acceptance-structure.md` |
| Phase 5｜架构总览收口 | 最后写的整体架构文档 | `references/architecture-overview.md` |

## 设计理念

6 条核心原则：仓库即唯一事实来源 / 地图而非手册 / 指定意图+建反馈回路 / 深度优先积木解锁积木 / 人掌舵 agent 执行 / 区分模型权威与代码权威。

完整说明见 [`SKILL.md`](./SKILL.md)。

## License

MIT
