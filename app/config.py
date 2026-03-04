import os
from pydantic import BaseSettings, Field


def get_env_setting(name: str, default=None):
    return os.getenv(name) or default


class Settings(BaseSettings):
    # general
    PROJECT_NAME: str = "MediFlow"
    ENV: str = Field(..., env="ENV")  # staging or production

    # database
    DATABASE_URL: str

    # redis / cache
    REDIS_URL: str

    # jwt
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # stripe
    STRIPE_API_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
