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
    query: str  # "바닷가 근처에서 바다뷰 보이는 카페에 갔다가 저녁은 삼겹살을 먹고싶어"
    area_code: Optional[str] = None      # 모바일에서 선택한 도 (예: "32" for 강원)
    sigungu_code: Optional[str] = None   # 모바일에서 선택한 시/군/구

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "바닷가 근처에서 바다뷰 보이는 카페에 갔다가 저녁은 삼겹살을 먹고싶어. 그리고 그 주변에서 하루 숙박하고 싶어",
                    "area_code": "32",
                    "sigungu_code": "1"
                }
            ]
        }
    }


# 리스트 뷰용 - 지도 연동 가능한 장소 정보
class SpotWithLocation(BaseModel):
    name: str
    address: Optional[str] = None
    category: Optional[str] = None       # 관광지/음식점/카페/숙박
    image_url: Optional[str] = None
    mapx: Optional[str] = None           # 경도 (지도 API용)
    mapy: Optional[str] = None           # 위도 (지도 API용)
    tel: Optional[str] = None            # 전화번호
    content_id: Optional[str] = None     # 상세정보 조회용


# 코스 뷰용 - 동선이 정리된 각 정차지
class CourseStop(BaseModel):
    order: int                           # 방문 순서
    name: str
    address: Optional[str] = None
    mapx: Optional[str] = None
    mapy: Optional[str] = None
    content_id: Optional[str] = None
    category: Optional[str] = None       # 카페/음식점/관광지/숙박
    time: Optional[str] = None           # "오전 10시"
    duration: Optional[str] = None       # "1시간"
    reason: Optional[str] = None         # 커플에게 추천하는 이유
    tip: Optional[str] = None            # 방문 팁


# 코스 뷰용 - LLM이 큐레이션한 전체 코스
class RecommendedCourse(BaseModel):
    title: str                           # "강릉 바다향 데이트 코스"
    stops: list[CourseStop]              # 순서대로 정렬된 정차지들
    total_duration: Optional[str] = None # "약 6시간"
    summary: Optional[str] = None        # 코스 요약 (커플 여행 관점)


class AskResponse(BaseModel):
    success: bool = True
    query: str                                        # 원본 쿼리
    area_code: Optional[str] = None
    sigungu_code: Optional[str] = None
    spots: list[SpotWithLocation] = []                # 리스트 뷰용 (전체 검색 결과)
    course: Optional[RecommendedCourse] = None        # 코스 뷰용 (LLM 큐레이션)
    message: str


# (하위 호환용 - 기존 CuratedSpot, CuratedCourse 유지)
class CuratedSpot(BaseModel):
    name: str
    time: Optional[str] = None
    duration: Optional[str] = None
    reason: Optional[str] = None
    tip: Optional[str] = None


class CuratedCourse(BaseModel):
    course_title: str
    spots: list[CuratedSpot]
    overall_tip: Optional[str] = None
    summary: Optional[str] = None


# === PhotoCard API ===

class PhotoCardCreate(BaseModel):
    user_id: Optional[str] = None
    province: str
    city: str
    message: Optional[str] = None
    hashtags: Optional[list[str]] = None
    ai_quote: Optional[str] = None
    image_path: Optional[str] = None
    area_code: Optional[str] = None      # 도/광역시 코드 (예: "32" for 강원)
    sigungu_code: Optional[str] = None   # 시/군/구 코드 (예: "1" for 강릉)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "province": "강원도",
                    "city": "강릉시",
                    "message": "강릉에서의 특별한 하루",
                    "hashtags": ["맛집탐방", "카페투어", "해변산책"],
                    "ai_quote": "사랑하는 사람과 함께하는 모든 순간이 기적이 됩니다",
                    "area_code": "32",
                    "sigungu_code": "1"
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
    session_id: Optional[str] = None  # 추천 세션 ID (있으면 추천 진행중)

    model_config = {"from_attributes": True}


# === Session API (만남승강장 추천 상태) ===

class SessionStatusResponse(BaseModel):
    """세션 상태 조회 응답"""
    session_id: str
    photo_card_id: str
    status: str  # pending, processing, completed, failed
    message: Optional[str] = None

    model_config = {"from_attributes": True}


class SessionRecommendationResponse(BaseModel):
    """세션 추천 결과 응답 (completed 상태일 때)"""
    session_id: str
    photo_card_id: str
    status: str
    spots: list[SpotWithLocation] = []
    course: Optional[RecommendedCourse] = None
    message: str
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


# === Review API ===

class ReviewImageResponse(BaseModel):
    """리뷰 이미지 응답"""
    id: str
    image_url: str
    image_order: int

    model_config = {"from_attributes": True}


class ReviewCreate(BaseModel):
    """리뷰 생성 요청 (이미지는 별도 multipart로 전송)"""
    place_id: str
    place_name: str
    rating: int  # 1~5
    content: str
    user_id: Optional[str] = None
    photo_card_id: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "place_id": "12345",
                    "place_name": "강릉 해변 카페",
                    "rating": 5,
                    "content": "바다 뷰가 정말 예쁘고 커피도 맛있었어요!",
                    "user_id": "user123"
                }
            ]
        }
    }


class ReviewUpdate(BaseModel):
    """리뷰 수정 요청"""
    rating: Optional[int] = None
    content: Optional[str] = None


class ReviewResponse(BaseModel):
    """리뷰 응답"""
    id: str
    place_id: str
    place_name: str
    rating: int
    content: str
    user_id: Optional[str] = None
    photo_card_id: Optional[str] = None
    image_urls: list[str] = []  # 이미지 URL 리스트
    created_at: str
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}


class ReviewListResponse(BaseModel):
    """리뷰 목록 응답"""
    reviews: list[ReviewResponse]
    total_count: int
    average_rating: float


class PlaceRatingResponse(BaseModel):
    """장소 평점 응답"""
    place_id: str
    average_rating: float
    review_count: int
