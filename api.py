"""FastAPI application exposing the minimal Cappuccino API used in tests."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from cappuccino_agent import CappuccinoAgent
from goal_manager import GoalManager
from planner import Planner
from state_manager import StateManager
from tool_manager import ToolManager


class RunRequest(BaseModel):
    query: str


class GoalsRequest(BaseModel):
    goals: List[str]


class PlanAdvanceRequest(BaseModel):
    step: int


class RealtimeSession:
    def __init__(self, model: str, voice: str, client_secret: Optional[Dict[str, Any]] = None) -> None:
        self.model = model
        self.voice = voice
        self.client_secret = client_secret or {"value": "demo-token"}

    def model_dump(self) -> Dict[str, Any]:
        return {"model": self.model, "voice": self.voice, "client_secret": self.client_secret}


class OpenAIClient:
    class RealtimeSessions:
        async def create(self, model: str, voice: str) -> RealtimeSession:
            return RealtimeSession(model, voice)

    class RealtimeNamespace:
        def __init__(self) -> None:
            self.sessions = OpenAIClient.RealtimeSessions()

    class BetaNamespace:
        def __init__(self) -> None:
            self.realtime = OpenAIClient.RealtimeNamespace()

    def __init__(self) -> None:
        self.beta = OpenAIClient.BetaNamespace()


app = FastAPI(title="Cappuccino Agent API")
openai_client = OpenAIClient()
state_manager = StateManager()
goal_manager = GoalManager(state_manager, {"interests": []})
planner = Planner()
agent = CappuccinoAgent(tool_manager=ToolManager(db_path=":memory:"))


async def call_openai(query: str) -> Dict[str, Any]:
    text = await agent.call_llm(query)
    return {"text": text, "images": []}


@app.post("/agent/run")
async def agent_run(request: RunRequest) -> Dict[str, Any]:
    return await call_openai(request.query)


@app.websocket("/agent/events")
async def agent_events(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            payload = await websocket.receive_json()
            query = payload.get("query", "")
            async for event in agent.stream_events(query):
                await websocket.send_text(event)
    except WebSocketDisconnect:
        return


@app.get("/agent/goals")
async def agent_goals() -> Dict[str, Any]:
    suggested = await goal_manager.derive_goals()
    return {"suggested": suggested}


@app.post("/agent/goals")
async def agent_confirm_goals(request: GoalsRequest) -> Dict[str, Any]:
    await goal_manager.confirm_goals(request.goals)
    plan = planner.create_plan(". ".join(request.goals))
    await state_manager.save_plan(plan)
    return {"plan": plan}


@app.post("/agent/plan/advance")
async def agent_plan_advance(request: PlanAdvanceRequest) -> Dict[str, Any]:
    await state_manager.update_step(request.step)
    return {"current_step": request.step}


@app.get("/session")
async def realtime_session() -> Dict[str, Any]:
    session = await openai_client.beta.realtime.sessions.create(
        model="gpt-4o-realtime-preview", voice="alloy"
    )
    return session.model_dump()
