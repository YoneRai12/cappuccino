"""FastAPI interface for Cappuccino agent and Realtime utilities."""

import os
import asyncio
from typing import Any, AsyncGenerator, Dict, List

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from openai import AsyncOpenAI

from cappuccino_agent import CappuccinoAgent
from goal_manager import GoalManager
from planner import Planner
from state_manager import StateManager
from tool_manager import ToolManager

# .envファイルを読み込む
load_dotenv()

# --- ここからが重要な変更点 ---

# Ollama (Llama 3.1) に接続するためのクライアント設定
# これにより、すべての通信がローカルのOllamaに向かうようになります
openai_client = AsyncOpenAI(
    base_url=os.getenv("OPENAI_API_BASE", "http://localhost:11434/v1"),
    api_key=os.getenv("OPENAI_API_KEY", "ollama")  # Ollamaの場合、キーは'ollama'でOK
)

# --- ここまでが重要な変更点 ---


async def stream_events(query: str) -> AsyncGenerator[str, None]:
    """Yield thoughts and tool outputs as discrete text chunks."""
    for i in range(2):
        await asyncio.sleep(0.05)
        yield f"thought {i}: {query}"
    tool_result = await tool_manager.message_notify_user("ws", query)
    yield f"tool_output: {tool_result['message']}"


tool_manager = ToolManager(db_path=":memory:")
# エージェントにも修正したクライアントを渡すように変更
agent = CappuccinoAgent(tool_manager=tool_manager, llm_client=openai_client)
app = FastAPI()

state_manager = StateManager()
planner = Planner()
goal_manager = GoalManager(state_manager, {"interests": ["python"]})


class RunRequest(BaseModel):
    query: str


class RunResponse(BaseModel):
    text: str
    images: List[str]


# この関数はOllamaと互換性がない可能性が高いため、
# ひとまずエージェント経由で呼び出すようにします。
# もし直接呼び出したい場合は、OllamaのAPI仕様に合わせる必要があります。
async def call_openai(prompt: str) -> Dict[str, List[str]]:
    # 修正：直接OpenAIのAPIを叩くのではなく、設定済みエージェントに処理を任せる
    # これにより、Llama 3.1 が使われるようになります。
    response = await agent.run(prompt)

    # agent.runの返り値の形式に合わせて調整が必要な場合があります。
    # 以下は仮の整形です。実際の返り値に合わせて修正してください。
    text_blocks = [str(response)]
    images = [] # 画像生成は別途ツールとして実装する必要がある

    return {"text": "\n\n".join(text_blocks), "images": images}


class ToolCallResult(BaseModel):
    data: Dict[str, Any]


class GoalList(BaseModel):
    goals: List[str]


class StepUpdate(BaseModel):
    step: int


class RealtimeSessionParams(BaseModel):
    """Parameters for creating a Realtime API session."""

    model: str = "gpt-4o-realtime-preview-2025-06-03"
    voice: str = "verse"


@app.post("/agent/run", response_model=RunResponse)
async def run_agent(request: RunRequest) -> Dict[str, List[str]]:
    # 修正：call_openai関数がエージェントを使うようにしたので、こちらも同様に動作する
    return await call_openai(request.query)


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


# Realtime APIはOpenAIの独自機能のため、Ollamaでは動作しません。
# このエンドポイントを呼び出すとエラーになります。
@app.get("/session")
async def realtime_session(params: RealtimeSessionParams = RealtimeSessionParams()) -> Dict[str, Any]:
    """Create a Realtime API session and return the ephemeral token."""
    try:
        resp = await openai_client.beta.realtime.sessions.create(
            model=params.model, voice=params.voice
        )
        return resp.model_dump()
    except Exception as e:
        return {"error": f"This endpoint is not compatible with Ollama. Details: {e}"}


@app.websocket("/agent/stream")
async def agent_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        query = await websocket.receive_text()
        async for chunk in agent.stream_responses(query):
            await websocket.send_text(chunk)
    except WebSocketDisconnect:
        pass


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