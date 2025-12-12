# Travel Hashtag Service - 프로젝트 현황

## 서비스 개요

사진 설명 → 해시태그 생성 → 맞춤 여행 코스 추천

```
모바일 앱 ──► Oracle Cloud (웹서버) ──► DIGITS PC (LLM)
                    │
                    └──► 한국관광공사 API
```

---

## 완료된 작업

### 1. 아키텍처 설계

| 서버 | 역할 | 기술스택 |
|------|------|----------|
| Oracle Cloud (Free Tier) | API Gateway, 관광 API 호출 | FastAPI |
| DIGITS PC | LLM 추론 (EXAONE 32B) | vLLM (예정) |

### 2. 웹서버 구현 (`travel-server/`)

```
travel-server/
├── main.py                 # FastAPI 앱
├── config.py               # 환경변수 설정
├── requirements.txt        # 의존성
├── .env.example            # 환경변수 예시
├── routers/
│   ├── hashtag.py          # POST /api/v1/hashtag
│   └── recommend.py        # POST /api/v1/recommend
├── services/
│   ├── llm_client.py       # DIGITS LLM 클라이언트
│   └── tour_api.py         # 한국관광공사 API
└── schemas/
    └── models.py           # Request/Response 모델
```

### 3. API 명세

#### 1차: 해시태그 생성
```http
POST /api/v1/hashtag
Content-Type: application/json

{
  "description": "오늘 강릉 바다 왔어요 날씨 좋고 커피도 맛있음"
}
```
```json
{
  "hashtags": ["#강릉여행", "#바다스타그램", "#커피는사랑", "#여기어디게", "#인생뷰"],
  "session_id": "abc123"
}
```

#### 2차: 여행 추천
```http
POST /api/v1/recommend
Content-Type: application/json

{
  "session_id": "abc123",
  "destination": "강릉",
  "preferences": {
    "theme": "바다",
    "with_whom": "연인",
    "style": "여유롭게"
  }
}
```

---

## 진행 예정 작업

### Phase 1: 로컬 테스트

- [ ] `.env` 파일 생성 및 API 키 설정
- [ ] 웹서버 로컬 실행 테스트
- [ ] LLM 없이 폴백 모드로 API 테스트

### Phase 2: DIGITS PC 설정

- [ ] vLLM 또는 text-generation-inference 설치
- [ ] EXAONE 32B 모델 로드
- [ ] OpenAI 호환 API 엔드포인트 노출
- [ ] 웹서버 ↔ DIGITS 연동 테스트

### Phase 3: Oracle Cloud 배포

- [ ] Oracle Cloud 인스턴스 접속
- [ ] Docker 또는 직접 배포
- [ ] 방화벽/보안그룹 설정 (8080 포트)
- [ ] DIGITS PC와 네트워크 연결 (VPN 또는 공인IP)

### Phase 4: 모바일 연동

- [ ] 모바일 앱에서 API 호출 테스트
- [ ] 응답 형식 조정 (필요시)
- [ ] 에러 핸들링 개선

---

## 환경 설정

### 필요한 환경변수 (`.env`)

```env
# DIGITS LLM Server
LLM_BASE_URL=http://<DIGITS_IP>:8000

# 한국관광공사 API
KORSERVICE_URL=https://apis.data.go.kr/B551011/KorService2
TARRLTE_URL=https://apis.data.go.kr/B551011/TarRlteTarService1
TOUR_API_KEY=your_api_key_here

# App
DEBUG=true
```

### 로컬 실행

```bash
cd travel-server
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# .env 편집
python main.py
```

서버 실행 후: http://localhost:8080/docs

---

## 인프라 구성

```
┌─────────────────────────────────────────────────────────────┐
│                        인터넷                                │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│    Oracle Cloud         │     │      DIGITS PC          │
│    (Free Tier)          │     │                         │
├─────────────────────────┤     ├─────────────────────────┤
│ • FastAPI (8080)        │────►│ • vLLM (8000)           │
│ • 관광 API 프록시        │     │ • EXAONE 32B            │
│ • 세션 관리             │     │                         │
└─────────────────────────┘     └─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│   한국관광공사 API       │
│ • KorService2           │
│ • TarRlteTarService1    │
└─────────────────────────┘
```

---

## 참고 자료

- [api_test/](./api_test/) - 기존 관광 API 테스트 코드
- [api_test/README.md](./api_test/README.md) - API 상세 문서
