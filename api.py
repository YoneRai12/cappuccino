# api.py (CappuccinoAgentの呼び出し方を修正した最終版)
from typing import Any, List, Dict
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import os
from dotenv import load_dotenv

from config import settings
from cappuccino_agent import CappuccinoAgent
from tool_manager import ToolManager

load_dotenv()

# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
# ★★★ ここが重要な修正点です ★★★
#
# CappuccinoAgentの初期化を、新しいシンプルな形に合わせます。
# ToolManagerを渡す必要はなくなりました。

agent = CappuccinoAgent(
    api_key=settings.openai_api_key,
    api_base=settings.openai_api_base
)

# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

app = FastAPI()

# ... (これ以降のコードは、前回提案した最終版と全く同じでOKです)
# (RunRequest, RunResponse, call_cappuccino_agent, etc...)
class RunRequest(BaseModel): query: str
class RunResponse(BaseModel): text: str; images: List[str]
async def call_cappuccino_agent(prompt: str) -> Dict[str, List[str]]:
    final_answer = await agent.run(prompt)
    return {"text": str(final_answer), "images": []}

@app.post("/agent/run", response_model=RunResponse)
async def run_agent(request: RunRequest) -> Dict[str, List[str]]:
    return await call_cappuccino_agent(request.query)

# ... (他のAPIエンドポイントも変更なし)