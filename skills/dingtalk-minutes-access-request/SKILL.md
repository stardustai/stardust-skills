---
name: dingtalk-minutes-access-request
description: Use when the user wants to request access to restricted DingTalk AI 听记/minutes pages, recheck permission-pending AI 听记 links, or diagnose why a shanji.dingtalk.com transcript cannot be opened. Do not use this skill to read transcripts or summaries; use dws minutes for reading.
---

# DingTalk Minutes Access Request

Use this skill only for DingTalk AI 听记 permission work:

- request access for restricted `shanji.dingtalk.com` 听记 pages
- recheck links that were previously permission-blocked
- diagnose whether a page is blocked by login, permission, stale storage state, or page layout

Do not use this skill to extract, summarize, or save meeting transcript content. Reading 听记 detail, transcript, AI summary, speakers, todos, keywords, or mind graph must go through `dws minutes`.

## Boundary

- `dws minutes`: read/list/get/transcript/summary/todo/speaker/keyword/mind-graph operations.
- `dingtalk-minutes-access-request`: browser-based permission request and blocked-page diagnosis only.

If permission is granted after a recheck, stop and switch to `dws minutes` for the actual read.

## Prerequisites

- macOS with Google Chrome installed.
- Python 3.10+ and Playwright installed.
- A dedicated DingTalk browser profile/storage state may already exist from prior sync work.

## Current Scripts

Check local prerequisites:

```bash
python3 scripts/doctor.py --pretty
```

Launch a dedicated visible browser when login refresh is needed:

```bash
python3 scripts/launch_dingtalk_sync_browser.py --pretty
```

Export storage state after login:

```bash
python3 scripts/export_dingtalk_storage_state.py --pretty
```

Check CDP connectivity:

```bash
python3 scripts/check_dingtalk_sync_browser.py --pretty
```

Recheck blocked permission pages and optionally send access requests:

```bash
python3 scripts/recheck_dingtalk_permission_pages.py \
  --storage-state ~/Documents/dingtalk-minutes-access-request/.storage_state.json \
  --url "https://shanji.dingtalk.com/app/transcribes/<row_key>" \
  --request-permissions \
  --pretty
```

Diagnose one blocked page:

```bash
python3 scripts/debug_permission_page.py \
  ~/Documents/dingtalk-minutes-access-request/.storage_state.json \
  <row_key>
```

## Default Local Layout

- config: `config.json`
- example config: `config.example.json`
- storage state: `~/Documents/dingtalk-minutes-access-request/.storage_state.json`
- dedicated Chrome profile: `~/Documents/dingtalk-minutes-access-request/.chrome-profile`

## Reporting Back

Always return:

- page URL or row key
- whether the page is accessible now
- whether an access request was sent
- permission-pending or failure reason
- next read path, normally `dws minutes ...`, when access is available
