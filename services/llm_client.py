import httpx
import json
from typing import Optional
from config import get_settings


class LLMClient:
    """DIGITS PC의 EXAONE LLM 서버와 통신"""

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.llm_base_url
        self.timeout = self.settings.llm_timeout

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """LLM에 텍스트 생성 요청"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # OpenAI 호환 API 형식 (vLLM, text-generation-inference 등)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": "exaone",  # DIGITS 서버 설정에 맞게 수정
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 1024,
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def generate_hashtags(self, description: str) -> list[str]:
        """설명을 기반으로 재밌는 해시태그 생성"""
        system_prompt = """당신은 SNS 해시태그 전문가입니다.
사용자의 여행 설명을 보고 재밌고 트렌디한 해시태그 5개를 생성합니다.
반드시 JSON 배열 형식으로만 응답하세요.
예시: ["#강릉여행", "#바다스타그램", "#커피는사랑", "#여기어디게", "#인생뷰"]"""

        prompt = f"다음 여행 설명에 어울리는 해시태그 5개를 만들어주세요:\n\n{description}"

        result = await self.generate(prompt, system_prompt)

        # JSON 파싱 시도
        try:
            # 응답에서 JSON 배열 추출
            start = result.find("[")
            end = result.rfind("]") + 1
            if start != -1 and end > start:
                hashtags = json.loads(result[start:end])
                return hashtags
        except json.JSONDecodeError:
            pass

        # 파싱 실패시 기본값
        return ["#여행스타그램", "#여행에미치다", "#여기어디", "#인생샷", "#추억저장"]

    async def extract_search_params(self, session_context: str, destination: str, preferences: dict) -> dict:
        """자연어 입력을 관광 API 검색 파라미터로 변환"""
        system_prompt = """당신은 여행 검색 전문가입니다.
사용자의 여행 정보를 분석하여 관광 API 검색에 필요한 파라미터를 추출합니다.
반드시 JSON 형식으로만 응답하세요.
예시: {"area": "강원특별자치도", "sigungu": "강릉시", "keyword": "해변", "content_type": "12"}

content_type 코드:
- 12: 관광지
- 14: 문화시설
- 15: 축제공연행사
- 32: 숙박
- 39: 음식점"""

        prompt = f"""이전 대화 컨텍스트: {session_context}
목적지: {destination}
선호사항: {preferences}

위 정보를 바탕으로 관광 API 검색 파라미터를 추출해주세요."""

        result = await self.generate(prompt, system_prompt)

        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(result[start:end])
        except json.JSONDecodeError:
            pass

        # 기본값
        return {"area": destination, "keyword": preferences.get("theme", "관광")}

    async def mcp_query(self, query: str, area_code: Optional[str] = None, sigungu_code: Optional[str] = None) -> dict:
        """MCP 엔드포인트로 자연어 쿼리 + area 정보 전달"""
        async with httpx.AsyncClient(timeout=300) as client:  # 5분 (MCP + LLM 처리시간)
            payload = {"query": query}
            if area_code:
                payload["area_code"] = area_code
            if sigungu_code:
                payload["sigungu_code"] = sigungu_code

            response = await client.post(
                f"{self.base_url}/v1/mcp/query",
                json=payload
            )
            response.raise_for_status()
            return response.json()

    async def parse_travel_query(self, query: str, area_code: Optional[str] = None, sigungu_code: Optional[str] = None) -> dict:
        """자연어 여행 질의를 파라미터로 파싱"""
        system_prompt = """당신은 여행 질의 분석 전문가입니다.
사용자의 자연어 여행 요청을 분석하여 검색에 필요한 정보를 추출합니다.
반드시 JSON 형식으로만 응답하세요.

예시 입력: "강릉 바다 근처 맛집이랑 카페 추천해줘"
예시 출력: {"destination": "강릉", "area": "강원", "keyword": "바다", "content_types": ["음식점", "카페"]}

예시 입력: "제주도 혼자 여행 갈건데 조용한 곳 추천"
예시 출력: {"destination": "제주", "area": "제주", "keyword": "조용한", "style": "혼자", "content_types": ["관광지"]}

content_types 가능 값: 관광지, 문화시설, 축제, 숙박, 음식점, 카페, 쇼핑"""

        result = await self.generate(query, system_prompt)

        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(result[start:end])
        except json.JSONDecodeError:
            pass

        # 기본값: 쿼리에서 키워드 추출 시도
        return {"keyword": query, "content_types": ["관광지"]}

    async def curate_and_explain(self, query: str, api_results: dict, parsed_params: dict) -> dict:
        """API 결과를 큐레이션하고 코스/설명/팁 생성"""
        system_prompt = """당신은 전문 여행 큐레이터입니다.
관광 API 데이터를 분석하여 사용자 맞춤 여행 코스를 설계합니다.

반드시 아래 JSON 형식으로만 응답하세요:
{
  "course_title": "코스 제목",
  "spots": [
    {
      "name": "장소명",
      "time": "오전 10시",
      "duration": "1시간",
      "reason": "이 장소를 추천하는 이유",
      "tip": "방문 팁"
    }
  ],
  "overall_tip": "전체 여행 팁",
  "summary": "코스 요약 설명"
}

주의사항:
- 사용자의 취향(동행, 스타일)을 반영하세요
- 동선이 효율적이도록 순서를 정하세요
- 각 장소별 추천 이유와 팁을 구체적으로 작성하세요
- API 데이터에 없는 장소는 추천하지 마세요"""

        # API 결과 요약 (토큰 절약)
        spots_summary = []
        for item in api_results.get("keyword_results", [])[:10]:
            spots_summary.append({
                "name": item.get("title", ""),
                "addr": item.get("addr1", ""),
                "type": item.get("contenttypeid", ""),
                "overview": item.get("overview", "")[:100] if item.get("overview") else ""
            })

        for item in api_results.get("related_results", [])[:10]:
            spots_summary.append({
                "name": item.get("rlteTatsNm", ""),
                "category": item.get("rlteCtgrySclsNm", ""),
                "rank": item.get("rlteRank", "")
            })

        prompt = f"""사용자 요청: {query}

분석된 정보:
- 목적지: {parsed_params.get('destination', '미정')}
- 키워드: {parsed_params.get('keyword', '')}
- 스타일: {parsed_params.get('style', '일반')}
- 원하는 장소 유형: {parsed_params.get('content_types', ['관광지'])}

API에서 찾은 장소들:
{json.dumps(spots_summary, ensure_ascii=False, indent=2)}

위 데이터를 바탕으로 최적의 여행 코스를 설계해주세요."""

        result = await self.generate(prompt, system_prompt)

        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(result[start:end])
        except json.JSONDecodeError:
            pass

        # 파싱 실패시 기본 응답
        return {
            "course_title": f"{parsed_params.get('destination', '')} 여행 코스",
            "spots": [],
            "overall_tip": "즐거운 여행 되세요!",
            "summary": "API 데이터 기반 추천"
        }


# 싱글톤 인스턴스
llm_client = LLMClient()
