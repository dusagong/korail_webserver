"""
리뷰 API - CRUD + S3 이미지 업로드
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from database import get_db
from crud import (
    create_review,
    get_review_by_id,
    get_reviews_by_place,
    get_reviews_by_user,
    get_all_reviews,
    get_place_average_rating,
    update_review,
    delete_review,
)
from schemas.models import (
    ReviewResponse,
    ReviewListResponse,
    ReviewUpdate,
    PlaceRatingResponse,
)
from services.s3_service import s3_service

router = APIRouter(
    prefix="/api/v1/reviews",
    tags=["reviews"]
)


def _review_to_response(review) -> ReviewResponse:
    """DB Review 모델을 Response로 변환"""
    return ReviewResponse(
        id=review.id,
        place_id=review.place_id,
        place_name=review.place_name,
        rating=review.rating,
        content=review.content,
        user_id=review.user_id,
        photo_card_id=review.photo_card_id,
        image_urls=[img.image_url for img in sorted(review.images, key=lambda x: x.image_order)],
        created_at=review.created_at.isoformat() if review.created_at else "",
        updated_at=review.updated_at.isoformat() if review.updated_at else None,
    )


@router.post("", response_model=ReviewResponse)
async def create_review_endpoint(
    place_id: str = Form(...),
    place_name: str = Form(...),
    rating: int = Form(..., ge=1, le=5),
    content: str = Form(...),
    user_id: Optional[str] = Form(None),
    photo_card_id: Optional[str] = Form(None),
    images: list[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db)
):
    """
    리뷰 생성 (이미지 포함)

    - multipart/form-data로 전송
    - images: 최대 5장까지 이미지 업로드 가능
    """
    # 이미지 개수 제한
    if len(images) > 5:
        raise HTTPException(status_code=400, detail="이미지는 최대 5장까지 업로드 가능합니다")

    # S3에 이미지 업로드
    image_urls = []
    if images:
        try:
            image_urls = await s3_service.upload_images(images, folder="reviews")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"이미지 업로드 실패: {str(e)}")

    # 리뷰 생성
    try:
        review = await create_review(
            db=db,
            place_id=place_id,
            place_name=place_name,
            rating=rating,
            content=content,
            image_urls=image_urls,
            user_id=user_id,
            photo_card_id=photo_card_id,
        )
        return _review_to_response(review)
    except Exception as e:
        # 실패시 업로드된 이미지 삭제
        if image_urls:
            s3_service.delete_images(image_urls)
        raise HTTPException(status_code=500, detail=f"리뷰 생성 실패: {str(e)}")


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review_endpoint(
    review_id: str,
    db: AsyncSession = Depends(get_db)
):
    """리뷰 단건 조회"""
    review = await get_review_by_id(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다")
    return _review_to_response(review)


@router.get("/place/{place_id}", response_model=ReviewListResponse)
async def get_reviews_by_place_endpoint(
    place_id: str,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """장소별 리뷰 목록 조회"""
    reviews = await get_reviews_by_place(db, place_id, limit, offset)
    avg_rating, total_count = await get_place_average_rating(db, place_id)

    return ReviewListResponse(
        reviews=[_review_to_response(r) for r in reviews],
        total_count=total_count,
        average_rating=round(avg_rating, 1),
    )


@router.get("/user/{user_id}", response_model=ReviewListResponse)
async def get_reviews_by_user_endpoint(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """사용자별 리뷰 목록 조회 (내 리뷰)"""
    reviews = await get_reviews_by_user(db, user_id, limit, offset)

    # 사용자 리뷰의 평균 별점 계산
    if reviews:
        avg_rating = sum(r.rating for r in reviews) / len(reviews)
    else:
        avg_rating = 0.0

    return ReviewListResponse(
        reviews=[_review_to_response(r) for r in reviews],
        total_count=len(reviews),
        average_rating=round(avg_rating, 1),
    )


@router.get("", response_model=ReviewListResponse)
async def get_all_reviews_endpoint(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """전체 리뷰 목록 조회"""
    reviews = await get_all_reviews(db, limit, offset)

    # 전체 리뷰의 평균 별점 계산
    if reviews:
        avg_rating = sum(r.rating for r in reviews) / len(reviews)
    else:
        avg_rating = 0.0

    return ReviewListResponse(
        reviews=[_review_to_response(r) for r in reviews],
        total_count=len(reviews),
        average_rating=round(avg_rating, 1),
    )


@router.get("/place/{place_id}/rating", response_model=PlaceRatingResponse)
async def get_place_rating_endpoint(
    place_id: str,
    db: AsyncSession = Depends(get_db)
):
    """장소별 평점 조회"""
    avg_rating, review_count = await get_place_average_rating(db, place_id)
    return PlaceRatingResponse(
        place_id=place_id,
        average_rating=round(avg_rating, 1),
        review_count=review_count,
    )


@router.patch("/{review_id}", response_model=ReviewResponse)
async def update_review_endpoint(
    review_id: str,
    update_data: ReviewUpdate,
    db: AsyncSession = Depends(get_db)
):
    """리뷰 수정 (별점, 내용만)"""
    review = await update_review(
        db,
        review_id,
        rating=update_data.rating,
        content=update_data.content,
    )
    if not review:
        raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다")
    return _review_to_response(review)


@router.delete("/{review_id}")
async def delete_review_endpoint(
    review_id: str,
    db: AsyncSession = Depends(get_db)
):
    """리뷰 삭제"""
    # 삭제 전 이미지 URL 수집
    review = await get_review_by_id(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다")

    image_urls = [img.image_url for img in review.images]

    # DB에서 삭제
    success = await delete_review(db, review_id)
    if not success:
        raise HTTPException(status_code=500, detail="리뷰 삭제 실패")

    # S3에서 이미지 삭제
    if image_urls:
        s3_service.delete_images(image_urls)

    return {"success": True, "message": "리뷰가 삭제되었습니다"}
