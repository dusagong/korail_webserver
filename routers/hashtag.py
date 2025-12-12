import uuid
from fastapi import APIRouter, HTTPException

from schemas import HashtagRequest, HashtagResponse
from services import LLMClient

router = APIRouter(prefix="/api/v1", tags=["hashtag"])

# 간단한 인메모리 세션 저장소 (데모용)
# 프로덕션에서는 Redis 사용 권장
sessions: dict[str, dict] = {}


@router.post("/hashtag", response_model=HashtagResponse)
async def generate_hashtag(request: HashtagRequest):
    """
    사진 설명을 받아 재밌는 해시태그 생성

    - **description**: 여행 사진/경험에 대한 설명
    - Returns: 해시태그 목록 + 세션 ID (2차 추천에서 사용)
    """
    if not request.description.strip():
        raise HTTPException(status_code=400, detail="설명을 입력해주세요")

    llm = LLMClient()

    try:
        hashtags = await llm.generate_hashtags(request.description)
    except Exception as e:
        # LLM 서버 연결 실패시 폴백
        hashtags = ["#여행스타그램", "#여행에미치다", "#여기어디", "#인생샷", "#추억저장"]

    # 세션 생성 (2차 추천에서 컨텍스트로 활용)
    session_id = str(uuid.uuid4())[:8]
    sessions[session_id] = {
        "description": request.description,
        "hashtags": hashtags,
    }

    return HashtagResponse(
        hashtags=hashtags,
        session_id=session_id
    )


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """세션 정보 조회 (디버그용)"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
    return sessions[session_id]
