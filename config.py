from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "Travel Hashtag Service"
    debug: bool = True

    # DIGITS LLM Server
    llm_base_url: str = "http://localhost:8000"  # DIGITS PC 주소로 변경 필요
    llm_timeout: int = 120  # 큐레이션용 충분한 시간

    # 한국관광공사 API
    tour_api_key: str
    korservice_url: str
    tarrlte_url: str

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
