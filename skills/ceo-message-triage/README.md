# CEO Message Triage

Decides the smallest justified response to an incoming DingTalk message: reply, reaction, clarification, handoff, or no action.

Use this skill for ordinary message triage. For specialized domains, route to the neighboring CEO workflow skills such as calendar invitations, document review, mail, meetings, personnel communication, or tracked work.

Key boundaries:

- Load `dingtalk-chat` before reading conversation context or proposing chat actions.
- Treat direct agent mentions like direct principal mentions, but do not treat an `@all` broadcast as principal responsibility by itself.
- Suppress late or redundant replies when newer context already completed the matter.
- Ask one concrete factual question when a verified participant can supply a missing fact.
- Do not invent recipients, targets, responsibilities, or follow-ups.
