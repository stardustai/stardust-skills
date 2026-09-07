# AI PR Redteam Skill

`ai-pr-redteam` 用于审查 AI 生成、Vibe Coding 产出或 agent 大比例参与的 PR / diff / commit，在合入前识别 fake 逻辑、fallback 假成功、弱测试、契约漂移，以及按编程语言范式判断的工程质量问题。

它的定位是“反方审查官”，不是修复工具。重点不是让报告显得严格，而是帮 reviewer 判断：这次 PR 是否真的完成、能否维护、证据是否足够、合入前必须改什么。

## 适用场景

- AI 生成的 PR 需要合入前验伪。
- 代码里出现 mock、fake、sample、dummy、fallback、TODO、hardcode 等可疑生产路径。
- 测试全绿但只断言 HTTP 200、mock 调用、snapshot 或 happy path。
- 需要分析代码拆分、包边界、抽象复用、错误处理、测试可维护性。
- 需要针对 TypeScript/JavaScript、Python、Go、Java/Kotlin 等语言按各自规范给工程质量建议。
- 需要输出可执行优化建议、owner、验收标准和 proof command。

## 不适用场景

- 项目已经跑不起来，需要救援修复：用 `vibe-coding-rescue`。
- 内部系统完整技术栈和生产标准设计：用 `internal-app-standards`。
- 等保 / MLPS 安全专项审计：用 `dengbao-code-audit`。
- 正常开发实现功能：用 `vibe-coding` 或普通开发流程。

## 推荐用法

```bash
python3 skills/ai-pr-redteam/scripts/scan_ai_pr.py <repo-root> --base origin/main --format markdown --output /tmp/ai-pr-redteam-scan.md
```

没有 base ref 时可以省略：

```bash
python3 skills/ai-pr-redteam/scripts/scan_ai_pr.py <repo-root> --format json
```

脚本只提供线索。最终审查必须由 Agent 读取 PR 描述、diff、相关代码、测试和运行证据后判断。

## 输出能力

- `Fake / Fallback Findings`：识别生产路径 fake 数据、fallback success、假集成、假权限、假配置、假测试。
- `Engineering Quality Findings`：先识别语言，再按语言设计思想分析模块拆分、包边界、抽象复用、错误处理和可测试性。
- `Targeted Optimization Plan`：给出最小修复、更好设计、owner、验收标准和 proof command。
- `Merge Decision`：输出 `block`、`changes_requested`、`risky_but_mergeable` 或 `pass`。

## 目录结构

```text
ai-pr-redteam/
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── fake-fallback-taxonomy.md
│   ├── language-quality-rules.md
│   └── output-contract.md
└── scripts/
    ├── scan_ai_pr.py
    └── test_scan_ai_pr.py
```

## 安全边界

- 默认只读审查，不修改 PR。
- 不提交 `.env`、token、cookie、私有 URL、数据库内容、日志敏感片段或本机状态。
- 扫描结果不是事实结论，只是 review leads；报告中必须区分已验证、疑似和未知。
