from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from mars.config.pipeline import PipelineConfig


class GeminiSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GEMINI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: SecretStr
    model: str = "gemini-3-flash-preview"
    temperature: float = Field(default=1.0, ge=0.0, le=2.0)
    max_output_tokens: int = Field(default=8192, ge=100, le=32768)
    thinking_level: str | None = "medium"
    retry_attempts: int = Field(default=8, ge=1)
    retry_initial_delay: float = Field(default=1.0, ge=0.0)
    retry_max_delay: float = Field(default=60.0, ge=0.0)


class DebateSettings(GeminiSettings):
    model_config = SettingsConfigDict(
        env_prefix="DEBATE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    max_output_tokens: int = Field(default=32768, ge=100, le=32768)


class OpenAISettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OPENAI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: SecretStr | None = None
    base_url: str | None = None
    model: str = "gpt-4o"
    temperature: float = Field(default=1.0, ge=0.0, le=2.0)
    max_output_tokens: int | None = None
    retry_attempts: int = Field(default=8, ge=1)
    retry_initial_delay: float = Field(default=1.0, ge=0.0)
    retry_max_delay: float = Field(default=60.0, ge=0.0)


class OpenRouterSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OPENROUTER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: SecretStr | None = None
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "qwen/qwen-2.5-72b-instruct"
    temperature: float = Field(default=1.0, ge=0.0, le=2.0)
    max_output_tokens: int | None = None
    retry_attempts: int = Field(default=8, ge=1)
    provider_sort: str | None = "throughput"


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
    min_request_interval: float = 1.5
    cache_dir: str | None = ".s2_cache"


class HuggingFaceSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HF_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    model_name: str = "allenai/specter2_base"
    token: SecretStr | None = None


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini: GeminiSettings = Field(default_factory=GeminiSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    openrouter: OpenRouterSettings = Field(default_factory=OpenRouterSettings)
    langextract: LangExtractSettings = Field(default_factory=LangExtractSettings)
    supabase: SupabaseSettings = Field(default_factory=SupabaseSettings)
    s2: SemanticScholarSettings = Field(default_factory=SemanticScholarSettings)
    huggingface: HuggingFaceSettings = Field(default_factory=HuggingFaceSettings)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)


class BaselineAppSettings(BaseSettings):
    """Settings required by the manual baseline deployment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini: GeminiSettings = Field(default_factory=GeminiSettings)
    supabase: SupabaseSettings = Field(default_factory=SupabaseSettings)
    s2: SemanticScholarSettings = Field(default_factory=SemanticScholarSettings)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
