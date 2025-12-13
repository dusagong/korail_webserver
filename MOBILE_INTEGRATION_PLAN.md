# Mobile Integration Plan - Flutter App ↔ travel-server

## 📱 현재 상황

### Flutter App 구조
- **위치**: `/Users/yoonseungjae/Documents/code/Seoul-Soft/hackerthon/FCM_APP-Flutter-with-AOS-IOS-`
- **상태**: 샘플 데이터 사용 중 (실제 API 연동 없음)
- **주요 기능**:
  - PhotoCard 생성 (province, city 정보 포함)
  - 지역별 관광지 추천
  - 쿠폰 발급/사용
  - 리뷰 작성

### travel-server 구조
- **위치**: `/Users/yoonseungjae/Documents/code/Seoul-Soft/hackerthon/travel-server`
- **상태**: MCP 통합 완료 ✅
- **엔드포인트**:
  - `POST /api/v1/ask` - 자연어 여행 추천 (area_code, sigungu_code 지원)

---

## 🔗 통합 계획

### 1단계: API 서비스 레이어 추가 (Flutter)

**파일 생성**: `lib/services/travel_api_service.dart`

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';

class TravelApiService {
  // ⚠️ 배포 전 환경변수로 변경 필요
  static const String baseUrl = 'http://YOUR_ORACLE_SERVER_IP:8080';

  // Province → area_code 매핑
  static const Map<String, String> provinceToAreaCode = {
    '서울특별시': '1',
    '인천광역시': '2',
    '대전광역시': '3',
    '대구광역시': '4',
    '광주광역시': '5',
    '부산광역시': '6',
    '울산광역시': '7',
    '세종특별자치시': '8',
    '경기도': '31',
    '강원도': '32',
    '강원특별자치도': '32',
    '충청북도': '33',
    '충청남도': '34',
    '경상북도': '35',
    '경상남도': '36',
    '전라북도': '37',
    '전북특별자치도': '37',
    '전라남도': '38',
    '제주특별자치도': '39',
    '제주도': '39',
  };

  // City → sigungu_code 매핑 (강릉 예시)
  static const Map<String, String> citySigunguCodeGangwon = {
    '강릉시': '1',
    '동해시': '2',
    '삼척시': '3',
    '속초시': '4',
    '원주시': '5',
    '춘천시': '6',
    '태백시': '7',
    '고성군': '8',
    // ... 나머지 강원도 시군구
  };

  /// 여행 추천 요청
  /// [query]: 사용자 요청 (예: "바다 근처 맛집 추천해줘")
  /// [province]: 도/광역시 (예: "강원도")
  /// [city]: 시/군/구 (예: "강릉시")
  static Future<TravelRecommendationResponse> getRecommendations({
    required String query,
    required String province,
    String? city,
  }) async {
    final areaCode = provinceToAreaCode[province];
    if (areaCode == null) {
      throw Exception('Unknown province: $province');
    }

    // TODO: city → sigungu_code 매핑 구현 필요
    String? sigunguCode;
    if (city != null && province == '강원도') {
      sigunguCode = citySigunguCodeGangwon[city];
    }

    final response = await http.post(
      Uri.parse('$baseUrl/api/v1/ask'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'query': query,
        'area_code': areaCode,
        if (sigunguCode != null) 'sigungu_code': sigunguCode,
      }),
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to get recommendations: ${response.statusCode}');
    }

    return TravelRecommendationResponse.fromJson(
      jsonDecode(utf8.decode(response.bodyBytes)),
    );
  }
}
```

---

### 2단계: 응답 모델 추가 (Flutter)

**파일 생성**: `lib/models/travel_recommendation.dart`

```dart
class TravelRecommendationResponse {
  final String? destination;
  final Map<String, dynamic> extractedParams;
  final CuratedCourse? curatedCourse;
  final List<RawCourse> rawCourses;
  final String message;

  TravelRecommendationResponse({
    this.destination,
    required this.extractedParams,
    this.curatedCourse,
    required this.rawCourses,
    required this.message,
  });

  factory TravelRecommendationResponse.fromJson(Map<String, dynamic> json) {
    return TravelRecommendationResponse(
      destination: json['destination'],
      extractedParams: json['extracted_params'] ?? {},
      curatedCourse: json['curated_course'] != null
        ? CuratedCourse.fromJson(json['curated_course'])
        : null,
      rawCourses: (json['raw_courses'] as List?)
        ?.map((c) => RawCourse.fromJson(c))
        .toList() ?? [],
      message: json['message'] ?? '',
    );
  }
}

class CuratedCourse {
  final String courseTitle;
  final List<CuratedSpot> spots;
  final String? overallTip;
  final String? summary;

  CuratedCourse({
    required this.courseTitle,
    required this.spots,
    this.overallTip,
    this.summary,
  });

  factory CuratedCourse.fromJson(Map<String, dynamic> json) {
    return CuratedCourse(
      courseTitle: json['course_title'] ?? '',
      spots: (json['spots'] as List?)
        ?.map((s) => CuratedSpot.fromJson(s))
        .toList() ?? [],
      overallTip: json['overall_tip'],
      summary: json['summary'],
    );
  }
}

class CuratedSpot {
  final String name;
  final String? time;
  final String? duration;
  final String? reason;
  final String? tip;

  CuratedSpot({
    required this.name,
    this.time,
    this.duration,
    this.reason,
    this.tip,
  });

  factory CuratedSpot.fromJson(Map<String, dynamic> json) {
    return CuratedSpot(
      name: json['name'] ?? '',
      time: json['time'],
      duration: json['duration'],
      reason: json['reason'],
      tip: json['tip'],
    );
  }
}

class RawCourse {
  final String title;
  final List<RawSpot> spots;
  final String? summary;

  RawCourse({
    required this.title,
    required this.spots,
    this.summary,
  });

  factory RawCourse.fromJson(Map<String, dynamic> json) {
    return RawCourse(
      title: json['title'] ?? '',
      spots: (json['spots'] as List?)
        ?.map((s) => RawSpot.fromJson(s))
        .toList() ?? [],
      summary: json['summary'],
    );
  }
}

class RawSpot {
  final String name;
  final String? address;
  final String? category;
  final String? description;
  final String? imageUrl;
  final int? rank;

  RawSpot({
    required this.name,
    this.address,
    this.category,
    this.description,
    this.imageUrl,
    this.rank,
  });

  factory RawSpot.fromJson(Map<String, dynamic> json) {
    return RawSpot(
      name: json['name'] ?? '',
      address: json['address'],
      category: json['category'],
      description: json['description'],
      imageUrl: json['image_url'],
      rank: json['rank'],
    );
  }
}
```

---

### 3단계: Provider 수정 (Flutter)

**파일 수정**: `lib/providers/app_provider.dart`

**⚠️ 주의**: 아직 수정하지 말 것! 기록만 남김

```dart
// 추가할 메서드 (line ~311 이후)

/// API를 통한 코스 생성 (실제 LLM 큐레이션)
Future<List<Course>> generateCoursesFromAPI(
  String province,
  String city,
  String query,
) async {
  try {
    final response = await TravelApiService.getRecommendations(
      query: query,
      province: province,
      city: city,
    );

    // CuratedCourse가 있으면 사용
    if (response.curatedCourse != null) {
      return _convertCuratedCourseToCourses(response.curatedCourse!);
    }

    // 없으면 RawCourse 사용
    if (response.rawCourses.isNotEmpty) {
      return _convertRawCoursesToCourses(response.rawCourses);
    }

    // 둘 다 없으면 기존 로컬 데이터 사용
    return generateCourses(province, city);

  } catch (e) {
    print('API Error: $e');
    // 에러 발생시 기존 로컬 데이터 폴백
    return generateCourses(province, city);
  }
}

List<Course> _convertCuratedCourseToCourses(CuratedCourse curatedCourse) {
  // CuratedSpot을 Place로 변환하여 Course 생성
  final places = curatedCourse.spots.map((spot) => Place(
    id: _uuid.v4(),
    name: spot.name,
    category: PlaceCategory.tourism, // 기본값
    description: spot.reason ?? '',
    rating: 0,
    reviewCount: 0,
    province: _currentProvince ?? '',
    city: _currentCity ?? '',
    latitude: 0,
    longitude: 0,
  )).toList();

  return [
    Course(
      timeSlot: TimeSlot.morning, // 기본값
      places: places,
      estimatedMinutes: places.length * 90,
    ),
  ];
}

List<Course> _convertRawCoursesToCourses(List<RawCourse> rawCourses) {
  // RawCourse를 Course로 변환
  // 구현 필요
  return [];
}
```

---

### 4단계: UI 수정 (Flutter)

**파일 수정**: `lib/screens/meeting_platform_screen.dart`

**⚠️ 주의**: 아직 수정하지 말 것! 기록만 남김

```dart
// PhotoCard의 province, city를 사용하여 API 호출
// 기존 generateCourses() 대신 generateCoursesFromAPI() 사용

final courses = await provider.generateCoursesFromAPI(
  photoCard.province,
  photoCard.city,
  '맛집이랑 카페 추천해줘', // 기본 쿼리 또는 사용자 입력
);
```

---

## 🔐 환경 설정

### Flutter `.env` 파일
```env
TRAVEL_API_BASE_URL=http://YOUR_ORACLE_SERVER_IP:8080
```

### pubspec.yaml 의존성 추가
```yaml
dependencies:
  http: ^1.1.0
  flutter_dotenv: ^5.1.0
```

---

## 📝 시군구 코드 매핑 완성 필요

**전국 시군구 코드 매핑**은 아래 파일에서 가져올 수 있음:
- Tour API 공식 문서
- 또는 `/Users/yoonseungjae/Documents/code/Seoul-Soft/hackerthon/tour-mcp-server/` 참고

**예시**:
```dart
static const Map<String, Map<String, String>> sigunguCodes = {
  '강원도': {
    '강릉시': '1',
    '동해시': '2',
    '삼척시': '3',
    // ...
  },
  '제주도': {
    '제주시': '1',
    '서귀포시': '2',
  },
  // ...
};
```

---

## ⚡ 테스트 시나리오

### 1. 로컬 테스트 (travel-server 로컬 실행)
```bash
# travel-server 실행
cd /Users/yoonseungjae/Documents/code/Seoul-Soft/hackerthon/travel-server
python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

Flutter에서:
```dart
static const String baseUrl = 'http://localhost:8080';
// 또는 Android Emulator: 'http://10.0.2.2:8080'
// 또는 iOS Simulator: 'http://localhost:8080'
```

### 2. 실제 서버 테스트 (Oracle Cloud 배포 후)
```dart
static const String baseUrl = 'http://YOUR_ORACLE_IP:8080';
```

---

## 🚨 주의사항

1. **LLM 호출 부분 수정 금지**:
   - `lib/services/travel_api_service.dart` 파일만 새로 생성
   - 기존 `app_provider.dart`는 메모만 하고 실제 수정은 나중에

2. **CORS 설정 확인**:
   - travel-server의 `main.py`에서 CORS 이미 설정됨:
   ```python
   allow_origins=["*"]  # 프로덕션에서는 특정 도메인만
   ```

3. **타임아웃 설정**:
   - LLM 처리 시간이 오래 걸릴 수 있음 (1-2분)
   - Flutter http 클라이언트 타임아웃 증가 필요:
   ```dart
   final response = await http.post(...).timeout(
     const Duration(minutes: 3),
   );
   ```

4. **에러 핸들링**:
   - API 실패 시 로컬 샘플 데이터로 폴백
   - 사용자에게 명확한 에러 메시지 표시

---

## 📊 데이터 흐름

```
User Input (PhotoCard)
  ↓
province: "강원도"
city: "강릉시"
  ↓
TravelApiService
  ↓
area_code: "32"
sigungu_code: "1"
query: "맛집이랑 카페 추천해줘"
  ↓
POST http://oracle-server:8080/api/v1/ask
  ↓
travel-server (FastAPI)
  ↓
DIGITS LLM (118.44.218.103:30000)
  ↓
MCP Server → Tour API
  ↓
LLM Curated Results
  ↓
Flutter App Display
```

---

## 🔄 향후 개선사항

1. **응답 캐싱**: 동일한 query + area 조합은 캐싱
2. **오프라인 지원**: 최근 추천 결과 로컬 저장
3. **사용자 쿼리 커스터마이징**: UI에서 상세 옵션 제공
4. **이미지 통합**: Tour API 이미지 URL 활용
5. **리뷰 연동**: 실제 리뷰 데이터와 통합

---

## ✅ 체크리스트

### travel-server (완료됨)
- [x] MCP 통합
- [x] area_code, sigungu_code 파라미터 지원
- [x] CORS 설정
- [x] 에러 핸들링

### Flutter App (예정)
- [ ] API 서비스 레이어 추가
- [ ] 응답 모델 정의
- [ ] Provider API 연동 메서드 추가
- [ ] UI 수정 (MeetingPlatformScreen)
- [ ] 전국 시군구 코드 매핑 완성
- [ ] 에러 핸들링 UI
- [ ] 로딩 인디케이터 추가
- [ ] 테스트 (로컬 + 서버)

---

**작성일**: 2025-12-13
**작성자**: Claude
**상태**: 계획 단계 (구현 대기)
