import httpx
from typing import Optional
from config import get_settings


class TourAPIService:
    """한국관광공사 API 서비스"""

    # 지역코드 매핑 (KorService2 → TarRlteTarService1)
    AREA_CODE_MAP = {
        "서울": ("1", "11"),
        "인천": ("2", "28"),
        "대전": ("3", "30"),
        "대구": ("4", "27"),
        "광주": ("5", "29"),
        "부산": ("6", "26"),
        "울산": ("7", "31"),
        "세종": ("8", "36"),
        "경기": ("31", "41"),
        "강원": ("32", "51"),
        "충북": ("33", "43"),
        "충남": ("34", "44"),
        "경북": ("35", "47"),
        "경남": ("36", "48"),
        "전북": ("37", "52"),
        "전남": ("38", "46"),
        "제주": ("39", "50"),
    }

    # 시군구코드 (주요 지역)
    SIGUNGU_MAP = {
        "32": {  # 강원
            "강릉": ("1", "51150"),
            "동해": ("2", "51130"),
            "삼척": ("3", "51140"),
            "속초": ("4", "51210"),
            "원주": ("5", "51110"),
            "춘천": ("6", "51100"),
        },
        "39": {  # 제주
            "제주": ("1", "50110"),
            "서귀포": ("2", "50130"),
        },
    }

    CONTENT_TYPES = {
        "관광지": "12",
        "문화시설": "14",
        "축제": "15",
        "여행코스": "25",
        "레포츠": "28",
        "숙박": "32",
        "쇼핑": "38",
        "음식점": "39",
    }

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.tour_api_key
        self.korservice_url = self.settings.korservice_url
        self.tarrlte_url = self.settings.tarrlte_url

    def _find_area_code(self, area_name: str) -> tuple[Optional[str], Optional[str]]:
        """지역명으로 코드 찾기 (KorService, TarRlte)"""
        for key, codes in self.AREA_CODE_MAP.items():
            if key in area_name or area_name in key:
                return codes
        return None, None

    def _find_sigungu_code(self, kor_area: str, sigungu_name: str) -> tuple[Optional[str], Optional[str]]:
        """시군구명으로 코드 찾기"""
        if kor_area not in self.SIGUNGU_MAP:
            return None, None
        for key, codes in self.SIGUNGU_MAP[kor_area].items():
            if key in sigungu_name or sigungu_name in key:
                return codes
        return None, None

    async def search_keyword(
        self,
        keyword: str,
        area: Optional[str] = None,
        sigungu: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> list[dict]:
        """KorService2 키워드 검색"""
        params = {
            "serviceKey": self.api_key,
            "MobileOS": "ETC",
            "MobileApp": "TravelHashtag",
            "_type": "json",
            "keyword": keyword,
            "numOfRows": 50,
        }

        if area:
            kor_code, _ = self._find_area_code(area)
            if kor_code:
                params["areaCode"] = kor_code

                if sigungu:
                    sigungu_kor, _ = self._find_sigungu_code(kor_code, sigungu)
                    if sigungu_kor:
                        params["sigunguCode"] = sigungu_kor

        if content_type and content_type in self.CONTENT_TYPES:
            params["contentTypeId"] = self.CONTENT_TYPES[content_type]

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.korservice_url}/searchKeyword2",
                params=params
            )
            data = response.json()

            if data["response"]["header"]["resultCode"] != "0000":
                return []

            items = data["response"]["body"].get("items", {})
            if not items:
                return []

            item_list = items.get("item", [])
            if isinstance(item_list, dict):
                item_list = [item_list]

            return item_list

    async def search_related(
        self,
        keyword: str,
        area: Optional[str] = None,
        sigungu: Optional[str] = None,
    ) -> list[dict]:
        """TarRlteTarService1 연관 관광지 검색"""
        params = {
            "serviceKey": self.api_key,
            "MobileOS": "ETC",
            "MobileApp": "TravelHashtag",
            "_type": "json",
            "baseYm": "202504",
            "keyword": keyword,
            "numOfRows": 50,
        }

        if area:
            _, tar_code = self._find_area_code(area)
            if tar_code:
                params["areaCd"] = tar_code

                if sigungu:
                    kor_code, _ = self._find_area_code(area)
                    if kor_code:
                        _, sigungu_tar = self._find_sigungu_code(kor_code, sigungu)
                        if sigungu_tar:
                            params["signguCd"] = sigungu_tar

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(
                    f"{self.tarrlte_url}/searchKeyword1",
                    params=params
                )
                data = response.json()

                if data["response"]["header"]["resultCode"] != "0000":
                    return []

                items = data["response"]["body"].get("items", {})
                if not items:
                    return []

                item_list = items.get("item", [])
                if isinstance(item_list, dict):
                    item_list = [item_list]

                return item_list
            except Exception:
                return []

    async def get_combined_results(
        self,
        keyword: str,
        area: Optional[str] = None,
        sigungu: Optional[str] = None,
    ) -> dict:
        """두 API 결과 통합"""
        keyword_results = await self.search_keyword(keyword, area, sigungu)
        related_results = await self.search_related(keyword, area, sigungu)

        return {
            "keyword_results": keyword_results,
            "related_results": related_results,
        }


# 싱글톤 인스턴스
tour_api = TourAPIService()
