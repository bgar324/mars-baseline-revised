"""Configuration for outbound HTTP clients."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class ClientConfig(BaseSettings):
    """Settings shared by HTTP provider clients."""

    model_config = SettingsConfigDict(env_prefix="CLIENT__", extra="ignore")

    base_url: str
    user_agent: str = "mars"
    request_timeout: float = 60.0
    min_request_interval: float = 0.0
