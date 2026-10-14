from typing import Any

from pydantic import BaseModel, Field


class OcrPage(BaseModel):
    page_number: int
    text: str
    confidence: float | None = None
    warnings: list[str] = Field(default_factory=list)


class OcrResponse(BaseModel):
    filename: str
    engine: str = "rapidocr"
    model: str
    text: str
    confidence: float | None = None
    warnings: list[str] = Field(default_factory=list)
    pages: list[OcrPage] = Field(default_factory=list)


class Segment(BaseModel):
    start: float | None = None
    end: float | None = None
    text: str


class AsrResponse(BaseModel):
    filename: str
    model: str
    text: str
    segments: list[Segment] = Field(default_factory=list)


class TtsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=3000)
    voice: str | None = Field(
        default=None,
        description="Preset voice: Vivian, Serena, Uncle_Fu, Dylan, Eric, Ryan, Aiden, Ono_Anna, Sohee.",
    )
    instructions: str | None = Field(
        default=None, description="Natural-language tone, emotion and pacing control."
    )
    model: str | None = None


class TtsResponse(BaseModel):
    model: str
    voice: str
    format: str
    media_type: str
    size_bytes: int
    audio_base64: str


class HealthResponse(BaseModel):
    status: str
    backends: dict[str, Any]
