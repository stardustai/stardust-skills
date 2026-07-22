# FundFlow investor meeting skill

This skill supports Stardust financing work around FundFlow investor meetings.

It prepares investor meetings, reviews post-meeting transcripts, analyzes investor questions and style, recommends follow-up actions, and drafts DingTalk financing-group updates.

Core boundaries:

- FundFlow / 融管通 is the source of truth for financing stage, investor status, meetings, transcripts, and follow-up.
- Public research can support investor style and market context, but it does not replace FundFlow facts.
- DingTalk messages are sent only after the target group and command schema are verified.
- Meeting analysis must distinguish transcript facts from judgment.

See [SKILL.md](SKILL.md) for the full workflow, tool order, routing rules, and message templates.
