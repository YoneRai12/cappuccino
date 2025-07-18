# api.py (TypeErrorを修正した最終版)

from typing import Any, AsyncGenerator, Dict, List
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import os
from dotenv import load_dotenv

# bot.pyと同じように、configから設定を読み込む
from config import settings
from cappuccino_agent import CappuccinoAgent
from tool_manager import ToolManager
from planner import Planner
from state_manager import StateManager
from goal_manager import GoalManager

# .envファイルを読み込む
load_dotenv()

# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
# ★★★ ここが最も重要な修正点です ★★★
#
# bot.py と同じ方法で、api_key と api_base を使ってエージェントを初期化します。
# これで TypeError は発生しなくなります。

tool_manager = ToolManager(db_path=":memory:")
agent = CappuccinoAgent(
    tool_manager=tool_manager,
    api_key=settings.openai_api_key,
    api_base=settings.openai_api_base
)

# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★


app = FastAPI()

state_manager = StateManager()
planner = Planner()
goal_manager = GoalManager(state_manager, {"interests": ["python"]})


class RunRequest(BaseModel):
    query: str


class RunResponse(BaseModel):
    text: str
    images: List[str]


# この関数は、agent.run を直接呼び出すように修正します。
async def call_cappuccino_agent(prompt: str) -> Dict[str, List[str]]:
    final_answer = await agent.run(prompt)
    
    image_path = None
    if isinstance(final_answer, str) and "画像を生成しました。パス: " in final_answer:
        path_str = final_answer.replace("画像を生成しました。パス: ", "").strip()
        if os.path.exists(path_str):
            # 画像パスからBase64にエンコードする処理が必要ですが、
            # まずはテキストを返すことを優先します。
            text = "画像を生成しました（API経由での画像返却は未実装です）"
            images = []
        else:
            text = f"エラー: 生成された画像ファイルが見つかりませんでした。パス: {path_str}"
            images = []
    else:
        text = str(final_answer)
        images = []

    return {"text": text, "images": images}


class ToolCallResult(BaseModel):
    data: Dict[str, Any]

class GoalList(BaseModel):
    goals: List[str]

class StepUpdate(BaseModel):
    step: int


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
async def confirm_goals(goals: GoalList) -> Dict[str, Any]:
    await goal_manager.confirm_goals(goals.goals)
    plan = planner.create_plan(". ".join(goals.goals))
    await state_manager.save_long_term_plan(plan, 0)
    return {"plan": plan}


@app.get("/agent/plan")
async def get_plan() -> Dict[str, Any]:
    return await state_manager.load_long_term_plan()


@app.post("/agent/plan/advance")
async def advance_plan(update: StepUpdate) -> Dict[str, Any]:
    await state_manager.update_long_term_step(update.step)
    return await state_manager.load_long_term_plan()


@app.post("/agent/tool_call_result")
async def agent_tool_call_result(result: ToolCallResult) -> Dict[str, Any]:
    return await agent.handle_tool_call_result(result.data)


@app.websocket("/agent/stream")
async def agent_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        query = await websocket.receive_text()
        async for chunk in agent.stream_responses(query):
            await websocket.send_text(chunk)
    except WebSocketDisconnect:
        pass