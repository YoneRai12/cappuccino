import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import pytest
import openai

from self_improver import SelfImprover
from tool_manager import ToolManager
from state_manager import StateManager


class DummyMessage:
    def __init__(self, content):
        self.content = content


class DummyChoice:
    def __init__(self, content):
        self.message = DummyMessage(content)


class DummyResponse:
    def __init__(self, content):
        self.choices = [DummyChoice(content)]


class DummyClient:
    class chat:
        class completions:
            @staticmethod
            async def create(model, messages, temperature=0):
                return DummyResponse("async def auto_tool(x: int) -> dict:\n    return {'result': x + 1}")


@pytest.mark.asyncio
async def test_self_improver_generates_tool(monkeypatch, tmp_path):
    monkeypatch.setattr(openai, 'AsyncOpenAI', lambda api_key=None: DummyClient)
    db = tmp_path / "state.db"
    state = StateManager(db_path=str(db))
    tm = ToolManager(db_path=str(db))

    history = [
        {'role': 'user', 'content': 'increment number'},
        {'role': 'assistant', 'content': 'error: tool missing'},
    ]
    await state.save([], history, 0)

    improver = SelfImprover(state, tm, api_key='k')
    res = await improver.improve()
    assert res['name'] == 'auto_tool'
    assert hasattr(tm, 'auto_tool')
    out = await getattr(tm, 'auto_tool')(1)
    assert out['result'] == 2


@pytest.mark.asyncio
async def test_advance_phase_calls_improver(monkeypatch):
    from cappuccino_agent import CappuccinoAgent

    agent = CappuccinoAgent(tool_manager=ToolManager(db_path=':memory:'), llm=None)
    called = False

    async def dummy():
        nonlocal called
        called = True
    monkeypatch.setattr(agent.self_improver, 'improve', dummy)
    await agent.advance_phase()
    assert called

