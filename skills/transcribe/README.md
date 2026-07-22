# Audio transcribe skill

This skill transcribes audio and video files with OpenAI transcription models.

It supports fast plain-text transcription, optional speaker diarization, and known-speaker reference audio for meeting or interview workflows.

Core boundaries:

- Use `OPENAI_API_KEY` from the local environment; never ask the user to paste the key.
- Default to fast text transcription unless the user needs speaker labels.
- Use diarization only when speaker labels are requested.
- Keep outputs in a task-specific output directory to avoid overwriting transcripts.

See [SKILL.md](SKILL.md) for the workflow and CLI examples.
