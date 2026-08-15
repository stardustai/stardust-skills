#!/usr/bin/env bash
# 工时填写 — bundle → digest
#
# 把 collect.sh 的 bundle 压成可读文本，供 Agent 做推断 / 对账 / 小时提案。
#
# 与「钉钉日报」digest.sh 的切面不同（别混用）:
#   日报按会话组织，为的是还原一天的故事；
#   本脚本按 **日期 × 会话/线索** 组织，为的是判断"这天精力分布在哪几条线"。
#   会话名在钉钉里通常就是项目名（"[商机]Subway知识库"、"华为xx高质量数据集项目"），
#   所以会话是"线索"的可观测代理。**最终挂哪个 Veyra 项目是 Agent 的判断，脚本不猜。**
#
# ⚠️ "我发的消息"靠 bundle 里的 my_name（本人显示名）匹配 .sender —— .sender 是显示名而非
#    userId。不要在脚本里硬编码任何人名。
#
# 用法: digest.sh <bundle.json>
set -uo pipefail
export LANG="${LANG:-en_US.UTF-8}" LC_ALL="${LC_ALL:-en_US.UTF-8}"
B="${1:?用法: digest.sh <bundle.json>}"
[ -f "$B" ] || { echo "digest.sh: 找不到 bundle: $B" >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "digest.sh: 未找到 jq" >&2; exit 1; }

ME_ID="$(jq -r '.my_user_id // "?"' "$B")"
MY_NAME="$(jq -r '.my_name // ""' "$B")"
FROM="$(jq -r '.range.from' "$B")"; TO="$(jq -r '.range.to' "$B")"
[ -n "$MY_NAME" ] || { echo "digest.sh: bundle 缺 my_name，无法区分「我发的消息」。用新版 collect.sh 重采。" >&2; exit 1; }

echo "# TIMESHEET DIGEST  $FROM ~ $TO"
echo "  本人: $MY_NAME ($ME_ID)   采集于: $(jq -r '.collected_at // "?"' "$B")"

# ─────────────────────────── Veyra 已填 ───────────────────────────
echo
echo "## Veyra 已填（对账基线）"
jq -r '
  (.veyra.filled // []) as $f
  | if ($f|length) == 0 then
      "  —（范围内一条未填）",
      "  ⚠️ 仅当 collect.sh 是在 veyra doctor 全绿下跑的，这才等于「真的没填」。"
    else
      ( $f | group_by(.workDate) | .[] |
        "  \(.[0].workDate)   合计 \([.[].hours // 0]|add)h",
        ( .[] | "        \(.hours)h  [\(.project // "?")]  \(.content // "" | tostring | gsub("\n";" ") | .[0:88])   id=\(.id)" )
      ),
      "  ── 范围合计 \([$f[].hours // 0]|add)h / \($f|length) 条"
    end
' "$B"

# ─────────────────────────── 逐日 ───────────────────────────
echo
echo "## 逐日（判断哪天在岗、精力在哪条线）"

DAYS="$(jq -r '
  def d(x): (x // "") | tostring | .[0:10];
  ( [ (.dingtalk.calendar.events // [])[] | d(.start.dateTime // .start.date) ]
  + [ (.dingtalk.all_messages // [])[] | (.messages // [])[] | d(.createTime) ]
  + [ (.dingtalk.minutes // [])[] | (((.startTime|tonumber)/1000 + 28800) | floor | strftime("%Y-%m-%d")) ]
  + [ (.veyra.filled // [])[] | .workDate ]
  ) | map(select(. != null and . != "" and (tostring|test("^[0-9]{4}-[0-9]{2}-[0-9]{2}$"))))
    | unique | sort | .[]
' "$B")"

if [ -z "$DAYS" ]; then
  echo "  —（范围内没有任何活动信号）"
else
  while IFS= read -r day; do
    [ -z "$day" ] && continue
    printf '\n### %s (%s)\n' "$day" "$(date -j -f "%Y-%m-%d" "$day" "+%a" 2>/dev/null || echo '?')"
    jq -r --arg day "$day" --arg me "$MY_NAME" '
      def d(x): (x // "") | tostring | .[0:10];
      # 听记 summary 里混着 ![图片](超长OSS URL) 和 <time data-ts=...> 标签，纯噪音，先剥掉
      def strip: (. // "") | tostring
                 | gsub("!\\[[^\\]]*\\]\\([^)]*\\)"; "")
                 | gsub("<[^>]*>"; "")
                 | gsub("\n";" ") | gsub(" +";" ");
      def clip(x;n): (x // "") | tostring | gsub("\n";" ") | .[0:n];
      def clips(x;n): (x | strip) | .[0:n];
      def hhmm(x): (x // "") | tostring | .[11:16];
      def mine: ((.sender // "") | tostring) as $s | ($s == $me or ($s|startswith($me)));

        [ (.dingtalk.calendar.events // [])[] | select(d(.start.dateTime // .start.date) == $day) ] as $mt
      | [ (.dingtalk.minutes // [])[]
          | select((((.startTime|tonumber)/1000 + 28800)|floor|strftime("%Y-%m-%d")) == $day) ] as $mn
      | [ (.dingtalk.all_messages // [])[] | (.title // "(无标题)") as $c | (.messages // [])[]
          | select(d(.createTime) == $day)
          | {c:$c, sender:(.sender // "?"), content:.content, t:hhmm(.createTime)} ] as $msg
      | [ (.veyra.filled // [])[] | select(.workDate == $day) ] as $fl
      | [ $mt[] | select(((.summary // "")|tostring) | test("请假|调休|年假|病假|事假|年休|休假")) ] as $leave
      | [ $msg[] | select(mine) ] as $my
      | (
          "  会议 \($mt|length) · 听记 \($mn|length) · 消息 \($msg|length)（我发 \($my|length)）· 会话 \([$msg[].c]|unique|length) · Veyra已填 \([$fl[].hours//0]|add // 0)h",

          ( if ($leave|length) > 0
            then "  🏖 请假信号（真值仍以钉钉审批为准）: " + ([$leave[].summary]|join(" / "))
            else empty end ),

          ( if ($mt|length) > 0
            then "  会议:",
                 ( $mt[] | "    - \(hhmm(.start.dateTime // .start.date))  \(clip(.summary;66))  \((.attendees//[])|length)人" )
            else empty end ),

          ( if ($mn|length) > 0
            then "  听记:",
                 ( $mn[] | "    - 【\(clip(.title;60))】", "        \(clips(.summary;600))" )
            else empty end ),

          ( if ($msg|length) > 0
            then "  会话活动（按条数倒序，⚑ = 我有发言）:",
                 ( $msg | group_by(.c) | sort_by(-length) | .[]
                   | ([ .[] | select(mine) ]) as $m
                   | "    \(if ($m|length) > 0 then "⚑" else "·" end) \(.[0].c)  [\(length)条\(if ($m|length) > 0 then "，我 \($m|length)" else "" end)]",
                     ( if ($m|length) > 0
                       then "        " + ([ $m[] | "\(.t) \(clip(.content;58))" ] | .[0:5] | join("  ｜  "))
                       else empty end ) )
            else empty end )
        )
    ' "$B"
  done <<<"$DAYS"
fi

# ─────────────────────────── 其余区块 ───────────────────────────
echo
echo "## @我的（别人交办 → 常对应一条工时）"
jq -r '
  def t(x): (x // "") | tostring | gsub("\n";" ") | .[0:140];
  (.dingtalk.mentions.conversationMessagesList // [])
  | if length == 0 then "  —" else
      ( [ .[] | (.title // "?") as $c | (.messages // [])[] | {c:$c, ts:((.createTime // "")|tostring|.[0:16]), s:(.sender // "?"), m:.content} ]
        | sort_by(.ts) | .[]
        | "  - [\(.ts)] [\(.c)] \(.s): \(t(.m))" )
    end
' "$B"

echo
echo "## 我发的钉钉日志（最直接的自述）"
jq -r '
  (.dingtalk.report_sent.report_list // [])
  | if length == 0 then "  —" else
      (.[] | "  - \(.title // .templateName // "日报") (\(.createTime // .gmtCreate // "?"))") end
' "$B"

echo
echo "## 参会听记（别人发起、我参会 —— 漏了就丢一半听记）"
jq -r '
  def strip: (. // "") | tostring
             | gsub("!\\[[^\\]]*\\]\\([^)]*\\)"; "")
             | gsub("<[^>]*>"; "")
             | gsub("\n";" ") | gsub(" +";" ");
  (.dingtalk.minutes_attended // [])
  | if length == 0 then "  —" else (.[] | "  - \((.summary|strip)[0:500])") end
' "$B"

echo
echo "## Veyra 项目池（挂项目**只能**从这里取 label；凭印象补 id/名称 = 返工）"
jq -r '
  (.veyra.projects // []) as $p
  | if ($p|length) == 0 then "  —（未采集或采集失败。不要凭印象补 —— 重采后再挂项目）" else
      "  共 \($p|length) 条。格式: type | id | projectId | label",
      "  ── 通用锚点（兜底 / 休假 / 其它事务）──",
      ( $p[] | select((.projectId // "" | tostring) | test("^(QTSW-|假期-)")) | "  \(.type) | \(.id) | \(.projectId) | \(.label)" ),
      "  ── 全量 ──",
      ( $p[] | "  \(.type) | \(.id) | \(.projectId) | \(.label)" )
    end
' "$B"
