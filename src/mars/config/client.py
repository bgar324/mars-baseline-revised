from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ClientConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CLIENT_", extra="ignore")

    base_url: str
    user_agent: str = "mars"
    request_timeout: float = 60.0
    min_request_interval: float = 0.0
    api_key: SecretStr | None = None
