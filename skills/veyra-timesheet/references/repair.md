# Veyra 改版后修 adapter

`opencli veyra` 依赖 Veyra 的 API 路径、字段结构和登录态。路径改名、字段改名、改成 GraphQL、加鉴权头，都会让命令失效。

adapter 在 `~/.opencli/clis/veyra/`，改完即时生效，不必重启。

> ⚠️ 这件事需要逆向能力。非技术同事应该找维护人，不要自己改——改错会静默写错工时。

## 失效信号

- `timesheet-list` 报错，或返回空但页面上明明有工时
- `timesheet-add` 返回非 201。404 表示路径没了，400 表示字段变了，401 表示登录失效
- `projects` 空或报错

⚠️ **空结果不等于真的没有。** 401 时 adapter 会静默返回 `[]` 且退出码 0。这就是 `collect.sh` 把 `veyra doctor` 设为必过检查的原因——不全绿就拒绝采集，否则会把"登录掉了"当成"整周没填"，然后重复补填。

## 先分清是环境问题还是接口变了

```bash
opencli veyra doctor -f json   # 登录态 / 读端点 / 项目端点
opencli doctor                 # 浏览器桥本身：Daemon / Extension / Connectivity
```

| 现象 | 归属 | 处置 |
|---|---|---|
| 桥不通 | 环境 | `opencli daemon restart`，检查扩展加载。不是 adapter 的事 |
| `auth/me` 401 | 环境 | 在挂 Bridge 扩展的 Chrome 里重登 Veyra。不是 adapter 的事 |
| 桥通、登录也正常，但端点 FAIL | **接口变了** | 往下走 |

## 重新发现接口结构

会话名用 `veyra`，与 adapter 的 domain 共用登录态。

```bash
BASE=https://guance.corpintra.rosettalab.top   # 或你的 VEYRA_BASE_URL

# 页面还在、URL 没变？
opencli browser veyra open "$BASE/timesheets"
opencli browser veyra extract          # 应有应填/已填/缺口和表格列

# 直接问浏览器实际加载了哪些 /api/ 资源，绕过抓包时序
opencli browser veyra eval "JSON.stringify(performance.getEntriesByType('resource').map(e=>e.name).filter(n=>/\/api\//.test(n)))"

# 抓真实请求体，拿新的 method / path / body 形状
opencli browser veyra open "$BASE/timesheets"
opencli browser veyra network --since 40s --all

# 表单字段改名时
opencli browser veyra state | grep -iE 'workDate|opportunity|content|hours|combobox|label'

# 实在认不出
opencli browser veyra analyze "$BASE/timesheets"
```

**写端点字段名变了时**，故意发一个空 body 的 POST，靠 zod 的 400 报错反推必填字段：

```bash
opencli browser veyra eval "(async()=>{const r=await fetch('$BASE/api/timesheets',{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:'{}'});return JSON.stringify({status:r.status,body:(await r.text()).slice(0,500)})})()"
```

400 的 message 会列出「expected one of …」「expected string received undefined」，据此识别缺哪些字段。`opportunityType` 加 `opportunityId` 是两个顶层字段而非嵌套 `opportunityRef`，当初就是这么定出来的。

**只发空或废 body 探测，不要写脏数据。**

## 改哪个文件

| 变化 | 改哪 |
|---|---|
| API 路径变，如 `/api/v2/timesheets` | 各文件里 `fetch('${BASE}/api/...')` 的 path |
| 读字段改名，如 `hours` → `duration` | `timesheet-list.js` 和 `doctor.js` 的解析 key |
| 写字段改名或结构变 | `timesheet-add.js` 和 `timesheet-edit.js` 的 body |
| 项目端点变 | `projects.js` 的 fetch path 和解析 |
| 改成 GraphQL 或需要新 header | 各 `func` 里的 fetch 重写 method / headers / body |
| 只是换环境或测试 | 设 env `VEYRA_BASE_URL`，不必改文件 |

## 改完必跑

```bash
opencli veyra doctor -f json                               # 三项全 ok
opencli veyra timesheet-list --start <周一> --end <周日>    # 能拉到已填
opencli veyra projects -f json | jq length                 # 约 260
```

写端点：先用 `timesheet-add` 写一条可识别的测试工时确认 201，再用 `timesheet-edit` 或在页面上清理。

## 改完之后别漏这三步

1. 把新结构更新到 [veyra-api.md](./veyra-api.md) 的底层 API 契约，避免下次重查
2. **把修好的 adapter 拷回本 skill 的 `references/adapter/`**，否则下一个安装者拿到的还是坏的
3. 通知其他使用者——Veyra 改版会让所有人同时失效

## 原则

adapter 是唯一需要随 Veyra 改版而修改的地方。结构变了就用 `opencli browser` 重新逆向、改 adapter；不退回手工填表，也不在 SKILL.md 里逐次添加临时修复说明。
