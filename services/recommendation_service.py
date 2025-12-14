"""
백그라운드 추천 서비스

포토카드 생성 시 비동기로 LLM 추천을 요청하고 DB에 저장합니다.
"""
import asyncio
from typing import Optional
from database import AsyncSessionLocal
from crud import update_session_status
from services.llm_client import LLMClient


async def process_recommendation_background(
    session_id: str,
    query: str,
    area_code: Optional[str] = None,
    sigungu_code: Optional[str] = None
):
    """
    백그라운드에서 추천 요청 처리

    1. 세션 상태를 "processing"으로 변경
    2. LLM MCP 쿼리 실행
    3. 결과를 DB에 저장 (completed/failed)
    """
    async with AsyncSessionLocal() as db:
        try:
            # 1. 상태 업데이트: processing
            await update_session_status(db, session_id, "processing")
            print(f"[Recommendation] Session {session_id}: processing started")

            # 2. LLM MCP 쿼리 실행
            llm = LLMClient()
            mcp_result = await llm.mcp_query(
                query=query,
                area_code=area_code,
                sigungu_code=sigungu_code
            )

            print(f"[Recommendation] Session {session_id}: MCP result received")

            # 3. 결과 확인 및 저장
            if mcp_result.get("success", False):
                recommendation_data = {
                    "spots": mcp_result.get("spots", []),
                    "course": mcp_result.get("course"),
                    "message": mcp_result.get("message", ""),
                    "selected_tools": mcp_result.get("selected_tools", []),
                }

                await update_session_status(
                    db,
                    session_id,
                    "completed",
                    recommendation_data=recommendation_data
                )
                print(f"[Recommendation] Session {session_id}: completed with {len(recommendation_data.get('spots', []))} spots")
            else:
                error_msg = mcp_result.get("error", "추천 요청 실패")
                await update_session_status(
                    db,
                    session_id,
                    "failed",
                    error_message=error_msg
                )
                print(f"[Recommendation] Session {session_id}: failed - {error_msg}")

        except Exception as e:
            print(f"[Recommendation] Session {session_id}: exception - {str(e)}")
            # DB 세션 재생성 (예외 발생 시)
            async with AsyncSessionLocal() as db2:
                await update_session_status(
                    db2,
                    session_id,
                    "failed",
                    error_message=str(e)
                )


def start_recommendation_task(
    session_id: str,
    query: str,
    area_code: Optional[str] = None,
    sigungu_code: Optional[str] = None
):
    """
    백그라운드 태스크 시작 (FastAPI BackgroundTasks에서 호출)

    Note: 이 함수는 동기 함수로, asyncio.create_task를 사용해서
    비동기 작업을 백그라운드에서 실행합니다.
    """
    asyncio.create_task(
        process_recommendation_background(
            session_id=session_id,
            query=query,
            area_code=area_code,
            sigungu_code=sigungu_code
        )
    )
