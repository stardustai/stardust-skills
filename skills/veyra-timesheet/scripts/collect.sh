#!/usr/bin/env bash
# 工时填写 — 收集层
#
# 一次性采集一个日期范围内的「钉钉侧」+「Veyra 侧」原始数据，吐一个 bundle。
# 只采集，不推断 —— 推断/对账/小时提案由 Agent 读 digest 完成（见 SKILL.md）。
#
# 与「钉钉日报」的 collect.sh 的区别（别混用）:
#   1. 按**范围**采集而不是逐日循环 —— 所有钉钉源都支持范围查询，一周只需一轮调用，
#      比逐日快数倍（逐日采 2 天就要分钟级）。日期切分交给 digest.sh 按 createTime 做。
#   2. 多采 Veyra 侧（项目池 + 已填工时），少采 todo/oa_pending/top_conversations
#      （待办是未来的事、审批不占工时、置顶只用于标记，对工时无用）。
#
# 用法:
#   collect.sh                          本周一 ~ 今天
#   collect.sh 2026-08-03 2026-08-07    指定范围（含端点）
#   collect.sh 2026-08-03..2026-08-07   同上
#   collect.sh --out-dir DIR            bundle 输出目录（默认 ${TMPDIR:-/tmp}/veyra-timesheet）
#   collect.sh --skip-veyra             只采钉钉侧（Veyra 登录态没恢复时先攒数据用）
#   collect.sh -h|--help
#
# 输出: <out-dir>/timesheet-bundle-<from>_<to>.json，并向 stdout 打印该路径
# bundle 结构:
#   { range:{from,to}, collected_at, my_user_id,
#     veyra:{ projects:[...], filled:[...] },
#     dingtalk:{ calendar, mentions, all_messages, minutes, minutes_attended, report_sent } }
#
# 硬门禁（**不可放宽**）:
#   - dws 未认证 → 退出。
#   - Veyra doctor 非全绿 → 退出。原因: adapter 在 401 时**静默返回 []**、退出码 0，
#     无法与「本周真的一条没填」区分。若放行，Agent 会判定"整周没填"然后重复补填一整周。
set -uo pipefail
export LANG="${LANG:-en_US.UTF-8}" LC_ALL="${LC_ALL:-en_US.UTF-8}"

OUT_DIR="${TMPDIR:-/tmp}/veyra-timesheet"
SKIP_VEYRA=0
ARGS=()

die()  { printf 'collect.sh: %s\n' "$*" >&2; exit 1; }
note() { printf '  [collect] %s\n' "$*" >&2; }
usage(){ sed -n '2,32p' "$0" | sed 's/^# \{0,1\}//'; exit 0; }

valid_date() { [[ "$1" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] && date -j -f "%Y-%m-%d" "$1" "+%F" >/dev/null 2>&1; }

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help)     usage ;;
    --out-dir)     OUT_DIR="${2:?--out-dir 需要目录}"; shift 2 ;;
    --skip-veyra)  SKIP_VEYRA=1; shift ;;
    *..*)          ARGS+=("${1%%..*}" "${1##*..}"); shift ;;
    *)             ARGS+=("$1"); shift ;;
  esac
done

if [ "${#ARGS[@]}" -ge 2 ]; then
  FROM="${ARGS[0]}"; TO="${ARGS[1]}"
elif [ "${#ARGS[@]}" -eq 1 ]; then
  FROM="${ARGS[0]}"; TO="${ARGS[0]}"
else
  # 默认本周一 ~ 今天（date +%u: 周一=1）
  FROM="$(date -j -v-"$(( $(date +%u) - 1 ))"d "+%F")"; TO="$(date +%F)"
fi
valid_date "$FROM" || die "非法日期: '$FROM'（需 YYYY-MM-DD）"
valid_date "$TO"   || die "非法日期: '$TO'（需 YYYY-MM-DD）"
[ "$FROM" \> "$TO" ] && { tmp="$FROM"; FROM="$TO"; TO="$tmp"; }

# ---------- 预检（硬门禁）----------
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INIT="bash $SKILL_DIR/scripts/init.sh"

command -v dws >/dev/null 2>&1 || die "未找到 dws CLI（未安装或不在 PATH）。跑: $INIT"
command -v jq  >/dev/null 2>&1 || die "未找到 jq（采集脚本硬依赖）。跑: $INIT  或 brew install jq"
dws auth status --format json 2>/dev/null | jq -e '.authenticated == true' >/dev/null 2>&1 \
  || die "dws 未认证。跑: dws auth login（需手机钉钉扫码）"

if [ "$SKIP_VEYRA" -eq 0 ]; then
  command -v opencli >/dev/null 2>&1 || die "未找到 opencli（未安装或不在 PATH）。跑: $INIT"
  VDOC="$(opencli veyra doctor -f json 2>/dev/null)"
  if [ -z "$VDOC" ]; then
    # 区分两种原因，否则会误诊。首次使用最常见的是 adapter 根本没装，
    # 而 `opencli doctor` 只查浏览器桥，查不出 adapter 缺失。
    if [ ! -f "$HOME/.opencli/clis/veyra/doctor.js" ]; then
      die "veyra adapter 未安装（$HOME/.opencli/clis/veyra/ 下没有 doctor.js）。跑: $INIT"
    fi
    die "adapter 在位但 veyra doctor 调不通，多为 daemon 未运行或 Chrome 扩展未加载。跑: $INIT --check 看哪一项缺"
  fi
  if printf '%s' "$VDOC" | jq -e 'map(select(.ok == false)) | length > 0' >/dev/null 2>&1; then
    printf '%s\n' "$VDOC" | jq -r '.[] | "    \(.check): \(if .ok then "ok" else "FAIL" end) \(.detail)"' >&2
    die "Veyra doctor 非全绿 —— 401 时 adapter 会静默返回 []，无法与「真的没填」区分，拒绝在此状态下采集。
     登录态失效 → 在挂 Bridge 扩展的 Chrome 里重新登录 Veyra
     端点异常   → 读 references/repair.md 走自愈
     只想先攒钉钉侧数据 → 加 --skip-veyra"
  fi
fi

# ---------- 工具 ----------
# dws 偶发在字符串里输出未转义控制字符 → 先剥掉再喂 jq（保留 \t \n \r）
clean() { LC_ALL=C tr -d '\000-\010\013\014\016-\037'; }
res()   { clean | jq -c '.result // null' 2>/dev/null || echo null; }
run()   { dws "$@" --format json 2>/dev/null | res; }

ISO_FROM="${FROM}T00:00:00+08:00"; ISO_TO="${TO}T23:59:59+08:00"
# list-all 的时间格式是 "yyyy-MM-dd HH:mm:ss"，**不是 ISO-8601**（传 ISO 会返回 0 条）
PLAIN_FROM="${FROM} 00:00:00";     PLAIN_TO="${TO} 23:59:59"

note "范围 $FROM ~ $TO"

# ---------- 身份 ----------
# 需要两个: userId（留档）+ **显示名**。
# 消息里的 .sender 是显示名而不是 userId，所以判断"哪些是我发的"必须拿显示名去比。
# 字段路径是 .result[0].orgEmployeeModel.orgUserName（不是 .result[0].orgUserName —— 那层是 null）。
SELF="$(dws contact user get-self --format json 2>/dev/null | clean)"
ME="$(printf '%s' "$SELF" | jq -r '.result[0].orgEmployeeModel.userId // .result[0].userId // empty' 2>/dev/null)"
MY_NAME="$(printf '%s' "$SELF" | jq -r '.result[0].orgEmployeeModel.orgUserName // empty' 2>/dev/null)"
[ -z "$ME" ] && ME="unknown"
[ -z "$MY_NAME" ] && die "拿不到本人显示名（orgUserName）—— 缺了它无法区分「我发的消息」和别人的，拒绝继续。先跑 dws contact user get-self 排查。"
note "本人：$MY_NAME ($ME)"

# ---------- 钉钉侧 ----------
note "会议日程…"
CALENDAR="$(run calendar event list --start "$ISO_FROM" --end "$ISO_TO")"

note "@我的…"
MENTIONS="$(run chat message list-mentions --start "$ISO_FROM" --end "$ISO_TO" --limit 100)"

note "全量消息（游标翻页，最耗时的一步）…"
ALLMSG="[]"; cursor="0"; page=0
while [ "$page" -lt 40 ]; do
  resp="$(dws chat message list-all --start "$PLAIN_FROM" --end "$PLAIN_TO" \
            --limit 100 --cursor "$cursor" --format json 2>/dev/null | clean)"
  [ -z "$resp" ] && break
  chunk="$(printf '%s' "$resp" | jq -c '.result.conversationMessagesList // []' 2>/dev/null || echo '[]')"
  ALLMSG="$(jq -c -n --argjson a "$ALLMSG" --argjson c "${chunk:-[]}" '$a + $c' 2>/dev/null || echo "$ALLMSG")"
  hasMore="$(printf '%s' "$resp" | jq -r '.result.hasMore // false' 2>/dev/null)"
  cursor="$(printf '%s' "$resp"  | jq -r '.result.nextCursor // empty' 2>/dev/null)"
  page=$((page+1))
  note "  第 $page 页，累计 $(printf '%s' "$ALLMSG" | jq 'length') 个会话"
  { [ "$hasMore" != "true" ] || [ -z "$cursor" ]; } && break
done
[ "$page" -ge 40 ] && note "  ⚠️ 到达 40 页上限，可能未拉完 —— 缩小日期范围重跑"

note "AI 听记（我发起的）…"
# minutes list mine 的 --max 必填；--start/--end 被 API 忽略 → 客户端按 startTime(epoch ms) 筛
FROM_MS=$(( $(date -j -f "%Y-%m-%d %H:%M:%S" "$PLAIN_FROM" +%s 2>/dev/null || echo 0) * 1000 ))
TO_MS=$((   $(date -j -f "%Y-%m-%d %H:%M:%S" "$PLAIN_TO"   +%s 2>/dev/null || echo 0) * 1000 ))
MIN_LIST="$(dws minutes list mine --max 200 --format json 2>/dev/null | clean \
  | jq -c --argjson f "$FROM_MS" --argjson t "$TO_MS" \
    '[.result.minutesDetails[]? | select(((.startTime|tonumber?)//0) >= $f and ((.startTime|tonumber?)//0) <= $t)
      | {taskUuid, title, startTime}]' 2>/dev/null || echo '[]')"
MINUTES="[]"
if [ "$MIN_LIST" != "[]" ] && [ "$MIN_LIST" != "null" ] && [ -n "$MIN_LIST" ]; then
  acc="[]"
  while IFS= read -r tuid; do
    [ -z "$tuid" ] && continue
    sm="$(dws minutes get summary --id "$tuid" --format json 2>/dev/null | clean \
          | jq -c '.result.fullSummary // .result.summary // null' 2>/dev/null || echo null)"
    meta="$(printf '%s' "$MIN_LIST" | jq -c --arg u "$tuid" '.[] | select(.taskUuid==$u)' 2>/dev/null)"
    acc="$(jq -c --argjson meta "${meta:-null}" --argjson sm "${sm:-null}" \
            '. + [($meta + {summary:$sm})]' <<<"$acc" 2>/dev/null || echo "$acc")"
  done <<<"$(printf '%s' "$MIN_LIST" | jq -r '.[].taskUuid')"
  MINUTES="$acc"
fi
note "  我发起的听记 $(printf '%s' "$MINUTES" | jq 'length') 条"

note "AI 听记（别人发起、我参会）…"
# ⚠️ 历史教训: minutes list mine **只返回我发起的**，别人发起我参会的拿不到。
#    从全量消息里抽听记分享链接的 resourceId 补回。漏这一步会丢掉一半听记。
MIN_ATTENDED="[]"
extra_ids="$(printf '%s' "$ALLMSG" | jq -r '[..|.content? // empty]|.[]' 2>/dev/null \
             | grep -oE 'resourceId=[A-Za-z0-9_-]+' | sed 's/resourceId=//' | sort -u | head -40)"
if [ -n "$extra_ids" ]; then
  while IFS= read -r id; do
    [ -z "$id" ] && continue
    esum="$(dws minutes get summary --id "$id" --format json 2>/dev/null | clean \
            | jq -c '.result.fullSummary // .result.summary // null' 2>/dev/null || echo null)"
    { [ "$esum" = "null" ] || [ -z "$esum" ]; } && continue
    MIN_ATTENDED="$(jq -c --arg id "$id" --argjson sm "$esum" \
                     '. + [{resourceId:$id, summary:$sm}]' <<<"$MIN_ATTENDED" 2>/dev/null || echo "$MIN_ATTENDED")"
  done <<<"$extra_ids"
fi
note "  参会听记 $(printf '%s' "$MIN_ATTENDED" | jq 'length') 条"

note "我发的钉钉日志…"
REPORT_SENT="$(run report sent)"

# ---------- Veyra 侧 ----------
PROJECTS="[]"; FILLED="[]"
if [ "$SKIP_VEYRA" -eq 0 ]; then
  note "Veyra 项目池…"
  PROJECTS="$(opencli veyra projects -f json 2>/dev/null | jq -c '. // []' 2>/dev/null || echo '[]')"
  n="$(printf '%s' "$PROJECTS" | jq 'length')"
  # doctor 已全绿仍拿到空池 = 真异常，不能当"池子是空的"往下走
  [ "${n:-0}" -lt 10 ] && die "项目池只有 ${n:-0} 条（正常约 260）。doctor 全绿却拿不到池子，属异常，停下排查。"
  note "  项目池 $n 条"

  note "Veyra 已填工时…"
  FILLED="$(opencli veyra timesheet-list --start "$FROM" --end "$TO" -f json 2>/dev/null | jq -c '. // []' 2>/dev/null || echo '[]')"
  note "  已填 $(printf '%s' "$FILLED" | jq 'length') 条，合计 $(printf '%s' "$FILLED" | jq '[.[].hours // 0]|add // 0') 小时"
else
  note "已跳过 Veyra 侧（--skip-veyra）"
fi

# ---------- 组装 ----------
mkdir -p "$OUT_DIR" || die "无法创建输出目录: $OUT_DIR"
BUNDLE="$OUT_DIR/timesheet-bundle-${FROM}_${TO}.json"

jq -n \
  --arg from "$FROM" --arg to "$TO" --arg me "$ME" --arg myname "$MY_NAME" \
  --arg at "$(date '+%Y-%m-%dT%H:%M:%S%z')" \
  --argjson projects "${PROJECTS:-[]}" --argjson filled "${FILLED:-[]}" \
  --argjson calendar "${CALENDAR:-null}" --argjson mentions "${MENTIONS:-null}" \
  --argjson all_messages "${ALLMSG:-null}" --argjson minutes "${MINUTES:-null}" \
  --argjson minutes_attended "${MIN_ATTENDED:-null}" --argjson report_sent "${REPORT_SENT:-null}" \
  '{range:{from:$from, to:$to}, collected_at:$at, my_user_id:$me, my_name:$myname,
    veyra:{projects:$projects, filled:$filled},
    dingtalk:{calendar:$calendar, mentions:$mentions, all_messages:$all_messages,
              minutes:$minutes, minutes_attended:$minutes_attended, report_sent:$report_sent}}' \
  > "$BUNDLE" || die "组装 bundle 失败"

jq -e '.dingtalk' "$BUNDLE" >/dev/null 2>&1 || die "bundle 不完整: $BUNDLE"
note "完成 → $BUNDLE"
printf '%s\n' "$BUNDLE"
