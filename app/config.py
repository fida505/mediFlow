import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    # general
    PROJECT_NAME: str = "MediFlow"
    ENV: str = "production"

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
        case_sensitive = True

settings = Settings()