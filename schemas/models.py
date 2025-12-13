from pydantic import BaseModel
from typing import Optional


# === 해시태그 API ===

class HashtagRequest(BaseModel):
    description: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"description": "오늘 강릉 바다 왔어요 날씨 좋고 커피도 맛있음"}
            ]
        }
    }


class HashtagResponse(BaseModel):
    hashtags: list[str]
    session_id: str


# === 추천 API ===

class Preferences(BaseModel):
    theme: Optional[str] = None      # 바다, 산, 카페 등
    with_whom: Optional[str] = None  # 연인, 가족, 친구, 혼자
    style: Optional[str] = None      # 여유롭게, 알차게, 맛집위주


class RecommendRequest(BaseModel):
    session_id: str
    destination: str
    preferences: Optional[Preferences] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "session_id": "abc123",
                    "destination": "강릉",
                    "preferences": {
                        "theme": "바다",
                        "with_whom": "연인",
                        "style": "여유롭게"
                    }
                }
            ]
        }
    }


class Spot(BaseModel):
    name: str
    address: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    rank: Optional[int] = None


class Course(BaseModel):
    title: str
    spots: list[Spot]
    summary: Optional[str] = None


class RecommendResponse(BaseModel):
    courses: list[Course]
    message: Optional[str] = None


# === 자연어 질의 API ===

class AskRequest(BaseModel):
    query: str  # "강릉 바다 근처 맛집이랑 카페 추천해줘"
    area_code: Optional[str] = None      # 모바일에서 선택한 도 (예: "32" for 강원)
    sigungu_code: Optional[str] = None   # 모바일에서 선택한 시/군/구

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "바다 근처 맛집이랑 카페 추천해줘",
                    "area_code": "32",
                    "sigungu_code": "1"
                }
            ]
        }
    }


class CuratedSpot(BaseModel):
    name: str
    time: Optional[str] = None          # "오전 10시"
    duration: Optional[str] = None      # "1시간"
    reason: Optional[str] = None        # 추천 이유
    tip: Optional[str] = None           # 방문 팁


class CuratedCourse(BaseModel):
    course_title: str
    spots: list[CuratedSpot]
    overall_tip: Optional[str] = None   # 전체 여행 팁
    summary: Optional[str] = None       # 코스 요약


class AskResponse(BaseModel):
    destination: Optional[str] = None
    extracted_params: dict
    curated_course: Optional[CuratedCourse] = None  # LLM 큐레이션 결과
    raw_courses: list[Course] = []                   # 원본 API 결과 (백업)
    message: str


# === PhotoCard API ===

class PhotoCardCreate(BaseModel):
    user_id: Optional[str] = None
    province: str
    city: str
    message: Optional[str] = None
    hashtags: Optional[list[str]] = None
    ai_quote: Optional[str] = None
    image_path: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "province": "강원도",
                    "city": "강릉시",
                    "message": "강릉에서의 특별한 하루",
                    "hashtags": ["맛집탐방", "카페투어", "해변산책"],
                    "ai_quote": "사랑하는 사람과 함께하는 모든 순간이 기적이 됩니다"
                }
            ]
        }
    }


class PhotoCardResponse(BaseModel):
    id: str
    province: str
    city: str
    message: Optional[str]
    hashtags: Optional[list[str]]
    ai_quote: Optional[str]
    created_at: str
    is_active: bool

    model_config = {"from_attributes": True}
