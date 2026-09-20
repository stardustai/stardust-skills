#!/usr/bin/env bash
set -euo pipefail

skill_dir="$(cd "$(dirname "$0")/.." && pwd)"
scanner="$skill_dir/scripts/scan_and_retry_sessions.py"
tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/codex-session-retry-test.XXXXXX")"
trap 'rm -rf "$tmp_dir"' EXIT

session_root="$tmp_dir/sessions"
mkdir -p "$session_root/2026/09/20"
session_file="$session_root/2026/09/20/rollout-test.jsonl"
state_file="$tmp_dir/state.json"
counter_file="$tmp_dir/counter"
args_file="$tmp_dir/args"
session_id="019ed90c-3b33-7922-92ad-6e61d74ca9c6"
printf '%s\n' 0 > "$counter_file"

printf '%s\n' '{"type":"session_meta","payload":{"id":"019ed90c-3b33-7922-92ad-6e61d74ca9c6"}}' > "$session_file"
printf '%s\n' '{"timestamp":"2026-09-20T09:09:44.000Z","ordinal":10,"type":"event_msg","payload":{"type":"task_complete","last_agent_message":null,"error":{"message":"Selected model is at capacity. Please try a different model.","codex_error_info":"server_overloaded"}}}' >> "$session_file"

fake_codex="$tmp_dir/fake-codex.sh"
cat > "$fake_codex" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" > "$FAKE_CODEX_ARGS"
attempt=$(( $(<"$FAKE_CODEX_COUNTER") + 1 ))
printf '%s\n' "$attempt" > "$FAKE_CODEX_COUNTER"
printf '%s\n' '{"type":"turn.completed","usage":{"output_tokens":1}}'
printf '%s\n' "{\"timestamp\":\"2026-09-20T09:10:0${attempt}.000Z\",\"ordinal\":$((10 + attempt)),\"type\":\"event_msg\",\"payload\":{\"type\":\"task_complete\",\"message\":\"resumed successfully\"}}" >> "$FAKE_SESSION_FILE"
EOF
chmod +x "$fake_codex"

output="$(FAKE_CODEX_COUNTER="$counter_file" FAKE_CODEX_ARGS="$args_file" FAKE_SESSION_FILE="$session_file" \
  python3 "$scanner" --once --session-root "$session_root" --state-file "$state_file" \
  --codex-bin "$fake_codex" --queue-bin "$fake_codex" --retry-delay-seconds 0 --max-age-seconds 0)"

[[ "$output" == *"$session_id"* ]]
[[ "$(<"$counter_file")" == 1 ]]
[[ "$(<"$args_file")" == *"exec resume --json --skip-git-repo-check $session_id"* ]]
[[ "$(<"$args_file")" != *"model_reasoning_effort"* ]]
[[ "$(<"$args_file")" != *"--model"* ]]
[[ "$(tail -n 1 "$session_file")" == *"resumed successfully"* ]]

python3 "$scanner" --once --session-root "$session_root" --state-file "$state_file" \
  --codex-bin "$fake_codex" --retry-delay-seconds 0 --max-age-seconds 0 >/dev/null
[[ "$(<"$counter_file")" == 1 ]]
echo "existing-session scanner test passed"

desktop_session_file="$session_root/2026/09/20/rollout-desktop.jsonl"
desktop_state_file="$tmp_dir/desktop-state.json"
desktop_session_id="019ed90c-3b33-7922-bc18-4f83044ba267"
printf '%s\n' "{\"type\":\"session_meta\",\"payload\":{\"id\":\"$desktop_session_id\"}}" > "$desktop_session_file"
printf '%s\n' '{"timestamp":"2026-09-20T09:11:44.000Z","ordinal":10,"type":"event_msg","payload":{"type":"task_complete","last_agent_message":null,"error":{"message":"Selected model is at capacity. Please try a different model.","codex_error_info":"server_overloaded"}}}' >> "$desktop_session_file"

desktop_codex="$tmp_dir/desktop-codex.sh"
cat > "$desktop_codex" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$DESKTOP_CALLS"
if [[ "$1 $2 $3" == "exec resume --json" ]]; then
  printf '%s\n' 'Error: thread/resume: thread/resume failed: thread-store conflict: thread already has an active writer' >&2
  exit 1
fi
[[ "$1 $2" == "queue --thread" ]]
EOF
chmod +x "$desktop_codex"
desktop_calls="$tmp_dir/desktop-calls"
desktop_output="$(DESKTOP_CALLS="$desktop_calls" python3 "$scanner" --once --session-root "$session_root" \
  --state-file "$desktop_state_file" --codex-bin "$desktop_codex" --queue-bin "$desktop_codex" \
  --retry-delay-seconds 0 --max-age-seconds 0 2>&1)"
[[ "$desktop_output" == *"Desktop-owned"* ]]
[[ "$(wc -l < "$desktop_calls")" == 2 ]]
[[ "$(sed -n '1p' "$desktop_calls")" == *"exec resume --json $desktop_session_id"* ]]
[[ "$(sed -n '2p' "$desktop_calls")" == *"queue --thread $desktop_session_id"* ]]
[[ "$(sed -n '2p' "$desktop_calls")" != *"--model"* ]]
echo "desktop-owned same-thread queue test passed"

repeat_file="$session_root/2026/09/20/rollout-repeat.jsonl"
repeat_state="$tmp_dir/repeat-state.json"
repeat_id="019ed90c-3b33-7922-92ad-6e61d74ca9d0"
printf '%s\n' "{\"type\":\"session_meta\",\"payload\":{\"id\":\"$repeat_id\"}}" > "$repeat_file"
printf '%s\n' '{"timestamp":"2026-09-20T09:12:44.000Z","ordinal":1,"type":"event_msg","payload":{"type":"task_complete","error":{"message":"429 model at capacity"}}}' >> "$repeat_file"
printf '%s\n' 0 > "$counter_file"
FAKE_CODEX_COUNTER="$counter_file" FAKE_CODEX_ARGS="$args_file" FAKE_SESSION_FILE="$repeat_file" \
  python3 "$scanner" --once --session-root "$session_root" --state-file "$repeat_state" \
  --codex-bin "$fake_codex" --retry-delay-seconds 0 --max-age-seconds 0 >/dev/null
printf '%s\n' '{"timestamp":"2026-09-20T09:12:45.000Z","ordinal":2,"type":"event_msg","payload":{"type":"task_complete","error":{"message":"429 model at capacity"}}}' >> "$repeat_file"
FAKE_CODEX_COUNTER="$counter_file" FAKE_CODEX_ARGS="$args_file" FAKE_SESSION_FILE="$repeat_file" \
  python3 "$scanner" --once --session-root "$session_root" --state-file "$repeat_state" \
  --codex-bin "$fake_codex" --retry-delay-seconds 0 --max-age-seconds 0 >/dev/null
[[ "$(<"$counter_file")" == 2 ]]
echo "new-capacity-failure retry test passed"

history_root="$tmp_dir/history-sessions"
history_state="$tmp_dir/history-state.json"
history_counter="$tmp_dir/history-counter"
history_id="019ed90c-3b33-7922-92ad-6e61d74ca9d1"
mkdir -p "$history_root"
history_old="$history_root/rollout-old.jsonl"
history_new="$history_root/rollout-new.jsonl"
printf '%s\n' "{\"type\":\"session_meta\",\"payload\":{\"id\":\"$history_id\"}}" > "$history_old"
printf '%s\n' '{"timestamp":"2026-09-20T09:14:00.000Z","ordinal":10,"type":"event_msg","payload":{"type":"task_complete","error":{"message":"429 model at capacity"}}}' >> "$history_old"
printf '%s\n' "{\"type\":\"session_meta\",\"payload\":{\"id\":\"$history_id\"}}" > "$history_new"
printf '%s\n' '{"timestamp":"2026-09-20T09:14:01.000Z","ordinal":11,"type":"event_msg","payload":{"type":"task_started","turn_id":"new-turn"}}' >> "$history_new"
printf '%s\n' 0 > "$history_counter"
history_codex="$tmp_dir/history-codex.sh"
cat > "$history_codex" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
attempt=$(( $(<"$HISTORY_COUNTER") + 1 ))
printf '%s\n' "$attempt" > "$HISTORY_COUNTER"
EOF
chmod +x "$history_codex"
HISTORY_COUNTER="$history_counter" python3 "$scanner" --once --session-root "$history_root" \
  --state-file "$history_state" --codex-bin "$history_codex" --retry-delay-seconds 0 --max-age-seconds 0 >/dev/null
[[ "$(<"$history_counter")" == 0 ]]
echo "historical rollout suppression test passed"

excluded_state="$tmp_dir/excluded-state.json"
excluded_counter="$tmp_dir/excluded-counter"
printf '%s\n' 0 > "$excluded_counter"
HISTORY_COUNTER="$excluded_counter" python3 "$scanner" --once --session-root "$session_root" \
  --state-file "$excluded_state" --codex-bin "$history_codex" --retry-delay-seconds 0 \
  --max-age-seconds 0 --exclude-session-id "$desktop_session_id" >/dev/null
[[ "$(<"$excluded_counter")" == 0 ]]
echo "controller-session exclusion test passed"

daemon_root="$tmp_dir/daemon-sessions"
daemon_state="$tmp_dir/daemon-state.json"
daemon_log="$tmp_dir/daemon.log"
daemon_pid="$tmp_dir/daemon.pid"
daemon_workdir="$tmp_dir/daemon-workdir"
daemon_cwd_file="$tmp_dir/daemon-cwd"
mkdir -p "$daemon_root"
mkdir -p "$daemon_workdir"
daemon_session_id="019ed90c-3b33-7922-92ad-6e61d74ca9e1"
printf '%s\n' "{\"type\":\"session_meta\",\"payload\":{\"id\":\"$daemon_session_id\"}}" > "$daemon_root/rollout-daemon.jsonl"
printf '%s\n' '{"timestamp":"2026-09-20T09:13:44.000Z","ordinal":1,"type":"event_msg","payload":{"type":"task_complete","error":{"message":"429 model at capacity"}}}' >> "$daemon_root/rollout-daemon.jsonl"
daemon_codex="$tmp_dir/daemon-codex.sh"
cat > "$daemon_codex" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
pwd > "$DAEMON_CWD_FILE"
EOF
chmod +x "$daemon_codex"
(cd "$daemon_workdir" && DAEMON_CWD_FILE="$daemon_cwd_file" python3 "$scanner" --daemon --once \
  --session-root "$daemon_root" --state-file "$daemon_state" --log-file "$daemon_log" \
  --pid-file "$daemon_pid" --codex-bin "$daemon_codex" --retry-delay-seconds 0 --max-age-seconds 0)
for _ in $(seq 1 20); do
  [[ -f "$daemon_cwd_file" ]] && [[ -f "$daemon_log" ]] && [[ "$(grep -c 'daemon started' "$daemon_log" || true)" == 1 ]] && break
  sleep 0.1
done
[[ -f "$daemon_log" ]]
[[ "$(grep -c 'daemon started' "$daemon_log")" == 1 ]]
[[ "$(<"$daemon_cwd_file")" == "$daemon_workdir" ]]
echo "detached daemon test passed"
