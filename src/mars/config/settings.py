from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class GeminiSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GEMINI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: SecretStr
    model: str = "gemini-3-flash-preview"
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)
    top_k: int = Field(default=40, ge=1, le=100)
    max_output_tokens: int = Field(default=2048, ge=100, le=8192)
    thinking_level: str | None = None


class LangExtractSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LANGEXTRACT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: SecretStr
    model_id: str = "gemini-2.5-flash-lite"
    extraction_passes: int = Field(default=1, ge=1, le=10)
    max_workers: int = Field(default=10, ge=1, le=100)
    max_char_buffer: int = Field(default=1000, ge=100, le=5000)


class SupabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SUPABASE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    url: str | None = None
    publishable_key: SecretStr | None = None
    secret_key: SecretStr | None = None


class SemanticScholarSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SEMANTIC_SCHOLAR_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: SecretStr | None = None
    base_url: str = "https://api.semanticscholar.org"
    request_timeout: float = 60.0
    min_request_interval: float = 1.0


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini: GeminiSettings = Field(default_factory=GeminiSettings)
    langextract: LangExtractSettings = Field(default_factory=LangExtractSettings)
    supabase: SupabaseSettings = Field(default_factory=SupabaseSettings)
    s2: SemanticScholarSettings = Field(default_factory=SemanticScholarSettings)
