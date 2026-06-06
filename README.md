# DingTalk Agent Skills

Custom local skills for Derek's DingTalk and Dingdang OKR workflows.

This repository is the source-controlled copy. Installed skills live under:

```text
~/.agents/skills
```

## Skills

| Skill | Purpose |
| --- | --- |
| `dingdang-okr-export` | Export Dingdang OKR data into a verified Excel workbook with one tab per person. |
| `dingtalk-browser-export` | Export the currently open DingTalk/Alidocs Chrome document to docx/pdf/md when browser export is needed. |
| `dingtalk-knowledge-organize` | Inventory, classify, rename, move, and deduplicate DingTalk knowledge base files through a CSV approval workflow. |
| `dingtalk-minutes-access-request` | Request or recheck access for restricted DingTalk AI 听记 pages. Reading content belongs to `dws minutes`. |
| `dingtalk-oa-approval` | Review DingTalk OA approvals with Derek's evidence and material-completeness rules. |

## Install

From this repo:

```bash
./install.sh
```

The installer syncs `skills/*` into `~/.agents/skills`, excluding local state such as `config.json`, `.env`, `node_modules`, browser profiles, and generated outputs.

## Rules

- Do not commit credentials, tokens, cookies, browser profiles, exported workbooks, raw captures, or local `config.json` files.
- Prefer `dws` for DingTalk primitive operations. These skills should contain only reusable workflow rules, review criteria, output formats, and fallback paths.
- Keep one business boundary per skill. Do not merge approval, OKR, knowledge-base cleanup, minutes access, and browser export into a single broad skill.
