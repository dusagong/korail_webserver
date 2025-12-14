from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas.models import PhotoCardCreate, PhotoCardResponse
from crud import photo_card_crud, create_session
from services import start_recommendation_task

router = APIRouter(
    prefix="/api/v1/photo_cards",
    tags=["photo_cards"]
)


@router.post("", response_model=PhotoCardResponse)
async def create_photo_card(
    photo_card: PhotoCardCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    PhotoCard 생성 + 추천 요청 시작

    - **province**: 도/광역시 (예: "강원도")
    - **city**: 시/군/구 (예: "강릉시")
    - **message**: 사용자 메시지
    - **hashtags**: 해시태그 리스트
    - **ai_quote**: AI 생성 감성 글귀 (선택사항)
    - **area_code**: 도/광역시 코드 (예: "32")
    - **sigungu_code**: 시/군/구 코드 (예: "1")

    포토카드 생성 시 자동으로 추천 요청이 백그라운드에서 시작됩니다.
    session_id를 사용해서 추천 상태를 조회할 수 있습니다.
    """
    # 1. 포토카드 생성
    db_photo_card = await photo_card_crud.create_photo_card(db, photo_card)

    # 2. 추천 쿼리 생성
    query = _build_recommendation_query(photo_card)

    # 3. 세션 생성 (area_code, sigungu_code가 있을 때만)
    session_id = None
    if photo_card.area_code and photo_card.sigungu_code:
        session = await create_session(
            db=db,
            photo_card_id=db_photo_card.id,
            query=query,
            area_code=photo_card.area_code,
            sigungu_code=photo_card.sigungu_code
        )
        session_id = session.id

        # 4. 백그라운드 추천 요청 시작
        start_recommendation_task(
            session_id=session.id,
            query=query,
            area_code=photo_card.area_code,
            sigungu_code=photo_card.sigungu_code
        )
        print(f"[PhotoCard] Created {db_photo_card.id}, session {session_id} started")

    # 5. 응답 반환
    response_data = PhotoCardResponse(
        id=db_photo_card.id,
        province=db_photo_card.province,
        city=db_photo_card.city,
        message=db_photo_card.message,
        hashtags=db_photo_card.hashtags,
        ai_quote=db_photo_card.ai_quote,
        created_at=db_photo_card.created_at.isoformat(),
        is_active=db_photo_card.is_active,
        session_id=session_id
    )

    return response_data


def _build_recommendation_query(photo_card: PhotoCardCreate) -> str:
    """포토카드 정보로 추천 쿼리 생성"""
    message = photo_card.message or ""

    if message:
        return message
    else:
        return f"{photo_card.city}에서 커플 데이트 코스 추천해줘"


@router.get("/{photo_card_id}", response_model=PhotoCardResponse)
async def get_photo_card(
    photo_card_id: str,
    db: AsyncSession = Depends(get_db)
):
    """PhotoCard 조회"""
    photo_card = await photo_card_crud.get_photo_card(db, photo_card_id)
    if not photo_card:
        raise HTTPException(status_code=404, detail="PhotoCard not found")

    # Convert datetime to string for response
    response_data = PhotoCardResponse(
        id=photo_card.id,
        province=photo_card.province,
        city=photo_card.city,
        message=photo_card.message,
        hashtags=photo_card.hashtags,
        ai_quote=photo_card.ai_quote,
        created_at=photo_card.created_at.isoformat(),
        is_active=photo_card.is_active
    )

    return response_data


@router.get("/{photo_card_id}/verify")
async def verify_photo_card(
    photo_card_id: str,
    db: AsyncSession = Depends(get_db)
):
    """PhotoCard 검증 (만남승강장 접근 전)"""
    is_valid = await photo_card_crud.verify_photo_card(db, photo_card_id)
    if not is_valid:
        raise HTTPException(
            status_code=404,
            detail="Invalid or inactive PhotoCard"
        )
    return {"valid": True, "photo_card_id": photo_card_id}
