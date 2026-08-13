# Veyra API 契约与归口顺序

## 归口顺序

逐条判断，不凭手感。同一情形每次必须落到同一个项目，否则跨周对账会乱。

1. **不在岗** → `假期-001`
2. **这条活有正式商机或项目编号**（客户交付、客户售前、已立项研发）→ 挂那个编号。用客户名搜确认：`opencli veyra projects --search 华为`
3. **本人为主的售前动作但客户线还没有商机**（客户访谈、调研、demo、方案探索、公用文档）→ `QTSW-002`
4. **明确属于下列事务类之一** → 用对应编号，别一律兜底

| 编号 | 什么活挂它 |
|---|---|
| `QTSW-001` | 培训学习 |
| `QTSW-003` | 招聘 |
| `QTSW-004` | 部门管理 |
| `QTSW-005` | 公共支持——**支持他人或其他部门**的活，不是本人主责的项目 |
| `QTSW-006` | 跨部门会议 |

**第 3 条与 `QTSW-005` 的分界**（实测两次运行在这里判断不一致）：判断标准是**这件事是不是本人主责**。客户访谈、调研、方案探索由本人主导推进 → `QTSW-002`。替别人跑腿、给其他部门提供支持 → `QTSW-005`。

**会议本身不是归口依据**（实测两次运行在这里判断不一致）：归口看这场会**讨论的是哪条业务线**，按第 2 条挂那条线的编号。只有确实跨多个部门、且没有单一业务线归属时，才用 `QTSW-006`。例：站会讨论的是某项目的立项与结算 → 挂该项目编号，不是 `QTSW-006`。

编号与用途的对应关系以 `projects` 现拉结果的 `label` 为准。上表是常见锚点，label 与描述冲突时**信 label**。

## 不登记个人业务线映射

每个人的客户线、研发项目、内部立项都不同。照抄别人的映射会系统性挂错项目。按上面四步判断，用客户名现搜。

## 项目 id 不缓存

- `opportunityId` 是数据库 cuid，项目重建就变，缓存必然过期失效。历史事故：照抄缓存 id 写错过工时
- `projectId`（编号，如 `QTSW-002`）相对稳定，作为归口锚点
- 每次由 `scripts/collect.sh` 拉全量池（约 260 条，含 lead / deal / project），按编号从本次结果取 `type` / `id` / `label`

## 检索提示

- **同一客户可能有 10 条以上 lead/deal**。必须按 label 里的项目名和客户全称选准，不能只按客户匹配
- 客户线搜不到专属项目时，先用客户名确认真的没有，再归 `QTSW-002`
- **产品名在 Veyra 里可能拼错**：MorningStar 的 label 写作 `MoringStar`，少一个 n。按正确拼写搜不到时试试错字写法，或用客户名搜
- 一条不捆两个项目。已捆在一起的先拆条，再分别归口

## 填写规则

- 应填基数 = 周期工作日 × 8。Veyra 已自动扣法定节假日（端午周应填 32h 而非 40h）。页面顶部显示应填、已填、缺口
- 5 类项目：销售开拓、探索性投入（售前未转化商机前）、商机（已转正式）、研发（内部立项）、其它事务（`QTSW-*`）
- 加班如实填，8h/天上限已于 2026-07-10 放开

## 底层 API 契约

adapter 位于 `~/.opencli/clis/veyra/`，用 COOKIE strategy 借已登录 Chrome 的 cookie，通过 `page.evaluate` 在登录态页面内 fetch `/api/*`。base_url 默认硬编码公司地址，可用 env `VEYRA_BASE_URL` 覆盖。stdout 是干净 JSON，版本升级提示走 stderr。

### GET /api/timesheets

`?page=<n>&pageSize=100&sortBy=workDate&sortOrder=desc` → `{success, data:{items:[…], total}}`

item：`{id, userName, departmentName, workDate, opportunityType, opportunityId, opportunityProjectId, opportunityProjectName, content, hours, …}`

**分页约束**（2026-08-07 实测，务必遵守）：

- `pageSize` 硬上限 100。传 200/500 仍只回 100 条，`total` 照实返回
- **不支持任何日期过滤参数**。`startDate` / `start` / `workDateStart` 三种命名均被静默忽略，`total` 不变。日期过滤只能在本地做
- 因此必须 `sortOrder=desc` 加翻页，拉取后本地过滤
- ⚠️ 旧 adapter 用 `sortOrder=asc` 拉单页再本地过滤。记录总数超过 100 后，最新数据会落在页外，任何日期范围查询都查不到且不报错。曾把「本周已填 24h」误判为「14h」，差点重复补填。已于 2026-08-07 修复为 desc 翻页

### GET /api/opportunities/select-options

项目池，约 260 条 → `{success, data:[{type:"lead"|"deal"|"project", id, projectId, projectName, customer, label}, …]}`

**`opportunityType` = `type`，`opportunityId` = `id`。**

### POST /api/timesheets

新建，成功 201。body：`{workDate:"YYYY-MM-DD", opportunityType:"project", opportunityId, content, hours}`

- `hours` 是数字。一天多项目发多条。2026-07-10 实测 8h 上限已放开：单条 10h、当天合计 12h 均 201
- 后端从 session 自动补 `userId` / `userName` / `departmentName`，不要手传
- zod 严格：缺 `opportunityType`(enum) 或 `opportunityId`(string) → 400。**它们是两个顶层字段，不是 `opportunityRef` 嵌套对象**
- **没有幂等键。** 写成功但响应丢失时盲目重试会造重复记录，重试前先 `timesheet-list` 核对

### PATCH /api/timesheets/:id

改，已实测 200。body 只含要改的字段（`{workDate?, opportunityType?, opportunityId?, content?, hours?}`，部分更新可用）。改项目时同时给 `opportunityType` 和 `opportunityId`。

### DELETE /api/timesheets/:id

**仍未验证。** 表单操作列有删除，推测走这个端点。基本用不到，改错填用 edit。真要删先拿一条 id 单测确认 2xx。

## 坑

- **不走前端 UI 填**：项目是 React 受控 combobox，`fill` / `type` 设了 value 但不触发搜索和 onChange，下拉不展开，提交 ref 也不对。adapter 一律走 `/api/timesheets`
- **401 时 adapter 静默返回 `[]` 且退出码 0**，无法与"真的没数据"区分。这是 `collect.sh` 把 `veyra doctor` 设为必过检查的原因
- **`timesheet-list` 返回空或缺最近几天时，先怀疑分页**，不是真没填
- `hours` 是数字，区别于旧钉钉多维表的字符串 `"8"`
- COOKIE strategy 借的是 Browser Bridge 所在那个已登录 Chrome 的状态。`opencli doctor` 不通时先 `opencli daemon restart`，再检查扩展是否加载、**那个 profile** 是否登录 Veyra
- adapter 里 `page.evaluate` 注入 content 时用 `JSON.stringify` 包裹，避免引号拆坏 JS
