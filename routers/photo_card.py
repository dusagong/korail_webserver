from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas.models import PhotoCardCreate, PhotoCardResponse
from crud import photo_card_crud

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
    PhotoCard 생성

    - **province**: 도/광역시 (예: "강원도")
    - **city**: 시/군/구 (예: "강릉시")
    - **message**: 사용자 메시지
    - **hashtags**: 해시태그 리스트
    - **ai_quote**: AI 생성 감성 글귀 (선택사항)

    Note: AI 생성 기능은 아직 미연동 상태입니다.
    클라이언트에서 ai_quote를 직접 제공해야 합니다.
    """
    db_photo_card = await photo_card_crud.create_photo_card(db, photo_card)

    # Convert datetime to string for response
    response_data = PhotoCardResponse(
        id=db_photo_card.id,
        province=db_photo_card.province,
        city=db_photo_card.city,
        message=db_photo_card.message,
        hashtags=db_photo_card.hashtags,
        ai_quote=db_photo_card.ai_quote,
        created_at=db_photo_card.created_at.isoformat(),
        is_active=db_photo_card.is_active
    )

    return response_data


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
