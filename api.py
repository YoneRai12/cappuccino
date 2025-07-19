"""FastAPI interface for CappuccinoAgent with extended utilities."""

from typing import Any, AsyncGenerator, Dict, List
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import os
from dotenv import load_dotenv

from cappuccino_agent import CappuccinoAgent
from planner import Planner
from state_manager import StateManager
from goal_manager import GoalManager
from tool_manager import ToolManager

load_dotenv()

# 環境変数からキーを読み込む
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")

# ToolManagerは使わないシンプル版に変更（もし使うならコメントアウト解除）
# tool_manager = ToolManager()

# CappuccinoAgentはシンプルに初期化
agent = CappuccinoAgent(
    api_key=OPENAI_API_KEY,
    api_base=OPENAI_API_BASE,
    # tool_manager=tool_manager  # もし必要なら
)

app = FastAPI()

# 状態管理やプランナー、ゴール管理も初期化
state_manager = StateManager()
planner = Planner()
goal_manager = GoalManager(state_manager, {"interests": ["python"]})

# リクエスト/レスポンスのPydanticモデル
class RunRequest(BaseModel):
    query: str

class RunResponse(BaseModel):
    text: str
    images: List[str]

# APIのコア処理。agent.runをawaitして結果を取得
async def call_cappuccino_agent(prompt: str) -> Dict[str, List[str]]:
    final_answer = await agent.run(prompt)
    # ここはagentの返り値に合わせて加工が必要
    # 例: final_answerが文字列ならそのまま、画像は空リスト
    return {"text": str(final_answer), "images": []}

@app.post("/agent/run", response_model=RunResponse)
async def run_agent(request: RunRequest) -> Dict[str, List[str]]:
    return await call_cappuccino_agent(request.query)

@app.get("/agent/status")
async def agent_status() -> Dict[str, Any]:
    return await agent.get_status()

@app.get("/agent/goals")
async def agent_goals() -> Dict[str, Any]:
    suggestions = await goal_manager.derive_goals()
    confirmed = await goal_manager.current_goals()
    return {"suggested": suggestions, "confirmed": confirmed}

@app.post("/agent/goals")
async def confirm_goals(goals: List[str]) -> Dict[str, Any]:
    await goal_manager.confirm_goals(goals)
    plan = planner.create_plan(". ".join(goals))
    await state_manager.save_long_term_plan(plan, 0)
    return {"plan": plan}

@app.get("/agent/plan")
async def get_plan() -> Dict[str, Any]:
    return await state_manager.load_long_term_plan()

@app.post("/agent/plan/advance")
async def advance_plan(step: int) -> Dict[str, Any]:
    await state_manager.update_long_term_step(step)
    return await state_manager.load_long_term_plan()

@app.post("/agent/tool_call_result")
async def agent_tool_call_result(result: Dict[str, Any]) -> Dict[str, Any]:
    return await agent.handle_tool_call_result(result)

# WebSocketによるストリーム応答 (例)
@app.websocket("/agent/stream")
async def agent_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        query = await websocket.receive_text()
        async for chunk in agent.stream_responses(query):
            await websocket.send_text(chunk)
    except WebSocketDisconnect:
        pass

# イベントストリーム(WebSocket)の例
@app.websocket("/agent/events")
async def agent_events(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        query = data.get("query", "")
        async for chunk in agent.stream_events(query):
            await websocket.send_text(chunk)
    except WebSocketDisconnect:
        pass
