from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from database import Base
import uuid


class PhotoCard(Base):
    __tablename__ = "photo_cards"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(100), nullable=True, index=True)
    province = Column(String(50), nullable=False)
    city = Column(String(50), nullable=False)
    message = Column(Text, nullable=True)
    hashtags = Column(JSONB, nullable=True)
    ai_quote = Column(Text, nullable=True)
    image_path = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, index=True)


class MeetingPlatformSession(Base):
    """
    만남승강장 세션 - 포토카드별 추천 결과 저장

    Status:
    - pending: 추천 요청 대기중
    - processing: LLM 처리중
    - completed: 완료
    - failed: 실패
    """
    __tablename__ = "meeting_platform_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    photo_card_id = Column(
        String(36),
        ForeignKey("photo_cards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True  # 포토카드당 하나의 세션만
    )
    status = Column(String(20), default="pending", nullable=False, index=True)
    query = Column(Text, nullable=True)
    area_code = Column(String(10), nullable=True)
    sigungu_code = Column(String(10), nullable=True)
    recommendation_data = Column(JSONB, nullable=True)  # spots, course 저장
    error_message = Column(Text, nullable=True)  # 실패시 에러 메시지
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)  # 완료 시각
    last_accessed_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
