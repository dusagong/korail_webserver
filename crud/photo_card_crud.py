from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.db_models import PhotoCard
from schemas.models import PhotoCardCreate
from typing import Optional
import uuid


async def create_photo_card(db: AsyncSession, photo_card: PhotoCardCreate) -> PhotoCard:
    """PhotoCard 생성"""
    db_photo_card = PhotoCard(
        id=str(uuid.uuid4()),
        user_id=photo_card.user_id,
        province=photo_card.province,
        city=photo_card.city,
        message=photo_card.message,
        hashtags=photo_card.hashtags,
        ai_quote=photo_card.ai_quote,
        image_path=photo_card.image_path,
    )
    db.add(db_photo_card)
    await db.commit()
    await db.refresh(db_photo_card)
    return db_photo_card


async def get_photo_card(db: AsyncSession, photo_card_id: str) -> Optional[PhotoCard]:
    """PhotoCard 조회"""
    result = await db.execute(
        select(PhotoCard).where(
            PhotoCard.id == photo_card_id,
            PhotoCard.is_active == True
        )
    )
    return result.scalar_one_or_none()


async def verify_photo_card(db: AsyncSession, photo_card_id: str) -> bool:
    """PhotoCard 존재 및 활성 상태 검증"""
    photo_card = await get_photo_card(db, photo_card_id)
    return photo_card is not None
