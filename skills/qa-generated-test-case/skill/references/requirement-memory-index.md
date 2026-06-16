# 已沉淀需求索引

| 需求日期 | 需求标题 | 主题关键词 | 对应记忆条目 |
| --- | --- | --- | --- |
| 2026-05-11 | 标注池、检查池、抽查池配置质检算法支持选择强校验与弱校验（含上游报错联动） | 强校验、弱校验、上游报错、工作池流转、多记录 | `entries/2026-05-11-validation-type-with-upstream-errors.md` |
| 2026-05-11 | 算法池支持退回质检算法未通过数据（含上游报错联动） | 算法池、质检失败、滞留算法池、驳回原操作人、报错状态、上游报错 | `entries/2026-05-11-algorithm-pool-failed-data-handling.md` |
| 2026-05-12 | 项目进度统计 | 整体进度、已交付量、已用成本、验收通过率、计划交付总量、抽查池 | `entries/2026-05-12-project-progress-overview.md` |
| 2026-05-13 | 历史测试用例沉淀的全局产品知识 | Rosetta、MorningStar、Phoenix、项目管理、人工标注、数据集、工作池、导出、统计、权限 | `entries/2026-05-13-historical-testcases-global-product-knowledge.md` |
| 2026-05-18 | 新增数据快照保存机制与快照结果导出 | 数据快照、annotations去重、标注池、检查池、抽查池、算法池、完成池导出、jsonl | `entries/2026-05-18-data-snapshot-export.md` |
| 2026-05-18 | 数据快照保存机制与快照结果导出技术实现口径 | 保存快照接口、includeSnapshots、task_annotation_snapshot、SDFS、hash去重、算法池兜底、批量查询 | `entries/2026-05-18-data-snapshot-export-tech-implementation.md` |
| 2026-06-02 | license管理 | Phoenix、license管理、license生成、私有化部署、申请码、有效期、授权到期、Admin、License写入 | `entries/2026-06-02-license-management.md` |
| 2026-06-02 | 任务列表页新增筛选，数据展示功能 | 任务列表、多条件筛选、AND、筛选数量、跨页选中、导出选中任务、分配时间、更新时间 | `entries/2026-06-02-task-list-filter-display.md` |
| 2026-06-02 | Rosetta 平台历史 PRD 全量归档 | 历史PRD、业务知识库、工作流、标注工具、项目管理、数据管理、组织权限、算法接入、版本关系 | `entries/2026-06-02-historical-prd-archive.md` |
| 2026-06-05 | license管理 | license、私有化、权限、状态流转、标注工具 | `entries/2026-06-05-license-management.md` |
| 2026-06-09 | 一级属性预标注结果增加确认流程 | 标注工具、算法池、预标注、一级属性、确认流程、状态流转、提交阻断、草稿取消 | `entries/2026-06-09-primary-attribute-preannotation-confirmation.md` |

## 通用漏测雷达

1. 权限：页面入口、按钮操作、后端接口都要考虑。
2. 状态：开始、处理中、报错、完成、已过期、恢复等状态要明确触发条件。
3. 导出：旧格式兼容、字段顺序、特殊字符、大数据量、权限越权。
4. 统计：时间范围、分母为0、历史数据、重复计数、四舍五入、动态列。
5. 工作池：上游/下游展示、当前池报错、上游报错残留、强弱校验优先级。
6. 私有化：Admin 与普通用户差异、授权到期拦截、恢复后回归、环境隔离。
7. 任务列表：筛选 AND/OR 口径、筛选命中总量、跨页选中状态、导出选中范围、首次分配时间不覆盖。
8. 历史版本：一期/二期/三期/V3.x/废弃/待讨论/未实现只能作为版本关系线索，不能不加判断地当作当前规则。
