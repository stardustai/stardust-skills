# CEO Calendar Invite

Handles incoming DingTalk calendar invitations, meeting cards, attendance decisions, conflicts, and questions about why the principal should attend.

Use this skill before deciding whether to accept, tentatively hold, decline, or clarify an invitation. Use `ceo-meeting-work` after attendance is settled and the work concerns meeting content.

Key boundaries:

- Load `dingtalk-calendar` before calendar reads or writes.
- Read event title, time, organizer, attendees, description, comments, linked materials, current response state, and conflicts.
- Do not clarify only because a description is missing when other facts establish meeting value.
- For silent meetings with material, process the material instead of merely accepting.
- Audit must reread live event state before executing a calendar response.
