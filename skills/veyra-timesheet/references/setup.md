# 装环境

```bash
bash <skill>/scripts/init.sh          # 探测并安装缺失项，可反复跑
bash <skill>/scripts/init.sh --check  # 只探测，不装
```

退出码：`0` 全部就绪 · `10` 有项需人工 · `1` 参数错误。单项失败不会中断脚本，全部检查跑完统一汇总。

输出每行 `KEY  STATUS  detail`。**只处理 STATUS 不是 `ok` / `INSTALLED` / `STARTED` / `FETCHED` 的行。**

实测组合（2026-08-13）：opencli CLI 1.8.4 + Bridge 扩展 v1.0.20。商店版扩展与 release zip 同源；新装后跑 `opencli doctor` 和 `opencli veyra doctor` 确认，行为异常先对版本。

## 脚本自动处理

| KEY | 行为 |
|---|---|
| `OPENCLI` | `npm install -g @jackwener/opencli`（要求 node ≥ 20；缺 npm 时先尝试 `brew install node`）。失败时会打出 npm 真实报错和对应修法，权限问题不要 sudo |
| `ADAPTER` | 复制 `references/adapter/*.js` 到 `~/.opencli/clis/veyra/`。只装缺的，已存在的不覆盖 |
| `DAEMON` | `opencli daemon restart` |
| `JQ` | `brew install jq`。采集脚本硬依赖 |
| `EXTENSION_PKG` | 仅商店不可达时出现：从 GitHub release 下最新 `opencli-extension-v*.zip` 解压到位 |
| `DWS` | 走官方安装脚本 |

## 三件只能人做的事

每完成一项重跑 `init.sh --check` 确认。

### EXTENSION 需要在 Chrome 里装扩展（一次点击）

adapter 靠这个扩展借 Chrome 的登录态。主路径是 Chrome Web Store：

1. `init.sh` 会自动打开商店页；没弹出就手动开
   <https://chromewebstore.google.com/detail/opencli/ildkmabpimmkaediidaifkhjpohdnifk>
2. 点「添加至 Chrome」。**装在登录 Veyra 的那个 Chrome profile 里**——多 profile 机器别装错
3. `opencli daemon restart`，`opencli doctor` 应显示 `[OK] Extension`

商店版自动更新，之后不用手动升级。

#### 商店打不开时（init.sh 自动回落）

`init.sh` 探测不到商店可达时，会从 GitHub release 下 zip 解压到 `~/.opencli/bridge-extension/unpacked/`（对应输出里的 `EXTENSION_PKG` 行），然后人工加载：

1. Chrome 打开 `chrome://extensions`，右上角打开开发者模式
2. 点「加载已解压的扩展程序」，选 `~/.opencli/bridge-extension/unpacked`
3. `opencli daemon restart`

zip 自动获取也失败（无网、API 限流、缺 unzip）时全手工：从 <https://github.com/jackwener/opencli/releases> 下最新 `opencli-extension-v*.zip`，解压内容直接落在上述目录，不要再套一层文件夹。回落版不自动更新：升级 = 重跑 `init.sh` 下新包，再回 `chrome://extensions` 点该扩展的重新加载。`opencli doctor` 提示 `Extension update available` **不是错误**，能连上就不用管。

### VEYRA_LOGIN 需要在那个 Chrome 里登录

**必须是挂着 Bridge 扩展的那个 Chrome 和那个 profile。** 多 profile 的机器最容易在这里踩空——另一个 profile 登录了不算。

让用户打开 base_url（默认 `https://guance.corpintra.rosettalab.top`）正常登录，然后 `opencli veyra doctor -f json` 三项应全 `ok:true`。

登录态会过期。以后采集报 401 就是这个，回到这一步即可，不用重装任何东西。

### DWS 需要扫码

```bash
dws auth login      # OAuth 扫码
dws auth status     # 应为 authenticated
```

要用户拿手机钉钉扫码，代替不了。

## EXTENSION_PKG 与 EXTENSION 是两件事

| KEY | 含义 | 谁做 |
|---|---|---|
| `EXTENSION_PKG` | （仅回落路径）release zip 是否已下载解压到磁盘 | 脚本自动 |
| `EXTENSION` | 扩展有没有装进 Chrome 并连上 daemon | 只能人做：商店一键装，回落时开发者模式加载 |

⚠️ **`npm i -g @jackwener/opencli` 不安装扩展。** npm 包不含扩展文件，`postinstall` 只装 shell 补全。扩展要么从商店装，要么从 GitHub release 下 zip。**新机器上 unpacked 目录不存在**，不要直接让用户去选它。

## ADAPTER DRIFT 要当心

意思是本地某个 adapter 文件与本 skill 携带的版本内容不一致，脚本**没有覆盖**它。两种可能，处置相反：

1. 本地是修过的新版（Veyra 改版后按 [repair.md](./repair.md) 改过）→ 保留本地，并把本地版本拷回本 skill 的 `references/adapter/`
2. 本 skill 是更新过的新版 → 用携带的版本覆盖本地

**别猜，让用户定。** 用 `diff ~/.opencli/clis/veyra/<f>.js <skill>/references/adapter/<f>.js` 把差异摆给他看。

## 常见硬失败

| 症状 | 原因 |
|---|---|
| `npm install -g` 权限报错 | npm 全局目录属 root。建议改 npm prefix 或用 nvm，不要 sudo |
| npm 报 EBADENGINE，或 opencli 装完即崩 | node < 20。`brew upgrade node` 或 `nvm install 20` |
| npm 一直超时 / ENOTFOUND | 国内网络换镜像：`npm config set registry https://registry.npmmirror.com` 后重跑 |
| `opencli doctor` 全绿但 `veyra doctor` 401 | 登录的不是挂扩展那个 Chrome profile |
| 商店和 GitHub release 都打不开 | 换网络或代理；实在不行让能访问的人下好 zip 拷给你，解压到 `~/.opencli/bridge-extension/unpacked/` |
| `veyra doctor` 端点报 404 或 500 而非 401 | Veyra 改版了，读 [repair.md](./repair.md)，不要手填表 |
| 找不到 `jq` | `brew install jq` |

装完跑 `init.sh --check`，看到 `=> 全部就绪` 再回主流程。
