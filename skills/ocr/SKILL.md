---
name: ocr
description: Extract text from local images, screenshots, scanned PDFs, receipts, forms, and mixed Chinese-English documents with the external Stardust OCR service. Use this skill whenever the user asks to OCR, recognize, transcribe, read, or extract text from image-based files, including when a PDF has no usable text layer.
metadata:
  requires:
    bins:
      - python3
---

# OCR

Use the external OCR service at `https://ocr.preseen.ai/v1`. It runs RapidOCR for simplified Chinese and English. The service can be cold after a long idle period, so the first request may take longer while its GPU worker starts.

## Workflow

1. Resolve every requested local file to an absolute path and confirm it exists.
2. For an image, screenshot, scanned PDF, receipt, or form, run:

```bash
python3 "$HOME/.agents/skills/ocr/scripts/ocr.py" \
  "/absolute/path/to/file.png" \
  --format markdown
```

3. Pass multiple files in one invocation when they belong to the same task. This lets the service batch them:

```bash
python3 "$HOME/.agents/skills/ocr/scripts/ocr.py" \
  "/absolute/path/to/page-1.png" \
  "/absolute/path/to/page-2.jpg" \
  --format markdown \
  --output "/absolute/path/to/ocr-result.md"
```

4. For selected PDF pages, use one-based page numbers:

```bash
python3 "$HOME/.agents/skills/ocr/scripts/ocr.py" \
  "/absolute/path/to/scanned.pdf" \
  --pages 1,3-5 \
  --format markdown
```

5. Read the result and answer the user's actual question. Preserve page boundaries when they matter. Clearly label uncertain text when confidence is low or the response contains warnings; do not silently repair names, amounts, dates, identifiers, or other consequential fields.

## Output modes

- `--format text`: recognized text only, suitable for piping or quick reading.
- `--format markdown`: source and page headings plus confidence and warnings. This is the default for agent use.
- `--format json`: the service response, suitable for downstream processing.
- `--output PATH`: write the selected format to a file. Without it, print to stdout.

## Authentication and configuration

The client resolves credentials at runtime and never prints them. Resolution order:

1. `DOCUMENT_OCR_API_KEY` environment variable.
2. The selected `document_ocr_providers` entry in the file named by `DOCUMENT_OCR_CONFIG`, or in `$HOME/Documents/Projects/memory-connector/config/providers.yaml` when that repository is present.

The public base URL defaults to `https://ocr.preseen.ai/v1`. Override it only when the user explicitly asks by setting `DOCUMENT_OCR_PUBLIC_BASE_URL` or passing `--base-url`. Do not use the provider registry's loopback `127.0.0.1` address from this machine; that address is only valid inside the OCR server.

The default model and languages come from the selected provider entry. Override them with `--model` or `--languages` only when the service advertises the requested values through `/v1/models` or `/healthz`.

The bundled client uses PyYAML to read the existing provider registry. If `import yaml` fails, install `PyYAML` into the Python environment used to run the script.

## Failure handling

- A missing file, unsupported MIME type, malformed page range, authentication failure, or service error is a real failure. Report it directly.
- Do not fall back to a different OCR engine or upload the file elsewhere without the user's authorization.
- OCR is probabilistic. For high-impact fields, quote the recognized value with its page and confidence, and recommend checking the source image when evidence is weak.
