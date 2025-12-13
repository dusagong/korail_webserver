from fastapi import APIRouter, HTTPException

from schemas import RecommendRequest, RecommendResponse, Course, Spot, AskRequest, AskResponse, CuratedCourse, CuratedSpot
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

    - **query**: 자연어 질의 (예: "바다 근처 맛집이랑 카페 추천해줘")
    - **area_code**: 모바일에서 선택한 도 코드 (예: "32" for 강원)
    - **sigungu_code**: 모바일에서 선택한 시/군/구 코드 (선택)
    """
    llm = LLMClient()

    # MCP 엔드포인트로 쿼리 + area 정보 전달
    try:
        mcp_result = await llm.mcp_query(
            query=request.query,
            area_code=request.area_code,
            sigungu_code=request.sigungu_code
        )

        print(f"[DEBUG] MCP result: {mcp_result}")  # 디버그 로그

        # MCP 응답 파싱
        curated_data = mcp_result.get("curated_course")
        selected_tools = mcp_result.get("selected_tools", [])
        raw_results = mcp_result.get("raw_results", [])

        # 추출된 파라미터 (LLM이 분석한 정보)
        extracted_params = {}
        if selected_tools:
            # 첫 번째 도구의 arguments에서 파라미터 추출
            extracted_params = selected_tools[0].get("arguments", {})

        # 큐레이션된 코스 변환
        curated_course = None
        if curated_data and curated_data.get("spots"):
            curated_spots = [
                CuratedSpot(
                    name=s.get("name", ""),
                    time=s.get("time"),
                    duration=s.get("duration"),
                    reason=s.get("reason"),
                    tip=s.get("tip")
                )
                for s in curated_data.get("spots", [])
            ]

            if curated_spots:
                curated_course = CuratedCourse(
                    course_title=curated_data.get("course_title", "추천 여행 코스"),
                    spots=curated_spots,
                    overall_tip=curated_data.get("overall_tip"),
                    summary=curated_data.get("summary")
                )

        # 원본 데이터로부터 백업 코스 생성
        raw_courses = []
        if raw_results:
            # raw_results는 MCP tool 실행 결과들
            # 간단한 백업 코스 생성
            for result in raw_results[:1]:  # 첫 번째 결과만 사용
                items = result.get("result", {}).get("response", {}).get("body", {}).get("items", {}).get("item", [])
                if items:
                    spots = []
                    for item in items[:5]:  # 최대 5개
                        spots.append(Spot(
                            name=item.get("title", "이름없음"),
                            address=item.get("addr1", ""),
                            category="MCP 검색 결과",
                            description=item.get("overview", "")[:200] if item.get("overview") else ""
                        ))

                    if spots:
                        raw_courses.append(Course(
                            title="MCP 기본 검색 결과",
                            spots=spots,
                            summary="LLM이 선택한 도구로 검색한 결과"
                        ))

        destination = extracted_params.get("area_code", request.area_code or "미정")

        return AskResponse(
            destination=destination,
            extracted_params=extracted_params,
            curated_course=curated_course,
            raw_courses=raw_courses,
            message=f"MCP 기반 맞춤 추천입니다."
        )

    except Exception as e:
        print(f"[ERROR] MCP query 실패: {e}")  # 에러 로그

        # MCP 실패시 에러 응답
        return AskResponse(
            destination=request.area_code or "미정",
            extracted_params={},
            curated_course=None,
            raw_courses=[],
            message=f"MCP 서버 오류: {str(e)}"
        )
