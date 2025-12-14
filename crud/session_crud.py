from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.sql import func
from models.db_models import MeetingPlatformSession
from typing import Optional
import uuid


async def create_session(
    db: AsyncSession,
    photo_card_id: str,
    query: str,
    area_code: Optional[str] = None,
    sigungu_code: Optional[str] = None
) -> MeetingPlatformSession:
    """세션 생성 (pending 상태)"""
    session = MeetingPlatformSession(
        id=str(uuid.uuid4()),
        photo_card_id=photo_card_id,
        status="pending",
        query=query,
        area_code=area_code,
        sigungu_code=sigungu_code,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session_by_photo_card_id(
    db: AsyncSession,
    photo_card_id: str
) -> Optional[MeetingPlatformSession]:
    """포토카드 ID로 세션 조회"""
    result = await db.execute(
        select(MeetingPlatformSession).where(
            MeetingPlatformSession.photo_card_id == photo_card_id
        )
    )
    return result.scalar_one_or_none()


async def get_session_by_id(
    db: AsyncSession,
    session_id: str
) -> Optional[MeetingPlatformSession]:
    """세션 ID로 조회"""
    result = await db.execute(
        select(MeetingPlatformSession).where(
            MeetingPlatformSession.id == session_id
        )
    )
    return result.scalar_one_or_none()


async def update_session_status(
    db: AsyncSession,
    session_id: str,
    status: str,
    recommendation_data: Optional[dict] = None,
    error_message: Optional[str] = None
) -> Optional[MeetingPlatformSession]:
    """세션 상태 업데이트"""
    update_data = {"status": status}

    if status == "completed" and recommendation_data:
        update_data["recommendation_data"] = recommendation_data
        update_data["completed_at"] = func.now()
    elif status == "failed" and error_message:
        update_data["error_message"] = error_message

    await db.execute(
        update(MeetingPlatformSession)
        .where(MeetingPlatformSession.id == session_id)
        .values(**update_data)
    )
    await db.commit()

    return await get_session_by_id(db, session_id)


async def update_last_accessed(
    db: AsyncSession,
    session_id: str
) -> None:
    """마지막 접근 시간 업데이트"""
    await db.execute(
        update(MeetingPlatformSession)
        .where(MeetingPlatformSession.id == session_id)
        .values(last_accessed_at=func.now())
    )
    await db.commit()
