# OCR skill

This skill extracts text from local images and scanned PDFs through the
Access-protected Stardust OCR API at `https://ocr.preseen.ai/v1`.

It supports simplified Chinese and English, multi-file batching, selected PDF
pages, text/Markdown/JSON output, and preservation of service confidence and
warnings.

Employees sign in through Cloudflare Access with an authorized `@stardust.ai`
identity on first use. Headless workloads set both
`CF_ACCESS_CLIENT_ID` and `CF_ACCESS_CLIENT_SECRET`. Use `ocr.py --auth-status`
to check the selected service origin and `ocr.py --logout` to remove only that
origin's session. The optional `memory-connector` provider registry supplies
model/language defaults only; legacy provider API keys are not used.

See [SKILL.md](SKILL.md) for the agent workflow and command examples.
