# DingTalk Runbook

## Preconditions

Use one authenticated `dws` profile for all reads, identity resolution, and
writes. Work from the dated run directory because `@file` arguments must be
relative to the current directory. Preserve raw structured results and inspect
`complete`, pagination, failures, and verification fields.

## 1. Resolve Documents

```bash
dws doc +fetch --node <exact-node-id-or-url> --detail full --scope full --format json
```

Record title, node ID, URL, and revision in `manifest.json`. Save the parsed
top-level JSONML element as `target-before.jsonml`. More than one plausible
target is a hard blocker.

## 2. Inventory and Read AI Minutes

```bash
dws minutes +search --start <beijing-start-rfc3339> --end <beijing-end-rfc3339> --scope all --page-all --format json
dws minutes +detail --ids <comma-separated-relevant-task-uuids> --artifacts basic,summary,keywords,transcript,todos --transcript-output file --output-dir minutes-transcripts --format json
```

Verify `complete=true` for the mine/shared inventory and every selected
transcript. Preserve every screened record and its inclusion or exclusion
reason. Relevant records require the complete transcript, not only the AI
summary.

## 3. Read the CEO's Messages and Context

Resolve `<verified-ceo-sender>` from the authenticated profile or another
verified identity source before searching. Identity-unverified results cannot
support a definitive CEO judgment.

```bash
dws chat +search-msg --senders <verified-ceo-sender> --start <beijing-start-rfc3339> --end <beijing-end-rfc3339> --page-all --order asc --format json
dws chat +thread-replies --message-id <selected-root-message-id> --page-all --order asc --format json
```

Use `dws chat +chat-messages` for sufficient preceding and following context in
non-threaded conversations. Every selected message ID needs a context-read
entry.

## 4. Build and Validate Locally

Create `evidence.json`, `previous-issues.json`, and `report.json`, then run from
the installed Skill directory:

```bash
python3 -m scripts.validate_run --manifest <run-dir>/manifest.json --report <run-dir>/report.json --previous-issues <run-dir>/previous-issues.json --output <run-dir>/validation.json
python3 -m scripts.render_dingtalk_jsonml --before <run-dir>/target-before.jsonml --report <run-dir>/report.json --anchor "<verified-managed-anchor>" --output <run-dir>/target-after.jsonml
```

Do not continue unless validation exits `0` with `publishable: true`. Inspect
the rendered document and verify every person node has a resolved DingTalk
`id` and official `name`.

## 5. Save a Recoverable Version

From the run directory:

```bash
dws doc +version-save --node <exact-target-node> --format json --yes
```

Record the returned version identity before writing. The user's explicit
request to update the named report authorizes this write; otherwise stop at the
validated local draft.

## 6. Guarded Write

Re-fetch the target immediately before writing. Any identity or revision change
blocks the write until the new content is reconciled and validated.

```bash
dws doc +update --node <exact-target-node> --command overwrite --content @target-after.jsonml --doc-format jsonml --expected-revision <verified-revision> --format json --yes
```

Perform one complete write. If the commit status is unknown, read back first;
never repeat an unknown external write.

## 7. Full Readback

```bash
dws doc +fetch --node <exact-target-node> --detail full --scope full --format json
```

Save the response as `readback.json` and verify: title and node unchanged;
revision advanced; preface/calendar preserved; all seven sections ordered; 12
fixed metrics present; prior open issue IDs retained or closed with proof;
native mentions valid; business-line full reports folded; links intact; no
literal Markdown markers, private fields, guessed actuals, or unclassified root
causes. An API success response without matching readback is not completion.

## Failure Policy

Block publication when the target or prior report is unresolved, a core source
is inaccessible, Minutes or messages are incompletely paginated, Derek's
identity is unresolved, the revision changed, or a write cannot be read back.
Keep the evidence and failure ledger and report the exact missing dependency.

Continue locally with a visible coverage warning when only a non-core linked
document, metric actual/definition, or forecast support is absent. Use `无数据`
or `证据缺失`, add a native mention and checkpoint, and do not extrapolate.
