from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://fineas:fineas@localhost:5432/fineas"
    ANTHROPIC_API_KEY: str = ""
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = "http://localhost:3001"
    DEFAULT_MONTE_CARLO_SIMULATIONS: int = 10000

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


settings = Settings()
