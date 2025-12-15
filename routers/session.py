"""
세션 API - 만남승강장 추천 상태 조회

포토카드 생성 후 추천 결과를 polling으로 조회합니다.
"""
import logging
import time
from datetime import datetime
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

# 로거 설정
logger = logging.getLogger("session")
logger.setLevel(logging.DEBUG)

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
    request_id = f"status_{int(time.time() * 1000)}"
    start_time = time.time()

    logger.info(f"[{request_id}] /status/{photo_card_id} 요청 시작")

    session = await get_session_by_photo_card_id(db, photo_card_id)

    if not session:
        logger.warning(f"[{request_id}] 세션 없음: photo_card_id={photo_card_id}")
        raise HTTPException(
            status_code=404,
            detail="Session not found for this photo card"
        )

    logger.info(f"[{request_id}] 세션 조회 성공: session_id={session.id}, status={session.status}")

    # 접근 시간 업데이트
    await update_last_accessed(db, session.id)

    # 상태별 메시지
    status_messages = {
        "pending": "추천 요청 대기중...",
        "processing": "AI가 여행 코스를 분석하고 있어요...",
        "completed": "추천 완료!",
        "failed": session.error_message or "추천 요청 실패",
    }

    elapsed = time.time() - start_time
    logger.info(f"[{request_id}] /status 응답 완료 (소요시간: {elapsed:.3f}초)")

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
    request_id = f"recommend_{int(time.time() * 1000)}"
    start_time = time.time()

    logger.info("=" * 60)
    logger.info(f"[{request_id}] /recommendation/{photo_card_id} 요청 시작")
    logger.info(f"[{request_id}] 시간: {datetime.now().isoformat()}")

    session = await get_session_by_photo_card_id(db, photo_card_id)

    if not session:
        logger.warning(f"[{request_id}] 세션 없음: photo_card_id={photo_card_id}")
        raise HTTPException(
            status_code=404,
            detail="Session not found for this photo card"
        )

    logger.info(f"[{request_id}] 세션 조회 성공:")
    logger.info(f"[{request_id}]   - session_id: {session.id}")
    logger.info(f"[{request_id}]   - status: {session.status}")
    logger.info(f"[{request_id}]   - created_at: {session.created_at}")

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
        logger.info(f"[{request_id}] 상태: pending - 대기중")
    elif session.status == "processing":
        response.message = "AI가 여행 코스를 분석하고 있어요..."
        logger.info(f"[{request_id}] 상태: processing - 처리중")
    elif session.status == "failed":
        response.message = session.error_message or "추천 요청 실패"
        logger.warning(f"[{request_id}] 상태: failed - {response.message}")
    elif session.status == "completed" and session.recommendation_data:
        logger.info(f"[{request_id}] 상태: completed - 데이터 변환 시작")

        # 추천 데이터 파싱
        data = session.recommendation_data
        logger.debug(f"[{request_id}] 원본 데이터 키: {data.keys()}")

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
        logger.info(f"[{request_id}] spots 변환 완료: {len(spots)}개")

        # course 변환
        course_data = data.get("course")
        if course_data and course_data.get("stops"):
            logger.info(f"[{request_id}] course 변환 시작 (stops: {len(course_data.get('stops', []))}개)")
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
                    travel_time_to_next=stop.get("travel_time_to_next"),
                    distance_to_next_km=stop.get("distance_to_next_km"),
                    reason=stop.get("reason"),
                    tip=stop.get("tip")
                ))

            response.course = RecommendedCourse(
                title=course_data.get("title", "추천 여행 코스"),
                stops=stops,
                total_duration=course_data.get("total_duration"),
                total_distance_km=course_data.get("total_distance_km"),
                summary=course_data.get("summary")
            )

            logger.info(f"[{request_id}] course 변환 완료:")
            logger.info(f"[{request_id}]   - title: {response.course.title}")
            logger.info(f"[{request_id}]   - stops: {len(stops)}개")
            logger.info(f"[{request_id}]   - total_duration: {response.course.total_duration}")
            logger.info(f"[{request_id}]   - total_distance_km: {response.course.total_distance_km}")
            for i, s in enumerate(stops):
                logger.debug(f"[{request_id}]   - stop[{i}]: {s.order}. {s.name} - 다음까지 {s.distance_to_next_km}km")

        response.message = data.get("message", f"{len(spots)}개의 장소를 찾았습니다.")

    elapsed = time.time() - start_time
    logger.info(f"[{request_id}] /recommendation 응답 완료 (소요시간: {elapsed:.3f}초)")
    logger.info(f"[{request_id}]   - spots: {len(response.spots)}개")
    logger.info(f"[{request_id}]   - course: {'있음' if response.course else '없음'}")
    logger.info("=" * 60)

    return response
