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
4. **写入**：用户确认后先重拉基线核对，再走 `opencli veyra timesheet-add / timesheet-edit` 逐条执行，写完复核。

## 初始化

```bash
bash scripts/init.sh          # 探测并安装缺失项，幂等可重跑
bash scripts/init.sh --check  # 只探测不安装
```

三件事需要人工完成：Chrome Web Store 安装 OpenCLI Bridge 扩展（脚本会自动打开商店页）、在挂扩展的那个 Chrome profile 登录 Veyra、`dws auth login` 扫码。`--check` 显示全部就绪后正常使用。

## 依赖

- `dws` CLI：钉钉侧采集
- `opencli` + Browser Bridge 扩展：借已登录 Chrome 的 Veyra 会话（node ≥ 20）
- `jq`：采集脚本依赖（新版 macOS 自带）

细节见 [SKILL.md](./SKILL.md) 与 [references/](./references/)：环境安装（setup.md）、Veyra 改版自愈（repair.md）、API 契约与归口顺序（veyra-api.md）。
