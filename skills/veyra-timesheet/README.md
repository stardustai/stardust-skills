# Veyra Timesheet Skill

`veyra-timesheet` 用于把一段时间的真实工作活动核对、补齐到「Veyra 睿策」工时系统。核心原则：活动记录能证明你在哪条线上，证明不了你花了几小时——项目归属由证据决定，小时数由用户拍板。仅支持 macOS。

## 适用场景

用户提到以下事项时应使用本 skill：

- 填工时、补工时、核对工时、这周工时
- 收到工时缺口或未达标通报
- 当期含请假、调休、加班

不适用：查考勤打卡（企业未开通）；改他人工时。

## 工作流程

1. **采集**：`scripts/collect.sh` 一次拉取日期范围内的钉钉侧证据（日程、全量消息、AI 听记、日志）和 Veyra 侧数据（项目池、已填记录），`scripts/digest.sh` 压成可读文本。
2. **对账与推断**：逐日与已填记录比对，分为缺填 / 错填 / 已正确三类，避免重复写入；按证据推断每天的项目归属。
3. **提案**：每条小时数给出数值 · 依据 · 置信度，不预设 8 小时，交用户拍板。
4. **写入**：用户确认后按下面的写入契约逐条执行。

## 初始化

```bash
bash scripts/init.sh            # 默认只探测，不改动任何东西
bash scripts/init.sh --install  # 经用户确认后执行安装，幂等可重跑
```

**默认模式零改动**。Agent 先跑探测、把缺失项和将改动的路径（npm 全局、Homebrew、`~/.opencli/`、dws 安装器）告知用户，确认后才跑 `--install`。

四件事需要人工完成：提供公司 Veyra 地址（写入 `~/.opencli/clis/veyra/config.json`，可与登录合并为一步）、Chrome Web Store 安装 OpenCLI Bridge 扩展（脚本会打开商店页）、在挂扩展的那个 Chrome profile 登录 Veyra、`dws auth login` 扫码。

## 数据边界

- 采集物（钉钉消息/听记/日志、Veyra 已填记录与项目池）**只落本机系统临时目录** `$TMPDIR/veyra-timesheet/`，不经任何外部服务，不上传。
- 保留与清理：macOS 会定期自动清理系统临时目录（重启必清）；随时可 `rm -rf "$TMPDIR/veyra-timesheet"` 立即清除。
- skill 目录本身**永不接收任何产物**——bundle、digest、拟改清单都不会写进 skill 目录，因此不可能随仓库同步或提交。
- Veyra 地址属用户配置（`config.json` / env `VEYRA_BASE_URL`），登录态留在用户自己的 Chrome 和 `dws` 里，都不进仓库。

## 写入契约

1. 先提案：拟改清单（新增 / 改 / 不动）连同依据、置信度交用户审阅。
2. **用户明确确认后才允许任何写操作**。
3. 写前立即重拉一次已填基线，与清单核对；对不上就停下重报，不擅自调整。
4. 逐条执行 `timesheet-add` / `timesheet-edit`（改错填用 edit，不删除重填）。
5. 写后回读 `timesheet-list` 复核条数与每日合计，再向用户汇报。
6. 幂等不确定时（超时/响应异常）：**先查后重试**——`POST /api/timesheets` 无幂等键，盲目重试会造成重复记录。

## 依赖

- `dws` CLI：钉钉侧采集
- `opencli` + Browser Bridge 扩展：借已登录 Chrome 的 Veyra 会话（node ≥ 20）
- `jq`：采集脚本依赖（新版 macOS 自带）

细节见 [SKILL.md](./SKILL.md) 与 [references/](./references/)：环境安装（setup.md）、Veyra 改版自愈（repair.md）、API 契约与归口顺序（veyra-api.md）。
