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
    자연어로 여행 추천 요청 (LLM 큐레이션 포함)

    - **query**: 자연어 질의 (예: "강릉 바다 근처 맛집이랑 카페 추천해줘")
    """
    llm = LLMClient()
    tour_api = TourAPIService()

    # 1. LLM으로 자연어 파싱
    try:
        params = await llm.parse_travel_query(request.query)
    except Exception:
        params = {"keyword": request.query, "content_types": ["관광지"]}

    destination = params.get("destination", "")
    area = params.get("area", destination)
    keyword = params.get("keyword", "관광")
    sigungu = params.get("sigungu")

    # 2. 관광 API 호출
    combined = await tour_api.get_combined_results(keyword, area, sigungu)

    keyword_results = combined["keyword_results"]
    related_results = combined["related_results"]

    if not keyword_results and not related_results:
        return AskResponse(
            destination=destination,
            extracted_params=params,
            curated_course=None,
            raw_courses=[],
            message=f"'{request.query}'에 맞는 결과를 찾지 못했습니다."
        )

    # 3. 원본 코스 생성 (백업용)
    raw_courses = _build_courses(keyword_results, related_results, keyword)

    # 4. LLM 큐레이션 (코스 설계 + 설명 + 팁)
    curated_course = None
    try:
        curated_data = await llm.curate_and_explain(request.query, combined, params)
        print(f"[DEBUG] curated_data: {curated_data}")  # 디버그 로그

        # 응답을 모델로 변환
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

        if curated_spots:  # spots가 있을 때만 코스 생성
            curated_course = CuratedCourse(
                course_title=curated_data.get("course_title", f"{destination} 추천 코스"),
                spots=curated_spots,
                overall_tip=curated_data.get("overall_tip"),
                summary=curated_data.get("summary")
            )
    except Exception as e:
        print(f"[ERROR] 큐레이션 실패: {e}")  # 에러 로그
        # 큐레이션 실패시 raw_courses만 반환

    return AskResponse(
        destination=destination,
        extracted_params=params,
        curated_course=curated_course,
        raw_courses=raw_courses,
        message=f"'{destination}' {keyword} 관련 맞춤 추천입니다."
    )
