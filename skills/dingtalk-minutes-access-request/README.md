# dingtalk-minutes-access-request

Permission-request helper for DingTalk AI 听记 pages.

This skill is intentionally narrow. It only handles:

- checking whether a `shanji.dingtalk.com` 听记 page is permission-blocked
- sending an access request when the page allows it
- rechecking previously blocked links
- diagnosing login, permission, or page-layout blockers

It does not read, export, summarize, or store transcript content. Use `dws minutes` for 听记 reading once access is available.

## Common Commands

Check prerequisites:

```bash
python3 scripts/doctor.py --pretty
```

Refresh login state:

```bash
python3 scripts/launch_dingtalk_access_browser.py --pretty
python3 scripts/export_dingtalk_storage_state.py --pretty
```

Request access for one URL:

```bash
python3 scripts/recheck_dingtalk_permission_pages.py \
  --storage-state ~/Documents/dingtalk-minutes-access-request/.storage_state.json \
  --url "https://shanji.dingtalk.com/app/transcribes/<row_key>" \
  --request-permissions \
  --pretty
```

Debug one blocked page:

```bash
python3 scripts/debug_permission_page.py \
  ~/Documents/dingtalk-minutes-access-request/.storage_state.json \
  <row_key>
```

## Read Path

After permission is available, switch to `dws minutes` for actual content:

```bash
dws minutes get --help
```
