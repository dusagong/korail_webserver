# Database Setup Plan - PhotoCard 식별코드 관리

## 📋 요구사항

1. **PhotoCard 생성 시 DB 저장**
   - 모바일에서 PhotoCard 생성 → travel-server DB에 저장
   - 고유 식별코드 (UUID) 발급

2. **만남승강장 접근 제어**
   - PhotoCard ID를 통해서만 만남승강장 접근 가능
   - ID 검증 후 여행 추천 데이터 제공

3. **Docker 기반 DB 관리**
   - PostgreSQL 또는 SQLite 사용
   - Docker Compose로 통합 관리

---

## 🗄️ 데이터베이스 설계

### 테이블: `photo_cards`

```sql
CREATE TABLE photo_cards (
    id VARCHAR(36) PRIMARY KEY,           -- UUID
    user_id VARCHAR(100),                 -- 사용자 식별자 (선택)
    province VARCHAR(50) NOT NULL,        -- 도/광역시
    city VARCHAR(50) NOT NULL,            -- 시/군/구
    message TEXT,                         -- 사용자 메시지
    hashtags JSON,                        -- 해시태그 배열
    ai_quote TEXT,                        -- AI 생성 감성 글귀
    image_path VARCHAR(255),              -- 사진 경로 (선택)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,                 -- 만료 시간 (선택)
    is_active BOOLEAN DEFAULT TRUE,       -- 활성 상태

    INDEX idx_created_at (created_at),
    INDEX idx_user_id (user_id)
);
```

### 테이블: `meeting_platform_sessions`

```sql
CREATE TABLE meeting_platform_sessions (
    id VARCHAR(36) PRIMARY KEY,
    photo_card_id VARCHAR(36) NOT NULL,
    query TEXT,                           -- 사용자 쿼리
    area_code VARCHAR(10),
    sigungu_code VARCHAR(10),
    recommendation_data JSON,             -- 추천 결과 캐싱
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (photo_card_id) REFERENCES photo_cards(id) ON DELETE CASCADE,
    INDEX idx_photo_card_id (photo_card_id)
);
```

---

## 🐳 Docker 구성

### `docker-compose.yml` (travel-server 프로젝트에 추가)

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: travel-server-db
    environment:
      POSTGRES_DB: travel_db
      POSTGRES_USER: travel_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U travel_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  # FastAPI Application
  travel-server:
    build: .
    container_name: travel-server-app
    environment:
      - DATABASE_URL=postgresql://travel_user:${DB_PASSWORD}@postgres:5432/travel_db
      - LLM_BASE_URL=${LLM_BASE_URL}
      - TOUR_API_KEY=${TOUR_API_KEY}
    ports:
      - "8080:8080"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - .:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8080 --reload
    restart: unless-stopped

volumes:
  postgres_data:
```

### `init.sql` (초기 스키마)

```sql
-- PhotoCards 테이블
CREATE TABLE IF NOT EXISTS photo_cards (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(100),
    province VARCHAR(50) NOT NULL,
    city VARCHAR(50) NOT NULL,
    message TEXT,
    hashtags JSONB,
    ai_quote TEXT,
    image_path VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_photo_cards_created_at ON photo_cards(created_at);
CREATE INDEX idx_photo_cards_user_id ON photo_cards(user_id);
CREATE INDEX idx_photo_cards_active ON photo_cards(is_active);

-- Meeting Platform Sessions 테이블
CREATE TABLE IF NOT EXISTS meeting_platform_sessions (
    id VARCHAR(36) PRIMARY KEY,
    photo_card_id VARCHAR(36) NOT NULL,
    query TEXT,
    area_code VARCHAR(10),
    sigungu_code VARCHAR(10),
    recommendation_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (photo_card_id) REFERENCES photo_cards(id) ON DELETE CASCADE
);

CREATE INDEX idx_sessions_photo_card_id ON meeting_platform_sessions(photo_card_id);
CREATE INDEX idx_sessions_last_accessed ON meeting_platform_sessions(last_accessed_at);
```

### `Dockerfile` (travel-server)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 코드 복사
COPY . .

# 포트 노출
EXPOSE 8080

# 실행 명령
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### `requirements.txt` (추가 필요)

```txt
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
httpx>=0.25.0
python-dotenv>=1.0.0
pydantic>=2.4.0
pydantic-settings>=2.0.0

# Database
sqlalchemy>=2.0.0
asyncpg>=0.29.0           # PostgreSQL async driver
alembic>=1.12.0           # DB migration tool
```

---

## 📝 코드 구현

### 1. Database 설정

**파일 생성**: `database.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import get_settings

settings = get_settings()

# PostgreSQL Async Engine
engine = create_async_engine(
    settings.database_url,
    echo=True,  # 개발 환경에서만
    future=True,
)

# Session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

# Dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

### 2. Models

**파일 생성**: `models/db_models.py`

```python
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
    __tablename__ = "meeting_platform_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    photo_card_id = Column(String(36), ForeignKey("photo_cards.id", ondelete="CASCADE"), nullable=False, index=True)
    query = Column(Text, nullable=True)
    area_code = Column(String(10), nullable=True)
    sigungu_code = Column(String(10), nullable=True)
    recommendation_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

### 3. CRUD Operations

**파일 생성**: `crud/photo_card_crud.py`

```python
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
```

### 4. API Endpoints

**파일 수정**: `routers/photo_card.py` (신규 생성)

```python
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas.models import PhotoCardCreate, PhotoCardResponse
from crud import photo_card_crud

router = APIRouter(prefix="/api/v1/photo_cards", tags=["photo_cards"])

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
    - **ai_quote**: AI 생성 감성 글귀
    """
    db_photo_card = await photo_card_crud.create_photo_card(db, photo_card)
    return db_photo_card

@router.get("/{photo_card_id}", response_model=PhotoCardResponse)
async def get_photo_card(
    photo_card_id: str,
    db: AsyncSession = Depends(get_db)
):
    """PhotoCard 조회"""
    photo_card = await photo_card_crud.get_photo_card(db, photo_card_id)
    if not photo_card:
        raise HTTPException(status_code=404, detail="PhotoCard not found")
    return photo_card

@router.get("/{photo_card_id}/verify")
async def verify_photo_card(
    photo_card_id: str,
    db: AsyncSession = Depends(get_db)
):
    """PhotoCard 검증 (만남승강장 접근 전)"""
    is_valid = await photo_card_crud.verify_photo_card(db, photo_card_id)
    if not is_valid:
        raise HTTPException(status_code=404, detail="Invalid or inactive PhotoCard")
    return {"valid": True, "photo_card_id": photo_card_id}
```

### 5. Schemas 추가

**파일 수정**: `schemas/models.py` (추가)

```python
# PhotoCard 관련 스키마
class PhotoCardCreate(BaseModel):
    user_id: Optional[str] = None
    province: str
    city: str
    message: Optional[str] = None
    hashtags: Optional[list[str]] = None
    ai_quote: Optional[str] = None
    image_path: Optional[str] = None

class PhotoCardResponse(BaseModel):
    id: str
    province: str
    city: str
    message: Optional[str]
    hashtags: Optional[list[str]]
    ai_quote: Optional[str]
    created_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}
```

### 6. Main.py 수정

```python
from routers import hashtag_router, recommend_router, photo_card_router

# 라우터 등록
app.include_router(hashtag_router)
app.include_router(recommend_router)
app.include_router(photo_card_router)  # 추가
```

### 7. Config 수정

**파일 수정**: `config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Travel Hashtag Service"
    llm_base_url: str
    llm_timeout: int = 60
    tour_api_key: str
    database_url: str  # 추가

    class Config:
        env_file = ".env"

def get_settings():
    return Settings()
```

### 8. .env 파일 업데이트

```env
LLM_BASE_URL=http://118.44.218.103:30000
TOUR_API_KEY=your_api_key_here
DATABASE_URL=postgresql+asyncpg://travel_user:password@localhost:5432/travel_db
DB_PASSWORD=your_secure_password
```

---

## 🚀 실행 방법

### 1. Docker Compose 실행

```bash
cd /Users/yoonseungjae/Documents/code/Seoul-Soft/hackerthon/travel-server

# .env 파일 확인
cat .env

# Docker Compose 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# DB 초기화 확인
docker-compose exec postgres psql -U travel_user -d travel_db -c "\dt"
```

### 2. Migration (선택사항 - Alembic 사용)

```bash
# Alembic 초기화
alembic init alembic

# Migration 생성
alembic revision --autogenerate -m "Create photo_cards table"

# Migration 적용
alembic upgrade head
```

---

## 📱 Flutter 앱 연동

### PhotoCard 생성 API 호출

```dart
Future<String> createPhotoCard({
  required String province,
  required String city,
  required String message,
  required List<String> hashtags,
  required String aiQuote,
}) async {
  final response = await http.post(
    Uri.parse('$baseUrl/api/v1/photo_cards'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({
      'province': province,
      'city': city,
      'message': message,
      'hashtags': hashtags,
      'ai_quote': aiQuote,
    }),
  );

  if (response.statusCode != 200) {
    throw Exception('Failed to create photo card');
  }

  final data = jsonDecode(utf8.decode(response.bodyBytes));
  return data['id'];  // PhotoCard ID 반환
}
```

### 만남승강장 접근 시 검증

```dart
Future<bool> verifyPhotoCard(String photoCardId) async {
  final response = await http.get(
    Uri.parse('$baseUrl/api/v1/photo_cards/$photoCardId/verify'),
  );

  if (response.statusCode != 200) {
    return false;
  }

  final data = jsonDecode(response.body);
  return data['valid'] == true;
}
```

---

## 🔄 데이터 흐름

```
1. PhotoCard 생성 (Flutter)
   ↓
2. POST /api/v1/photo_cards
   ↓
3. DB에 저장 (UUID 생성)
   ↓
4. PhotoCard ID 반환
   ↓
5. 만남승강장 접근 (Flutter)
   ↓
6. GET /api/v1/photo_cards/{id}/verify
   ↓
7. DB에서 PhotoCard 검증
   ↓
8. 검증 성공 시 추천 API 호출 허용
   ↓
9. POST /api/v1/ask (area_code, sigungu_code 포함)
```

---

## ✅ 체크리스트

- [ ] PostgreSQL Docker 설정
- [ ] SQLAlchemy 모델 정의
- [ ] CRUD 함수 구현
- [ ] API 엔드포인트 추가
- [ ] Docker Compose 테스트
- [ ] Migration 스크립트 작성
- [ ] Flutter 앱 연동
- [ ] 에러 핸들링 추가
- [ ] 로깅 설정
- [ ] 성능 모니터링

---

**작성일**: 2025-12-13
**상태**: 계획 단계 (구현 대기)
