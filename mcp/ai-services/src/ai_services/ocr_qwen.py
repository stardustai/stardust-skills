"""OCR through the gateway's multimodal Qwen chat model.

Used for tables and complex layouts, where plain RapidOCR text loses structure. The
model reads one page image per request (the gateway allows one image per prompt) and
returns Markdown. PDFs are rendered to PNG pages with PyMuPDF first.
"""

from __future__ import annotations

import base64
import re
from concurrent.futures import ThreadPoolExecutor

import httpx
import pymupdf

from ai_services.backends import BackendError, backend_request
from ai_services.config import Settings
from ai_services.schemas import OcrPage, OcrResponse

PROMPT = (
    "Transcribe every piece of text in this image exactly as written, in natural reading "
    "order. Output Markdown only. Render tables as Markdown tables (use an HTML <table> "
    "when cells are merged), keep headings and lists, and describe nothing that is not "
    "text. Do not translate, summarize or add commentary, and do not wrap the answer in "
    "a code fence. If the image contains no text, output nothing."
)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_FENCE_RE = re.compile(r"^\s*```(?:markdown|md)?\s*\n(.*?)\n```\s*$", re.DOTALL)


def clean_model_text(text: str) -> str:
    text = _THINK_RE.sub("", text).strip()
    fenced = _FENCE_RE.match(text)
    return (fenced.group(1) if fenced else text).strip()


def render_pdf_pages(
    data: bytes, page_numbers: list[int] | None, settings: Settings
) -> list[tuple[int, bytes]]:
    try:
        document = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"could not open PDF: {exc}") from exc
    with document:
        total = document.page_count
        wanted = page_numbers or list(range(1, total + 1))
        invalid = [n for n in wanted if not 1 <= n <= total]
        if invalid:
            raise ValueError(f"page_numbers {invalid} out of range; the PDF has {total} pages")
        if len(wanted) > settings.ocr_qwen_max_pages:
            raise ValueError(
                f"{len(wanted)} pages requested; qwen mode reads at most "
                f"{settings.ocr_qwen_max_pages} per call, so pass page_numbers"
            )
        return [
            (n, document[n - 1].get_pixmap(dpi=settings.ocr_qwen_pdf_dpi).tobytes("png"))
            for n in wanted
        ]


def _read_page(
    image: bytes,
    mime_type: str,
    settings: Settings,
    transport: httpx.BaseTransport | None,
) -> str:
    data_uri = f"data:{mime_type};base64,{base64.b64encode(image).decode('ascii')}"
    payload: dict = {
        "model": settings.ocr_qwen_model,
        "temperature": 0,
        "max_tokens": settings.ocr_qwen_max_output_tokens,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_uri}},
                    {"type": "text", "text": PROMPT},
                ],
            }
        ],
    }
    if settings.ocr_qwen_reasoning_effort:
        payload["reasoning_effort"] = settings.ocr_qwen_reasoning_effort
    response = backend_request(
        "OCR(qwen)",
        "POST",
        settings.ocr_qwen_base_url.rstrip("/") + "/chat/completions",
        api_key=settings.ocr_qwen_api_key,
        timeout_seconds=settings.ocr_qwen_timeout_seconds,
        transport=transport,
        json=payload,
    )
    try:
        choice = response.json()["choices"][0]
        content = choice["message"].get("content") or ""
    except (ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
        raise BackendError("OCR(qwen)", "returned an unexpected response") from exc
    text = clean_model_text(content)
    if choice.get("finish_reason") == "length":
        text += "\n\n[output truncated at the token limit]"
    return text


def ocr_with_qwen(
    name: str,
    data: bytes,
    mime_type: str,
    settings: Settings,
    *,
    page_numbers: list[int] | None = None,
    transport: httpx.BaseTransport | None = None,
) -> OcrResponse:
    if mime_type == "application/pdf":
        inputs = [(n, png, "image/png") for n, png in render_pdf_pages(data, page_numbers, settings)]
    else:
        inputs = [(1, data, mime_type)]

    workers = max(1, min(settings.ocr_qwen_concurrency, len(inputs)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        texts = list(
            pool.map(lambda item: _read_page(item[1], item[2], settings, transport), inputs)
        )

    pages = [OcrPage(page_number=n, text=text) for (n, _, _), text in zip(inputs, texts)]
    warnings = [f"page {p.page_number} returned no text" for p in pages if not p.text]
    return OcrResponse(
        filename=name,
        engine="qwen",
        model=settings.ocr_qwen_model,
        text="\n\n".join(p.text for p in pages if p.text),
        warnings=warnings,
        pages=pages if mime_type == "application/pdf" else [],
    )
