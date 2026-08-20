# Daily Frontier Tech Discovery

Produces a fresh, evidence-backed Chinese technology brief for a technical audience, archives the complete candidate analysis, and can send the final Markdown to DingTalk.

## Local setup

Copy `config/config.example.json` to `config/config.json`, replace both placeholders, and restrict the file to the current user:

```bash
chmod 600 config/config.json
```

`config/config.json` is local-only and must never be committed. Reports and `reported_items.jsonl` live below `${FRONTIER_REPORT_DIR:-$HOME/Documents/memory/tech/daily frontier report}` by default.

Validate a report without sending:

```bash
python scripts/send_dingtalk_markdown.py \
  --title "每日前沿技术洞察" \
  --text-file report.md \
  --dry-run
```
