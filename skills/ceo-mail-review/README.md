# CEO Mail Review

Resolves incoming mail cards, complete mail threads, linked materials, attachments, reply authorization, and duplicate-reply state.

Use this skill when the source request is a DingTalk or Lark mail workflow. Use `ceo-document-review` for substantive review of linked material inside the mail thread.

Key boundaries:

- Load the platform mail skill, such as `dingtalk-mail` or `lark-mail`.
- Treat previews and truncated cards as locators, not evidence.
- Resolve sender, recipients, subject, thread state, and exact request before judging.
- Propose a mail reply only when the current request explicitly authorizes replying.
- Do not draft from unread previews or duplicate a reply already sent in the current thread.
