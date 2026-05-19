from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ClientConfig(BaseSettings):
    """Settings shared by HTTP provider clients."""

    model_config = SettingsConfigDict(env_prefix="CLIENT__", extra="ignore")

    base_url: str
    user_agent: str = "mars"
    request_timeout: float = 60.0
    min_request_interval: float = 0.0
    api_key: SecretStr | None = None


class SemanticScholarSettings(BaseSettings):
    """Runtime configuration for the Semantic Scholar client."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    semantic_scholar_api_key: SecretStr | None = None
    base_url: str = "https://api.semanticscholar.org"
    request_timeout: float = 60.0
    min_request_interval: float = 1.0
