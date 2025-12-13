# Implementation Status - PhotoCard Database Setup

**작성일**: 2025-12-13
**버전**: v0.2.0
**상태**: ✅ 구현 완료 (Docker + PostgreSQL + CRUD API)

---

## ✅ 구현 완료 항목

### 1. Docker 인프라 구성

#### 📁 `docker-compose.yml`
- PostgreSQL 15-alpine 컨테이너 설정
- FastAPI 애플리케이션 컨테이너 설정
- 헬스체크 및 의존성 관리
- Volume 설정 (`postgres_data`)
- 환경변수 주입 구조

#### 📁 `Dockerfile`
- Python 3.11-slim 베이스 이미지
- PostgreSQL 클라이언트 설치
- 의존성 설치 및 앱 복사
- 포트 8080 노출

#### 📁 `init.sql`
- `photo_cards` 테이블 스키마
- `meeting_platform_sessions` 테이블 스키마
- 인덱스 생성 (created_at, user_id, is_active, photo_card_id)
- 외래키 제약조건 (ON DELETE CASCADE)

### 2. Database Layer

#### 📁 `database.py`
- SQLAlchemy async engine 설정
- AsyncSession 팩토리
- `get_db()` 의존성 함수
- DEBUG 모드 지원 (echo=settings.debug)

#### 📁 `models/db_models.py`
- `PhotoCard` 모델 (UUID, province, city, message, hashtags, ai_quote, timestamps)
- `MeetingPlatformSession` 모델 (photo_card_id FK, query, area_code, sigungu_code)
- JSONB 타입 사용 (hashtags, recommendation_data)
- 자동 UUID 생성

#### 📁 `models/__init__.py`
- 모델 익스포트

### 3. CRUD Operations

#### 📁 `crud/photo_card_crud.py`
- `create_photo_card()` - PhotoCard 생성
- `get_photo_card()` - PhotoCard 조회 (활성 상태만)
- `verify_photo_card()` - PhotoCard 검증 (만남승강장 접근 제어용)

#### 📁 `crud/__init__.py`
- CRUD 함수 익스포트

### 4. API Endpoints

#### 📁 `routers/photo_card.py`
- **POST /api/v1/photo_cards** - PhotoCard 생성
  - 입력: province, city, message, hashtags, ai_quote
  - 출력: PhotoCardResponse (id, created_at 포함)
  - Note: AI 생성 기능은 미연동 (클라이언트에서 ai_quote 제공 필요)

- **GET /api/v1/photo_cards/{photo_card_id}** - PhotoCard 조회
  - 404 에러 처리

- **GET /api/v1/photo_cards/{photo_card_id}/verify** - PhotoCard 검증
  - 만남승강장 접근 전 호출
  - valid=True/False 반환

#### 📁 `routers/__init__.py`
- photo_card_router 익스포트 추가

### 5. Schemas

#### 📁 `schemas/models.py` (추가)
- `PhotoCardCreate` - PhotoCard 생성 요청 스키마
  - 예시 데이터 포함
  - 선택적 필드 지원 (user_id, message, hashtags, ai_quote, image_path)

- `PhotoCardResponse` - PhotoCard 응답 스키마
  - `from_attributes=True` 설정 (SQLAlchemy ORM 지원)
  - datetime → string 변환

### 6. 설정 파일

#### 📁 `config.py` (수정)
- `database_url` 필드 추가
- 기본값 설정 (localhost:5432)

#### 📁 `.env.example` (수정)
- `DATABASE_URL` 추가
- `DB_PASSWORD` 추가

#### 📁 `requirements.txt` (수정)
- `sqlalchemy==2.0.23` 추가
- `asyncpg==0.29.0` 추가
- `alembic==1.12.1` 추가

### 7. Main Application

#### 📁 `main.py` (수정)
- photo_card_router 등록
- API 설명 업데이트 (PostgreSQL 언급)
- 버전 0.2.0으로 업데이트
- 루트 엔드포인트에 photo_cards 추가

---

## ❌ 구현하지 않은 항목 (의도적 제외)

### 1. LLM 기반 AI 기능
**이유**: 아직 LLM 통합이 완전하지 않아 에러 발생 가능성이 높음

- ❌ AI 자동 해시태그 생성 (PhotoCard 생성 시)
- ❌ AI 감성 글귀 자동 생성
- ❌ PhotoCard 기반 자동 여행 추천

**대체 방안**:
- 클라이언트(Flutter)에서 `hashtags`와 `ai_quote`를 직접 제공
- 향후 LLM 안정화 후 서버 측 생성으로 전환 가능

### 2. MeetingPlatformSession 관련 API
**이유**: 아직 추천 시스템과의 통합 로직이 명확하지 않음

- ❌ Session 생성 API
- ❌ Session 기반 추천 캐싱
- ❌ Session 히스토리 조회

**향후 계획**:
- `/api/v1/ask` 엔드포인트와 통합 필요
- 추천 결과를 Session에 저장하는 로직 추가

### 3. Database Migration Tools
**이유**: 프로토타입 단계에서는 init.sql로 충분

- ❌ Alembic migration 스크립트
- ❌ 자동 마이그레이션 실행

**현재 상태**:
- Docker 컨테이너 초기화 시 `init.sql` 자동 실행
- 스키마 변경 시 컨테이너 재생성 필요

### 4. 고급 기능
**이유**: 현재 요구사항에 포함되지 않음

- ❌ PhotoCard 수정 (UPDATE)
- ❌ PhotoCard 삭제 (soft delete는 가능, 하드 삭제 미구현)
- ❌ PhotoCard 목록 조회 (pagination)
- ❌ 사용자별 PhotoCard 조회
- ❌ 이미지 업로드 처리
- ❌ PhotoCard 만료 처리 (expires_at 자동 체크)

---

## 🚀 실행 방법

### 1. 환경 설정

```bash
cd /Users/yoonseungjae/Documents/code/Seoul-Soft/hackerthon/travel-server

# .env 파일 생성 (예시)
cat > .env << EOF
LLM_BASE_URL=http://118.44.218.103:30000
TOUR_API_KEY=your_api_key_here
KORSERVICE_URL=https://apis.data.go.kr/B551011/KorService2
TARRLTE_URL=https://apis.data.go.kr/B551011/TarRlteTarService1
DATABASE_URL=postgresql+asyncpg://travel_user:password@postgres:5432/travel_db
DB_PASSWORD=your_secure_password
DEBUG=true
EOF
```

### 2. Docker Compose 실행

```bash
# 컨테이너 빌드 및 실행
docker-compose up -d --build

# 로그 확인
docker-compose logs -f

# DB 초기화 확인
docker-compose exec postgres psql -U travel_user -d travel_db -c "\dt"
```

**기대 출력**:
```
              List of relations
 Schema |           Name            | Type  |   Owner
--------+---------------------------+-------+------------
 public | meeting_platform_sessions | table | travel_user
 public | photo_cards               | table | travel_user
```

### 3. API 테스트

#### PhotoCard 생성
```bash
curl -X POST http://localhost:8080/api/v1/photo_cards \
  -H "Content-Type: application/json" \
  -d '{
    "province": "강원도",
    "city": "강릉시",
    "message": "강릉에서의 특별한 하루",
    "hashtags": ["맛집탐방", "카페투어", "해변산책"],
    "ai_quote": "사랑하는 사람과 함께하는 모든 순간이 기적이 됩니다"
  }'
```

**응답 예시**:
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "province": "강원도",
  "city": "강릉시",
  "message": "강릉에서의 특별한 하루",
  "hashtags": ["맛집탐방", "카페투어", "해변산책"],
  "ai_quote": "사랑하는 사람과 함께하는 모든 순간이 기적이 됩니다",
  "created_at": "2025-12-13T14:30:00.123456",
  "is_active": true
}
```

#### PhotoCard 검증
```bash
curl http://localhost:8080/api/v1/photo_cards/a1b2c3d4-e5f6-7890-abcd-ef1234567890/verify
```

**응답 예시**:
```json
{
  "valid": true,
  "photo_card_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### 4. API 문서 확인

브라우저에서 접속:
- http://localhost:8080/docs (Swagger UI)
- http://localhost:8080/redoc (ReDoc)

---

## 🔧 개발 환경 (로컬 실행)

Docker 없이 로컬에서 실행하려면:

```bash
# PostgreSQL 직접 설치 및 실행
brew install postgresql@15
brew services start postgresql@15

# 데이터베이스 생성
createdb -U postgres travel_db
psql -U postgres -d travel_db -f init.sql

# Python 가상환경
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# .env 파일에서 DATABASE_URL 수정
# DATABASE_URL=postgresql+asyncpg://postgres:@localhost:5432/travel_db

# 서버 실행
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

---

## 📊 데이터베이스 스키마

### photo_cards

| Column      | Type         | Constraints       |
|-------------|--------------|-------------------|
| id          | VARCHAR(36)  | PRIMARY KEY       |
| user_id     | VARCHAR(100) | INDEX             |
| province    | VARCHAR(50)  | NOT NULL          |
| city        | VARCHAR(50)  | NOT NULL          |
| message     | TEXT         |                   |
| hashtags    | JSONB        |                   |
| ai_quote    | TEXT         |                   |
| image_path  | VARCHAR(255) |                   |
| created_at  | TIMESTAMP    | DEFAULT NOW, INDEX|
| expires_at  | TIMESTAMP    |                   |
| is_active   | BOOLEAN      | DEFAULT TRUE, INDEX|

### meeting_platform_sessions

| Column               | Type         | Constraints       |
|----------------------|--------------|-------------------|
| id                   | VARCHAR(36)  | PRIMARY KEY       |
| photo_card_id        | VARCHAR(36)  | FK, NOT NULL, INDEX|
| query                | TEXT         |                   |
| area_code            | VARCHAR(10)  |                   |
| sigungu_code         | VARCHAR(10)  |                   |
| recommendation_data  | JSONB        |                   |
| created_at           | TIMESTAMP    | DEFAULT NOW       |
| last_accessed_at     | TIMESTAMP    | DEFAULT NOW, INDEX|

---

## 🐛 알려진 이슈

### 1. datetime 직렬화
- SQLAlchemy `DateTime` → Pydantic `str` 변환 수동 처리
- `created_at.isoformat()` 사용
- 향후 자동 변환 로직 추가 가능

### 2. Docker Compose 볼륨
- 스키마 변경 시 볼륨 삭제 필요:
  ```bash
  docker-compose down -v
  docker-compose up -d --build
  ```

### 3. 환경변수 누락 시 에러
- `.env` 파일이 없으면 FastAPI 시작 실패
- `.env.example`을 참고하여 `.env` 생성 필수

---

## 📝 향후 작업

### 단기 (1-2주)
1. ✅ PostgreSQL + Docker 설정 완료
2. ⏳ Flutter 앱과 API 연동 테스트
3. ⏳ MeetingPlatformSession과 `/api/v1/ask` 통합
4. ⏳ 이미지 업로드 기능 (S3 or 로컬 스토리지)

### 중기 (1개월)
1. ⏳ AI 자동 해시태그 생성 (LLM 안정화 후)
2. ⏳ AI 감성 글귀 생성
3. ⏳ PhotoCard 기반 추천 히스토리
4. ⏳ Alembic migration 도입

### 장기 (2개월+)
1. ⏳ 사용자 인증 시스템 (JWT)
2. ⏳ PhotoCard 공유 기능
3. ⏳ 관리자 대시보드
4. ⏳ 프로덕션 배포 (Oracle Cloud)

---

## 📂 생성된 파일 목록

```
travel-server/
├── docker-compose.yml          # ✅ 신규
├── Dockerfile                  # ✅ 신규
├── init.sql                    # ✅ 신규
├── database.py                 # ✅ 신규
├── requirements.txt            # ✏️ 수정
├── config.py                   # ✏️ 수정
├── .env.example                # ✏️ 수정
├── main.py                     # ✏️ 수정
├── models/                     # ✅ 신규 디렉토리
│   ├── __init__.py             # ✅ 신규
│   └── db_models.py            # ✅ 신규
├── crud/                       # ✅ 신규 디렉토리
│   ├── __init__.py             # ✅ 신규
│   └── photo_card_crud.py      # ✅ 신규
├── routers/
│   ├── __init__.py             # ✏️ 수정
│   └── photo_card.py           # ✅ 신규
└── schemas/
    └── models.py               # ✏️ 수정 (PhotoCard 스키마 추가)
```

---

## ✅ 체크리스트

- [x] PostgreSQL Docker 설정
- [x] SQLAlchemy 모델 정의
- [x] CRUD 함수 구현
- [x] API 엔드포인트 추가
- [x] Docker Compose 설정
- [x] init.sql 스키마 작성
- [ ] Flutter 앱 연동 (다음 단계)
- [ ] 에러 핸들링 강화
- [ ] 로깅 설정
- [ ] 성능 모니터링

---

**마지막 업데이트**: 2025-12-13
**작성자**: Claude
**문의**: DATABASE_SETUP_PLAN.md 및 MOBILE_INTEGRATION_PLAN.md 참고
