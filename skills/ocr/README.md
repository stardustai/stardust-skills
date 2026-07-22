# OCR skill

This skill extracts text from local images and scanned PDFs through the external Stardust OCR API at `https://ocr.preseen.ai/v1`.

It supports simplified Chinese and English, multi-file batching, selected PDF pages, text/Markdown/JSON output, and preservation of service confidence and warnings. Credentials are resolved at runtime from `DOCUMENT_OCR_API_KEY` or the existing `memory-connector` provider registry and are never copied into this skill.

See [SKILL.md](SKILL.md) for the agent workflow and command examples.
