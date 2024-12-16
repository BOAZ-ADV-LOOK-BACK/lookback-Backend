from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    # 기존 설정
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # 추가된 설정 필드
    DB_PWD: str = os.getenv("DB_PWD")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    class Config:
        env_file = ".env"  # .env 파일 사용
        env_file_encoding = "utf-8"
        extra = "ignore"  # 정의되지 않은 필드는 무시

settings = Settings()
