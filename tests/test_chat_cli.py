import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest

from chat_cli import chat_once
from cappuccino_agent import CappuccinoAgent


@pytest.mark.asyncio
async def test_chat_once(monkeypatch):
    async def fake_run(self, msg):
        return "pong"

    monkeypatch.setattr(CappuccinoAgent, "run", fake_run)
    agent = CappuccinoAgent(tool_manager=None, llm=None)
    response = await chat_once(agent, "ping")
    assert response == "pong"
