from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    host: str = Field(default="127.0.0.1", alias="AI_SERVICES_HOST")
    port: int = Field(default=8920, alias="AI_SERVICES_PORT")
    mcp_path: str = Field(default="/mcp", alias="AI_SERVICES_MCP_PATH")
    # Comma-separated Host headers the MCP transport accepts (add the public hostname).
    mcp_allowed_hosts: str = Field(
        default="127.0.0.1,localhost,127.0.0.1:*,localhost:*", alias="AI_SERVICES_MCP_ALLOWED_HOSTS"
    )

    ocr_base_url: str = Field(default="http://127.0.0.1:7998/v1", alias="AI_SERVICES_OCR_BASE_URL")
    ocr_model: str | None = Field(default=None, alias="AI_SERVICES_OCR_MODEL")
    ocr_api_key: str | None = Field(default=None, alias="AI_SERVICES_OCR_API_KEY")
    ocr_timeout_seconds: float = Field(default=300.0, alias="AI_SERVICES_OCR_TIMEOUT_SECONDS")

    # Qwen vision mode (tables / complex layouts) runs on the gateway's multimodal chat model.
    ocr_qwen_base_url: str = Field(
        default="http://127.0.0.1:8900/v1", alias="AI_SERVICES_OCR_QWEN_BASE_URL"
    )
    ocr_qwen_model: str = Field(default="qwen3.8-27b", alias="AI_SERVICES_OCR_QWEN_MODEL")
    ocr_qwen_api_key: str | None = Field(default=None, alias="AI_SERVICES_OCR_QWEN_API_KEY")
    ocr_qwen_reasoning_effort: str | None = Field(
        default="low", alias="AI_SERVICES_OCR_QWEN_REASONING_EFFORT"
    )
    ocr_qwen_max_output_tokens: int = Field(
        default=8192, alias="AI_SERVICES_OCR_QWEN_MAX_OUTPUT_TOKENS"
    )
    ocr_qwen_timeout_seconds: float = Field(
        default=600.0, alias="AI_SERVICES_OCR_QWEN_TIMEOUT_SECONDS"
    )
    ocr_qwen_pdf_dpi: int = Field(default=150, alias="AI_SERVICES_OCR_QWEN_PDF_DPI")
    ocr_qwen_max_pages: int = Field(default=20, alias="AI_SERVICES_OCR_QWEN_MAX_PAGES")
    ocr_qwen_concurrency: int = Field(default=3, alias="AI_SERVICES_OCR_QWEN_CONCURRENCY")

    asr_base_url: str = Field(default="http://127.0.0.1:8900/v1", alias="AI_SERVICES_ASR_BASE_URL")
    asr_model: str = Field(default="qwen3-asr", alias="AI_SERVICES_ASR_MODEL")
    asr_api_key: str | None = Field(default=None, alias="AI_SERVICES_ASR_API_KEY")
    asr_language: str | None = Field(default=None, alias="AI_SERVICES_ASR_LANGUAGE")
    asr_timeout_seconds: float = Field(default=1800.0, alias="AI_SERVICES_ASR_TIMEOUT_SECONDS")

    tts_base_url: str = Field(default="http://127.0.0.1:8900/v1", alias="AI_SERVICES_TTS_BASE_URL")
    tts_model: str = Field(default="qwen3-tts-1.7b-customvoice", alias="AI_SERVICES_TTS_MODEL")
    tts_voice: str = Field(default="Vivian", alias="AI_SERVICES_TTS_VOICE")
    tts_api_key: str | None = Field(default=None, alias="AI_SERVICES_TTS_API_KEY")
    tts_timeout_seconds: float = Field(default=300.0, alias="AI_SERVICES_TTS_TIMEOUT_SECONDS")

    model_config = SettingsConfigDict(env_file=".env", populate_by_name=True, extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
