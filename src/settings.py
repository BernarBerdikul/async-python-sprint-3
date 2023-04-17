from pydantic import BaseSettings, Field


class AppSettings(BaseSettings):
    """Application settings."""

    SERVER_HOST: str = Field(default="localhost")
    SERVER_PORT: int = Field(default=8000)
    MSG_BATCH_SIZE: int = Field(default=20)
    MAIN_CHAT_NAME: str = Field(default="main")

    class Config:
        env_file = "../.env"


settings = AppSettings()
