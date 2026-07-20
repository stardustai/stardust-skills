# Dengbao Code Audit Skill

`dengbao-code-audit` 用于从等保三级/MLPS 2.0 Level 3 的代码安全视角审计项目。它面向工程整改，不替代正式等保测评。

## 适用场景

- 审计内部系统或公网系统的认证、权限、日志、数据安全、接口安全和传输安全。
- 检查部署文件、CI/CD、配置、脚本和项目文档中的安全缺口。
- 生成 Markdown 安全检测报告和整改计划。

## 审计范围

默认覆盖：

- 源代码
- 配置文件
- Docker、Kubernetes、Nginx 等部署材料
- CI/CD 文件
- 脚本
- README 和 docs

默认排除依赖、构建和缓存目录，例如 `.git`、`node_modules`、`dist`、`build`、`target`、`.venv`、`coverage`。

## 推荐流程

1. 确认项目根目录和审计范围。
2. 运行 inventory 脚本生成文件清单：

```bash
python3 <skill-dir>/scripts/inventory.py <project-root> --output <workdir>/dengbao-inventory.json
```

3. 运行规则扫描获取第一批证据：

```bash
python3 <skill-dir>/scripts/grep_rules.py <project-root> --output <workdir>/dengbao-findings.json
```

4. 阅读关键代码路径，验证 grep 结果是否真实成立。
5. 按模板生成或整理报告：

```bash
python3 <skill-dir>/scripts/summarize_findings.py \
  --inventory <workdir>/dengbao-inventory.json \
  --findings <workdir>/dengbao-findings.json \
  --output <project-root>/reports/等保代码安全检测报告.md
```

6. 将脚本发现升级为人工确认后的风险、影响、修复建议和验收标准。

## 报告要求

每个问题必须包含：

- 风险等级：`高危`、`中危`、`低危` 或 `待确认`
- 分类：登录认证、权限控制、安全审计、数据安全、接口安全、传输安全、运维暴露面、备份恢复、发布变更、文档材料
- 证据：文件路径和行号
- 影响：在当前系统中可能发生什么
- 修复建议：可执行的代码、配置或流程改动
- 验收标准：团队如何验证修复完成

## 目录结构

```text
dengbao-code-audit/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── checklist.md
│   ├── framework-patterns.md
│   ├── remediation-playbook.md
│   ├── report-template.md
│   └── severity-rubric.md
└── scripts/
    ├── grep_rules.py
    ├── inventory.py
    └── summarize_findings.py
```

## 安全边界

- 不在报告中原样输出 token、密码、私钥、连接串或 session。
- 正则命中只是线索，不是结论。
- 代码无法确认时标记为 `待确认`，并说明需要补充的材料。
