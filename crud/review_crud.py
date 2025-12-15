"""
리뷰 CRUD 함수
"""
from typing import Optional
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from models.db_models import Review, ReviewImage


async def create_review(
    db: AsyncSession,
    place_id: str,
    place_name: str,
    rating: int,
    content: str,
    image_urls: list[str],
    user_id: Optional[str] = None,
    photo_card_id: Optional[str] = None,
) -> Review:
    """리뷰 생성"""
    review = Review(
        place_id=place_id,
        place_name=place_name,
        rating=rating,
        content=content,
        user_id=user_id,
        photo_card_id=photo_card_id,
    )
    db.add(review)
    await db.flush()  # ID 생성을 위해 flush

    # 이미지 추가
    for i, url in enumerate(image_urls):
        image = ReviewImage(
            review_id=review.id,
            image_url=url,
            image_order=i,
        )
        db.add(image)

    await db.commit()
    await db.refresh(review)

    # 이미지와 함께 다시 로드
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.images))
        .where(Review.id == review.id)
    )
    return result.scalar_one()


async def get_review_by_id(
    db: AsyncSession,
    review_id: str
) -> Optional[Review]:
    """리뷰 ID로 조회"""
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.images))
        .where(Review.id == review_id, Review.is_deleted == False)
    )
    return result.scalar_one_or_none()


async def get_reviews_by_place(
    db: AsyncSession,
    place_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[Review]:
    """장소별 리뷰 목록 조회"""
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.images))
        .where(Review.place_id == place_id, Review.is_deleted == False)
        .order_by(desc(Review.created_at))
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_reviews_by_user(
    db: AsyncSession,
    user_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[Review]:
    """사용자별 리뷰 목록 조회"""
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.images))
        .where(Review.user_id == user_id, Review.is_deleted == False)
        .order_by(desc(Review.created_at))
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_all_reviews(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
) -> list[Review]:
    """전체 리뷰 목록 조회"""
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.images))
        .where(Review.is_deleted == False)
        .order_by(desc(Review.created_at))
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_place_average_rating(
    db: AsyncSession,
    place_id: str
) -> tuple[float, int]:
    """장소별 평균 별점과 리뷰 수 조회"""
    result = await db.execute(
        select(
            func.avg(Review.rating).label("avg_rating"),
            func.count(Review.id).label("count")
        )
        .where(Review.place_id == place_id, Review.is_deleted == False)
    )
    row = result.one()
    avg_rating = float(row.avg_rating) if row.avg_rating else 0.0
    count = row.count or 0
    return avg_rating, count


async def update_review(
    db: AsyncSession,
    review_id: str,
    rating: Optional[int] = None,
    content: Optional[str] = None,
) -> Optional[Review]:
    """리뷰 수정"""
    review = await get_review_by_id(db, review_id)
    if not review:
        return None

    if rating is not None:
        review.rating = rating
    if content is not None:
        review.content = content

    await db.commit()
    await db.refresh(review)
    return review


async def delete_review(
    db: AsyncSession,
    review_id: str,
    soft_delete: bool = True
) -> bool:
    """리뷰 삭제 (소프트 삭제)"""
    review = await get_review_by_id(db, review_id)
    if not review:
        return False

    if soft_delete:
        review.is_deleted = True
        await db.commit()
    else:
        await db.delete(review)
        await db.commit()

    return True


async def add_review_images(
    db: AsyncSession,
    review_id: str,
    image_urls: list[str],
    start_order: int = 0,
) -> list[ReviewImage]:
    """리뷰에 이미지 추가"""
    images = []
    for i, url in enumerate(image_urls):
        image = ReviewImage(
            review_id=review_id,
            image_url=url,
            image_order=start_order + i,
        )
        db.add(image)
        images.append(image)

    await db.commit()
    return images


async def delete_review_image(
    db: AsyncSession,
    image_id: str
) -> bool:
    """리뷰 이미지 삭제"""
    result = await db.execute(
        select(ReviewImage).where(ReviewImage.id == image_id)
    )
    image = result.scalar_one_or_none()
    if not image:
        return False

    await db.delete(image)
    await db.commit()
    return True
