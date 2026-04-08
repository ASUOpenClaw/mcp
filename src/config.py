from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MCP_", extra="ignore")

    rest_url: str = "http://localhost:8000"
    service_api_key: str = ""  # shared secret — MCP_SERVICE_API_KEY
    redis_url: str = "redis://localhost:6379/0"
    host: str = "0.0.0.0"
    port: int = 8002
    context_ttl: int = 300  # seconds, matches Shell EX 300
    http_pool_size: int = 20


settings = Settings()
