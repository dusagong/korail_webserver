"""
세션 API - 만남승강장 추천 상태 조회

포토카드 생성 후 추천 결과를 polling으로 조회합니다.
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas.models import (
    SessionStatusResponse,
    SessionRecommendationResponse,
    SpotWithLocation,
    RecommendedCourse,
    CourseStop,
)
from crud import (
    get_session_by_photo_card_id,
    get_session_by_id,
    update_last_accessed,
)

router = APIRouter(
    prefix="/api/v1/sessions",
    tags=["sessions"]
)


@router.get("/status/{photo_card_id}", response_model=SessionStatusResponse)
async def get_session_status(
    photo_card_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    포토카드 ID로 세션 상태 조회 (polling용)

    - **status**: pending, processing, completed, failed
    - 클라이언트는 completed가 될 때까지 polling
    """
    session = await get_session_by_photo_card_id(db, photo_card_id)

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found for this photo card"
        )

    # 접근 시간 업데이트
    await update_last_accessed(db, session.id)

    # 상태별 메시지
    status_messages = {
        "pending": "추천 요청 대기중...",
        "processing": "AI가 여행 코스를 분석하고 있어요...",
        "completed": "추천 완료!",
        "failed": session.error_message or "추천 요청 실패",
    }

    return SessionStatusResponse(
        session_id=session.id,
        photo_card_id=session.photo_card_id,
        status=session.status,
        message=status_messages.get(session.status, "")
    )


@router.get("/recommendation/{photo_card_id}", response_model=SessionRecommendationResponse)
async def get_session_recommendation(
    photo_card_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    포토카드 ID로 추천 결과 조회

    - status가 "completed"일 때만 spots, course 데이터가 있음
    - status가 "pending" 또는 "processing"이면 빈 결과
    - status가 "failed"면 에러 메시지
    """
    session = await get_session_by_photo_card_id(db, photo_card_id)

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found for this photo card"
        )

    # 접근 시간 업데이트
    await update_last_accessed(db, session.id)

    # 기본 응답
    response = SessionRecommendationResponse(
        session_id=session.id,
        photo_card_id=session.photo_card_id,
        status=session.status,
        spots=[],
        course=None,
        message="",
        created_at=session.created_at.isoformat() if session.created_at else None,
        completed_at=session.completed_at.isoformat() if session.completed_at else None,
    )

    # 상태별 처리
    if session.status == "pending":
        response.message = "추천 요청 대기중..."
    elif session.status == "processing":
        response.message = "AI가 여행 코스를 분석하고 있어요..."
    elif session.status == "failed":
        response.message = session.error_message or "추천 요청 실패"
    elif session.status == "completed" and session.recommendation_data:
        # 추천 데이터 파싱
        data = session.recommendation_data

        # spots 변환
        spots = []
        for s in data.get("spots", []):
            spots.append(SpotWithLocation(
                name=s.get("name", ""),
                address=s.get("address"),
                category=s.get("category"),
                image_url=s.get("image_url"),
                mapx=s.get("mapx"),
                mapy=s.get("mapy"),
                tel=s.get("tel"),
                content_id=s.get("content_id")
            ))
        response.spots = spots

        # course 변환
        course_data = data.get("course")
        if course_data and course_data.get("stops"):
            stops = []
            for stop in course_data.get("stops", []):
                stops.append(CourseStop(
                    order=stop.get("order", 0),
                    name=stop.get("name", ""),
                    address=stop.get("address"),
                    mapx=stop.get("mapx"),
                    mapy=stop.get("mapy"),
                    content_id=stop.get("content_id"),
                    category=stop.get("category"),
                    time=stop.get("time"),
                    duration=stop.get("duration"),
                    reason=stop.get("reason"),
                    tip=stop.get("tip")
                ))

            response.course = RecommendedCourse(
                title=course_data.get("title", "추천 여행 코스"),
                stops=stops,
                total_duration=course_data.get("total_duration"),
                summary=course_data.get("summary")
            )

        response.message = data.get("message", f"{len(spots)}개의 장소를 찾았습니다.")

    return response
