from fastapi import APIRouter, HTTPException

from schemas import (
    RecommendRequest, RecommendResponse, Course, Spot,
    AskRequest, AskResponse, SpotWithLocation, CourseStop, RecommendedCourse
)
from services import LLMClient, TourAPIService

router = APIRouter(prefix="/api/v1", tags=["recommend"])

# hashtag.py의 세션과 공유
from routers.hashtag import sessions


@router.post("/recommend", response_model=RecommendResponse)
async def get_recommendation(request: RecommendRequest):
    """
    해시태그 세션 + 추가 정보를 바탕으로 여행 코스 추천

    - **session_id**: 해시태그 생성시 받은 세션 ID
    - **destination**: 목적지 (예: 강릉, 제주)
    - **preferences**: 선호 사항 (테마, 동행, 스타일)
    """
    # 세션 컨텍스트 가져오기
    session_context = ""
    if request.session_id in sessions:
        session_data = sessions[request.session_id]
        session_context = f"이전 설명: {session_data['description']}, 해시태그: {session_data['hashtags']}"

    llm = LLMClient()
    tour_api = TourAPIService()

    # 1. LLM으로 검색 파라미터 추출
    preferences_dict = {}
    if request.preferences:
        preferences_dict = request.preferences.model_dump(exclude_none=True)

    try:
        search_params = await llm.extract_search_params(
            session_context,
            request.destination,
            preferences_dict
        )
    except Exception:
        # LLM 실패시 기본값
        search_params = {
            "area": request.destination,
            "keyword": preferences_dict.get("theme", "관광")
        }

    # 2. 관광 API로 데이터 조회
    keyword = search_params.get("keyword", "관광")
    area = search_params.get("area", request.destination)
    sigungu = search_params.get("sigungu")

    combined = await tour_api.get_combined_results(keyword, area, sigungu)

    keyword_results = combined["keyword_results"]
    related_results = combined["related_results"]

    if not keyword_results and not related_results:
        return RecommendResponse(
            courses=[],
            message=f"'{request.destination}'에서 '{keyword}' 관련 정보를 찾지 못했습니다."
        )

    # 3. 코스 생성
    courses = _build_courses(keyword_results, related_results, keyword)

    return RecommendResponse(
        courses=courses,
        message=f"'{request.destination}' {keyword} 테마 여행 코스입니다."
    )


def _build_courses(keyword_results: list, related_results: list, theme: str) -> list[Course]:
    """검색 결과를 여행 코스로 변환"""
    spots = []

    # 메인 관광지 (KorService2)
    main_spots = [
        item for item in keyword_results
        if item.get("contenttypeid") == "12"
    ][:3]

    for item in main_spots:
        spots.append(Spot(
            name=item.get("title", "이름없음"),
            address=item.get("addr1", ""),
            category="관광지",
            description=item.get("overview", ""),
            image_url=item.get("firstimage", ""),
        ))

    # 연관 맛집 (TarRlteTarService1)
    food_spots = [
        item for item in related_results
        if item.get("rlteCtgryLclsNm") == "음식"
    ]
    food_spots.sort(key=lambda x: int(x.get("rlteRank", 99)))

    for item in food_spots[:2]:
        spots.append(Spot(
            name=item.get("rlteTatsNm", "이름없음"),
            category=item.get("rlteCtgrySclsNm", "음식"),
            rank=int(item.get("rlteRank", 0)),
        ))

    # 연관 관광지
    extra_spots = [
        item for item in related_results
        if item.get("rlteCtgryLclsNm") == "관광지"
    ]
    extra_spots.sort(key=lambda x: int(x.get("rlteRank", 99)))

    for item in extra_spots[:2]:
        spots.append(Spot(
            name=item.get("rlteTatsNm", "이름없음"),
            category="연관 관광지",
            rank=int(item.get("rlteRank", 0)),
        ))

    if not spots:
        return []

    return [Course(
        title=f"{theme} 테마 추천 코스",
        spots=spots,
        summary=f"KorService2 + TarRlteTarService1 데이터 기반 추천"
    )]


@router.post("/ask", response_model=AskResponse)
async def ask_travel(request: AskRequest):
    """
    자연어로 여행 추천 요청 (MCP 통합)

    - **query**: 자연어 질의 (예: "바닷가 근처에서 바다뷰 보이는 카페에 갔다가 저녁은 삼겹살을 먹고싶어")
    - **area_code**: 모바일에서 선택한 도 코드 (예: "32" for 강원)
    - **sigungu_code**: 모바일에서 선택한 시/군/구 코드 (선택)

    응답 구조:
    - **spots**: 리스트 뷰용 (전체 검색 결과, 지도 좌표 포함)
    - **course**: 코스 뷰용 (LLM이 큐레이션한 동선)
    """
    llm = LLMClient()

    try:
        # MCP 엔드포인트로 쿼리 + area 정보 전달
        mcp_result = await llm.mcp_query(
            query=request.query,
            area_code=request.area_code,
            sigungu_code=request.sigungu_code
        )

        print(f"[DEBUG] MCP result keys: {mcp_result.keys()}")

        # 성공 여부 확인
        if not mcp_result.get("success", False):
            return AskResponse(
                success=False,
                query=request.query,
                area_code=request.area_code,
                sigungu_code=request.sigungu_code,
                spots=[],
                course=None,
                message=mcp_result.get("error", "추천 요청 실패")
            )

        # spots 변환 (리스트 뷰용)
        spots = []
        for s in mcp_result.get("spots", []):
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

        # course 변환 (코스 뷰용)
        course = None
        course_data = mcp_result.get("course")
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
                    travel_time_to_next=stop.get("travel_time_to_next"),
                    distance_to_next_km=stop.get("distance_to_next_km"),
                    reason=stop.get("reason"),
                    tip=stop.get("tip")
                ))

            course = RecommendedCourse(
                title=course_data.get("title", "추천 여행 코스"),
                stops=stops,
                total_duration=course_data.get("total_duration"),
                total_distance_km=course_data.get("total_distance_km"),
                summary=course_data.get("summary")
            )

        return AskResponse(
            success=True,
            query=request.query,
            area_code=request.area_code,
            sigungu_code=request.sigungu_code,
            spots=spots,
            course=course,
            message=mcp_result.get("message", f"{len(spots)}개의 장소를 찾았습니다.")
        )

    except Exception as e:
        print(f"[ERROR] MCP query 실패: {e}")

        return AskResponse(
            success=False,
            query=request.query,
            area_code=request.area_code,
            sigungu_code=request.sigungu_code,
            spots=[],
            course=None,
            message=f"서버 오류: {str(e)}"
        )
