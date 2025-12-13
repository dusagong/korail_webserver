from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from routers import hashtag_router, recommend_router, photo_card_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="""
## Travel Hashtag Service

사진 설명으로 해시태그 생성 + 맞춤 여행 코스 추천 + PhotoCard 관리

### 흐름
1. **POST /api/v1/hashtag** - 여행 설명 → 재밌는 해시태그 생성
2. **POST /api/v1/recommend** - 목적지 + 취향 → 여행 코스 추천
3. **POST /api/v1/photo_cards** - PhotoCard 생성 (만남승강장 접근용)
4. **GET /api/v1/photo_cards/{id}/verify** - PhotoCard 검증

### 사용 API
- **EXAONE 32B** (DIGITS PC) - 자연어 처리
- **KorService2** - 한국관광공사 관광정보
- **TarRlteTarService1** - 연관 관광지 (Tmap 이동 데이터)
- **PostgreSQL** - PhotoCard 저장소
    """,
    version="0.2.0",
)

# CORS 설정 (모바일 앱 연동용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(hashtag_router)
app.include_router(recommend_router)
app.include_router(photo_card_router)


@app.get("/")
async def root():
    return {
        "service": settings.app_name,
        "version": "0.2.0",
        "endpoints": {
            "hashtag": "/api/v1/hashtag",
            "recommend": "/api/v1/recommend",
            "photo_cards": "/api/v1/photo_cards",
            "docs": "/docs",
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
