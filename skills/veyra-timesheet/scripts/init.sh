#!/usr/bin/env bash
# 工时填写 skill — 初始化 / 环境探测
#
# 只做确定性动作 + 探测，吐结构化结果给 Agent 读。
# 需要人在 GUI 里完成的三件事（加载 Chrome 扩展 / 登录 Veyra / dws 扫码）本脚本
# 只探测和报告，不代做 —— Agent 按 references/setup.md 引导用户。
#
# 用法:
#   init.sh              只探测，不改动任何东西（默认；--check 同义）
#   init.sh --install    探测 + 安装缺失项（幂等，可反复跑）。会改动：
#                        npm 全局(@jackwener/opencli)、brew(node/jq)、
#                        ~/.opencli/clis/veyra/（adapter 与 config 模板）、
#                        ~/.opencli/bridge-extension/（仅商店不可达时）、
#                        重启 opencli daemon、打开 Chrome 商店页、dws 官方安装脚本。
#                        Agent 必须先跑默认探测，把缺失项和上述改动范围给用户确认后才可用。
#   init.sh -h|--help
#
# 输出契约（每行 "KEY  STATUS  detail"，末尾一行 => 汇总）:
#   OPENCLI        ok|MISSING|INSTALLED     失败不中断其余检查；报错带 npm 真实原因（node 需 >= 20）
#   ADAPTER        ok|INSTALLED|DRIFT       DRIFT = 本地与 bundled 不一致，本脚本不覆盖
#   DAEMON         ok|STARTED|FAIL
#   JQ             ok|INSTALLED|MISSING     collect.sh / digest.sh 硬依赖
#   EXTENSION      ok|MISSING               主路径 = Chrome Web Store 一键装（自动更新），GUI 需人工
#   EXTENSION_PKG  FETCHED|MISSING          仅商店不可达的回落路径出现：release zip 是否到位
#   VEYRA_CONFIG   ok|CREATED|MISSING       Veyra 地址（config.json），真实地址需用户提供
#   VEYRA_LOGIN    ok|MISSING               需人工
#   DWS            ok|MISSING|UNAUTH        UNAUTH 需人工扫码
#   => N 项需人工 / 全部就绪
#
# 退出码: 0 = 全部就绪；10 = 有项需人工；1 = 参数错误
set -uo pipefail
export LANG="${LANG:-en_US.UTF-8}" LC_ALL="${LC_ALL:-en_US.UTF-8}"

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUNDLED_ADAPTER="$SKILL_DIR/references/adapter"
TARGET_ADAPTER="$HOME/.opencli/clis/veyra"
CHECK_ONLY=1   # 默认只探测；--install 才改动机器状态（评审要求：所有变更需显式选择）
NEED_HUMAN=0

case "${1:-}" in
  -h|--help)   sed -n '2,36p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
  --install)   CHECK_ONLY=0 ;;
  --check|"")  ;;
  *)           echo "init.sh: 未知参数 '$1'（试 --help）" >&2; exit 1 ;;
esac

say()  { printf '%-14s %-10s %s\n' "$1" "$2" "${3:-}"; }
human(){ NEED_HUMAN=$((NEED_HUMAN+1)); say "$1" "$2" "$3"; }

# ---------- 1. opencli ----------
# 任何失败都不 exit：JQ / DWS 不依赖 node，剩余检查照跑，最后统一汇总。
# npm 的真实报错必须端出来——吞掉再猜"多为权限问题"只会把人逼回手动排查。
NPM_LOG="$(mktemp -t init-npm)"
trap 'rm -f "$NPM_LOG"' EXIT
npm_diag() {  # 认出三类常见死因给对应修法，认不出就贴原始报错尾部
  if grep -qiE 'EACCES|permission denied' "$NPM_LOG"; then
    echo "npm 全局目录权限问题，不要 sudo：改 npm prefix 或用 nvm"
  elif grep -qiE 'EBADENGINE|unsupported engine' "$NPM_LOG"; then
    echo "node 版本不够（要求 >= 20，当前 $(node -v 2>/dev/null || echo '?')）：brew upgrade node 或 nvm install 20"
  elif grep -qiE 'ETIMEDOUT|ENOTFOUND|ECONNRESET|EAI_AGAIN' "$NPM_LOG"; then
    echo "网络/registry 不通。国内网络可换镜像后重跑：npm config set registry https://registry.npmmirror.com"
  else
    tail -3 "$NPM_LOG" | tr '\n' ' '
  fi
}

if command -v opencli >/dev/null 2>&1; then
  say OPENCLI ok "$(opencli --version 2>/dev/null | head -1)"
elif [ "$CHECK_ONLY" -eq 1 ]; then
  say OPENCLI MISSING "未安装（默认只探测；用户确认后跑 init.sh --install）"
else
  if ! command -v npm >/dev/null 2>&1; then
    echo "  [init] 未找到 npm，先装 Node.js…" >&2
    if command -v brew >/dev/null 2>&1 && brew install node >"$NPM_LOG" 2>&1 && command -v npm >/dev/null 2>&1; then
      echo "  [init] Node.js $(node -v 2>/dev/null) 就绪" >&2
    else
      human OPENCLI MISSING "缺 Node.js（需 >= 20）且自动安装失败。人工：brew install node 或从 https://nodejs.org 装 LTS，再重跑 init.sh"
    fi
  fi
  if command -v npm >/dev/null 2>&1; then
    NODE_MAJOR="$(node -v 2>/dev/null | sed 's/^v//; s/\..*//')"
    if [ "${NODE_MAJOR:-0}" -lt 20 ] 2>/dev/null; then
      human OPENCLI MISSING "node $(node -v 2>/dev/null) < 20，opencli 装上也跑不动。人工：brew upgrade node 或 nvm install 20，再重跑 init.sh"
    else
      echo "  [init] 安装 opencli…" >&2
      if npm install -g @jackwener/opencli >"$NPM_LOG" 2>&1 && command -v opencli >/dev/null 2>&1; then
        say OPENCLI INSTALLED "$(opencli --version 2>/dev/null | head -1)"
      else
        human OPENCLI MISSING "npm install -g @jackwener/opencli 失败：$(npm_diag)"
      fi
    fi
  fi
fi

# ---------- 2. adapter ----------
# 纪律: 不存在才装；已存在则比对，不同只报 DRIFT，绝不覆盖。
# 理由: 本地那份可能已被 references/repair.md 的自愈流程改过。
adapter_state() {
  local drift=0 missing=0 f base
  for f in "$BUNDLED_ADAPTER"/*.js; do
    base="$(basename "$f")"
    if [ ! -f "$TARGET_ADAPTER/$base" ]; then
      missing=$((missing+1))
    elif ! cmp -s "$f" "$TARGET_ADAPTER/$base"; then
      drift=$((drift+1))
    fi
  done
  echo "$missing $drift"
}

read -r A_MISSING A_DRIFT <<<"$(adapter_state)"
if [ "$A_MISSING" -eq 0 ] && [ "$A_DRIFT" -eq 0 ]; then
  say ADAPTER ok "$(ls -1 "$TARGET_ADAPTER"/*.js 2>/dev/null | wc -l | tr -d ' ') files"
elif [ "$CHECK_ONLY" -eq 1 ]; then
  say ADAPTER MISSING "缺 $A_MISSING 个，drift $A_DRIFT 个（--install 会复制缺失项，绝不覆盖）"
else
  mkdir -p "$TARGET_ADAPTER"
  copied=0
  for f in "$BUNDLED_ADAPTER"/*.js; do
    base="$(basename "$f")"
    [ -f "$TARGET_ADAPTER/$base" ] || { cp "$f" "$TARGET_ADAPTER/$base"; copied=$((copied+1)); }
  done
  # 配置模板一并放入（不覆盖已有文件；config.json 是用户数据，绝不动）
  [ -f "$TARGET_ADAPTER/config.example.json" ] || cp "$BUNDLED_ADAPTER/config.example.json" "$TARGET_ADAPTER/" 2>/dev/null || true
  if [ "$A_DRIFT" -gt 0 ]; then
    say ADAPTER DRIFT "新装 $copied 个；另有 $A_DRIFT 个与 bundled 不一致，**未覆盖**（可能是本地自愈改动，请人工比对 $TARGET_ADAPTER）"
    NEED_HUMAN=$((NEED_HUMAN+1))
  else
    say ADAPTER INSTALLED "新装 $copied 个"
  fi
fi

# ---------- 3. daemon ----------
if ! command -v opencli >/dev/null 2>&1; then
  say DAEMON FAIL "opencli 未装；OPENCLI 解决后重跑 init.sh"
elif opencli doctor 2>/dev/null | grep -q '\[OK\] Daemon'; then
  say DAEMON ok
elif [ "$CHECK_ONLY" -eq 1 ]; then
  say DAEMON FAIL "未运行（--install 会 opencli daemon restart）"
else
  opencli daemon restart >/dev/null 2>&1
  sleep 2
  if opencli doctor 2>/dev/null | grep -q '\[OK\] Daemon'; then
    say DAEMON STARTED
  else
    say DAEMON FAIL "opencli daemon restart 后仍未就绪"
  fi
fi

# ---------- 4. jq（采集脚本硬依赖）----------
if command -v jq >/dev/null 2>&1; then
  say JQ ok "$(jq --version 2>/dev/null)"
elif [ "$CHECK_ONLY" -eq 1 ]; then
  say JQ MISSING "collect.sh / digest.sh 都要它（--install 会 brew install jq）"
elif command -v brew >/dev/null 2>&1 && brew install jq >/dev/null 2>&1; then
  say JQ INSTALLED "$(jq --version 2>/dev/null)"
else
  human JQ MISSING "人工：brew install jq（collect.sh / digest.sh 硬依赖）"
fi

# ---------- 5. Browser Bridge 扩展 ----------
# 主路径：Chrome Web Store 一键安装（上游 README 的推荐路径 Option A，自动更新）。
# 回落：商店不可达（无代理的内网/国内网络）时，从 GitHub release 下 zip 走
#       开发者模式加载。**npm 包不含扩展文件**，postinstall 只装 shell 补全。
# 早期版本把回落当唯一路径实现，七步手工劝退过真实同事。
STORE_URL="https://chromewebstore.google.com/detail/opencli/ildkmabpimmkaediidaifkhjpohdnifk"
EXT_DIR="$HOME/.opencli/bridge-extension/unpacked"
ext_ver() { jq -r '.version // "?"' "$EXT_DIR/manifest.json" 2>/dev/null || echo '?'; }

if command -v opencli >/dev/null 2>&1 && opencli doctor 2>/dev/null | grep -q '\[OK\] Extension'; then
  say EXTENSION ok "已加载并连上 daemon"
elif [ -f "$EXT_DIR/manifest.json" ]; then
  # zip 已在磁盘（走过回落路径）：就近引导装完，不再绕商店
  human EXTENSION MISSING "扩展文件已在磁盘（v$(ext_ver)）。人工：chrome://extensions → 开发者模式 → 加载已解压 → ${EXT_DIR}，然后 opencli daemon restart；也可改装商店版 ${STORE_URL}"
elif [ "$CHECK_ONLY" -eq 1 ]; then
  human EXTENSION MISSING "人工：Chrome Web Store 一键安装 ${STORE_URL}（装在登录 Veyra 的那个 profile）。商店打不开时 --install 模式会走 zip 回落"
elif curl -fsSL -o /dev/null --max-time 8 "$STORE_URL" 2>/dev/null; then
  open -a "Google Chrome" "$STORE_URL" >/dev/null 2>&1 || open "$STORE_URL" >/dev/null 2>&1 || true
  human EXTENSION MISSING "人工：已打开商店页，点「添加至 Chrome」（装在登录 Veyra 的那个 profile），然后 opencli daemon restart。页面没弹出就手动开 ${STORE_URL}"
else
  # ── 商店不可达 → 回落：GitHub release 下 zip ──
  if ! command -v jq >/dev/null 2>&1 || ! command -v unzip >/dev/null 2>&1; then
    human EXTENSION_PKG MISSING "商店不可达且缺 jq 或 unzip。人工：从 https://github.com/jackwener/opencli/releases 下 opencli-extension-v*.zip 解压到 ${EXT_DIR}/"
    human EXTENSION MISSING "拿到扩展文件后：chrome://extensions → 开发者模式 → 加载已解压 → ${EXT_DIR}"
  else
    echo "  [init] 商店不可达，回落：从 GitHub release 获取扩展…" >&2
    # release 按时间倒序返回，展平后第一个 opencli-extension-*.zip 就是最新的
    ASSET_URL="$(curl -fsSL "https://api.github.com/repos/jackwener/opencli/releases?per_page=20" 2>/dev/null \
      | jq -r '[.[].assets[]? | select(.name | test("^opencli-extension-v.*\\.zip$"))] | .[0].browser_download_url // empty' 2>/dev/null)"
    if [ -z "$ASSET_URL" ]; then
      human EXTENSION_PKG MISSING "商店与 release 均不可达（网络？限流？）。人工：https://github.com/jackwener/opencli/releases 下 opencli-extension-v*.zip 解压到 ${EXT_DIR}/"
      human EXTENSION MISSING "拿到扩展文件后：chrome://extensions → 开发者模式 → 加载已解压 → ${EXT_DIR}"
    else
      TMPZ="$(mktemp -t opencli-ext).zip"
      if curl -fsSL -o "$TMPZ" "$ASSET_URL" 2>/dev/null \
         && mkdir -p "$EXT_DIR" \
         && unzip -oq "$TMPZ" -d "$EXT_DIR" 2>/dev/null \
         && [ -f "$EXT_DIR/manifest.json" ]; then
        say EXTENSION_PKG FETCHED "v$(ext_ver) ← $(basename "$ASSET_URL")"
        human EXTENSION MISSING "人工：chrome://extensions → 开发者模式 → 加载已解压 → ${EXT_DIR}，然后 opencli daemon restart"
      else
        human EXTENSION_PKG MISSING "下载或解压失败。人工：$ASSET_URL → 解压到 ${EXT_DIR}/"
        human EXTENSION MISSING "拿到扩展文件后：chrome://extensions → 开发者模式 → 加载已解压 → ${EXT_DIR}"
      fi
      rm -f "$TMPZ"
    fi
  fi
fi

# ---------- 6. Veyra 地址配置 ----------
# 地址不随 skill 分发（公开仓库不放内网信息），真实地址只能用户给：
# Agent 问「平时填工时的网站地址」写入 config.json；env VEYRA_BASE_URL 可临时覆盖。
VEYRA_CFG="$TARGET_ADAPTER/config.json"
cfg_url() { jq -r '.veyra_base_url // empty' "$VEYRA_CFG" 2>/dev/null; }
CFG_OK=0
if [ -n "${VEYRA_BASE_URL:-}" ]; then
  CFG_OK=1; say VEYRA_CONFIG ok "env VEYRA_BASE_URL 已设置（覆盖 config.json）"
elif [ -f "$VEYRA_CFG" ] && ! grep -q '<' "$VEYRA_CFG" 2>/dev/null && [ -n "$(cfg_url)" ]; then
  CFG_OK=1; say VEYRA_CONFIG ok "$(cfg_url)"
elif [ "$CHECK_ONLY" -eq 0 ] && [ ! -f "$VEYRA_CFG" ] && [ -f "$BUNDLED_ADAPTER/config.example.json" ]; then
  mkdir -p "$TARGET_ADAPTER" && cp "$BUNDLED_ADAPTER/config.example.json" "$VEYRA_CFG"
  human VEYRA_CONFIG CREATED "已建 ${VEYRA_CFG}（占位符）。人工：问用户要平时填工时的网站地址，替换占位符"
else
  human VEYRA_CONFIG MISSING "人工：问用户要平时填工时的网站地址，写入 ${VEYRA_CFG}（格式: {\"veyra_base_url\":\"https://…\"}）"
fi

# ---------- 7. Veyra 登录态（人工）----------
# 用 adapter 自带的 doctor 判定；它一次测登录态 + 读端点 + 项目端点。
VEYRA_URL="${VEYRA_BASE_URL:-$(cfg_url)}"
case "$VEYRA_URL" in ''|*'<'*) VEYRA_URL="你平时填工时的 Veyra 网站" ;; esac
if ! command -v opencli >/dev/null 2>&1; then
  human VEYRA_LOGIN MISSING "OPENCLI 装好后：在挂 Bridge 扩展的那个 Chrome 里登录 ${VEYRA_URL}，跑 opencli veyra doctor 验证"
elif [ "$CFG_OK" -eq 0 ]; then
  human VEYRA_LOGIN MISSING "待 VEYRA_CONFIG 配好后：在挂 Bridge 扩展的那个 Chrome 里登录该地址，跑 opencli veyra doctor 验证"
else
  VEYRA_DOC="$(opencli veyra doctor -f json 2>/dev/null)"
  if [ -n "$VEYRA_DOC" ] && ! printf '%s' "$VEYRA_DOC" | grep -q '"ok": *false'; then
    say VEYRA_LOGIN ok
  else
    detail="$(printf '%s' "$VEYRA_DOC" | grep -A1 '">> 诊断"' | grep '"detail"' | sed 's/.*"detail": *"//; s/".*//')"
    # 注意: 全角括号的字节 >= 0x80，紧跟在 $var 后会被 bash 当成变量名的一部分 →
    # 变量引用一律加花括号 ${var}，否则 set -u 下报 "unbound variable"。
    human VEYRA_LOGIN MISSING "人工：在挂着 Bridge 扩展的那个 Chrome 里登录 ${VEYRA_URL}${detail:+（doctor: ${detail}）}"
  fi
fi

# ---------- 8. dws ----------
if ! command -v dws >/dev/null 2>&1; then
  if [ "$CHECK_ONLY" -eq 1 ]; then
    say DWS MISSING "未安装（--install 会走官方安装脚本）"
  else
    echo "  [init] 安装 dws…" >&2
    if curl -fsSL https://raw.githubusercontent.com/DingTalk-Real-AI/dingtalk-workspace-cli/main/scripts/install.sh | sh >/dev/null 2>&1 \
       && command -v dws >/dev/null 2>&1; then
      human DWS UNAUTH "已安装。人工：跑 dws auth login 扫码"
    else
      human DWS MISSING "自动安装失败。人工：curl -fsSL https://raw.githubusercontent.com/DingTalk-Real-AI/dingtalk-workspace-cli/main/scripts/install.sh | sh"
    fi
  fi
elif dws auth status --format json 2>/dev/null | grep -q '"authenticated": *true'; then
  say DWS ok "$(dws --version 2>/dev/null | head -1)"
else
  human DWS UNAUTH "人工：跑 dws auth login 扫码"
fi

# ---------- 汇总 ----------
if [ "$NEED_HUMAN" -eq 0 ]; then
  echo "=> 全部就绪"
  exit 0
else
  echo "=> $NEED_HUMAN 项需人工，读 references/setup.md"
  exit 10
fi
