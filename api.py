
"""FastAPI interface for Cappuccino agent and Realtime utilities."""

from typing import Any, AsyncGenerator, Dict, List
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv
from planner import Planner
from state_manager import StateManager
from goal_manager import GoalManager
from tool_manager import ToolManager
from cappuccino_agent import CappuccinoAgent

load_dotenv()
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def stream_events(query: str) -> AsyncGenerator[str, None]:
    """Yield thoughts and tool outputs as discrete text chunks."""
    for i in range(2):
        await asyncio.sleep(0.05)
        yield f"thought {i}: {query}"
    tool_result = await tool_manager.message_notify_user("ws", query)
    yield f"tool_output: {tool_result['message']}"


tool_manager = ToolManager(db_path=":memory:")
agent = CappuccinoAgent(tool_manager)
app = FastAPI()

state_manager = StateManager()
planner = Planner()
goal_manager = GoalManager(state_manager, {"interests": ["python"]})


class RunRequest(BaseModel):
    query: str


class RunResponse(BaseModel):
    text: str
    images: List[str]


async def call_openai(prompt: str) -> Dict[str, List[str]]:
    resp = await openai_client.responses.create(
        model="gpt-4.1",
        tools=[
            {"type": "web_search_preview"},
            {"type": "code_interpreter", "container": {"type": "auto"}},
            {"type": "image_generation"},
        ],
        input=[{"role": "user", "content": prompt}],
    )

    text_blocks: List[str] = []
    images: List[str] = []
    for item in resp.output:
        if item.type == "message":
            for block in item.content:
                if getattr(block, "type", "") in {"output_text", "text"}:
                    txt = getattr(block, "text", "").strip()
                    if txt:
                        text_blocks.append(txt)
        elif item.type == "image_generation_call":
            img_data = getattr(item, "result", None)
            if img_data:
                images.append(f"data:image/png;base64,{img_data}")

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


@app.get("/session")
async def realtime_session(params: RealtimeSessionParams = RealtimeSessionParams()) -> Dict[str, Any]:
    """Create a Realtime API session and return the ephemeral token."""
    resp = await openai_client.beta.realtime.sessions.create(
        model=params.model, voice=params.voice
    )
    return resp.model_dump()


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

