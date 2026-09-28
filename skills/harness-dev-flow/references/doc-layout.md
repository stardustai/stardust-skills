# 文档目录布局与索引规则

docs/ 是唯一事实来源（Harness 原则 1），README.md 是地图而非手册（原则 2）。

## 目录结构

```
docs/
├── README.md            # 目录索引（map），按 MVS 分节列链接
├── overview/            # 跨阶段产物：PRD、技术 Plan、MVS-Plan、最后的架构总览
├── mvs-01/              # 一个 MVS 一个目录
│   ├── MVS-01-ExecPlan.md
│   ├── MVS-01-01-<单元名>.md
│   └── MVS-01-<末>-可重复验收.md
├── mvs-02/
│   └── schema-catalog/  # 阶段内持续多文档的主题建子目录
└── mvs-xx/
```

## 放置规则
- 跨阶段的 PRD、总计划、整体技术方案、架构总览放 `overview/`。
- 一个 MVS 的入口 ExecPlan 和阶段级说明放对应 `mvs-xx/`。
- 阶段内持续产生多个文档的主题，建子目录（如 `mvs-02/schema-catalog/`）。
- 从第二个 MVS 起，最细执行单元固定为 `MVS-xx-yy`，不再拆 `MVS-xx-yy-zz`；内部清单不形成独立编号/ExecPlan/进度状态。
- 最小执行单元沿用编号命名，放所属主题目录，不继续增加目录深度。

## README 索引维护
- README 按 MVS 分节，每节列出该 MVS 的 ExecPlan + 全部单元文档 + 可重复验收的本地链接。
- 新增、移动或重命名文档后，**必须同步更新 README 并通过 Markdown 本地链接检查**。
- README 末尾附"后续放置规则"，让下一位执行者（人或 agent）知道文档该放哪。

## AGENTS.md（仓库根，可选）
- 若用，保持约 100 行，只当目录索引，指向 docs/ 更深的真相，不堆规则。
- 不要写成一个塞满约束的巨文件：会挤占上下文、瞬间腐烂、无法机械校验。
