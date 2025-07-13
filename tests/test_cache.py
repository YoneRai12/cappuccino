import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
import os
import pytest

from tool_manager import ToolManager
from cappuccino_agent import CappuccinoAgent

@pytest.mark.asyncio
async def test_cache_methods(tmp_path):
    tm = ToolManager(db_path=os.path.join(tmp_path, "db.sqlite"))
    await tm.set_cached_result("foo", "bar")
    value = await tm.get_cached_result("foo")
    assert value == "bar"

@pytest.mark.asyncio
async def test_agent_cache(tmp_path):
    tm = ToolManager(db_path=os.path.join(tmp_path, "db.sqlite"))

    async def fake_llm(text: str) -> str:
        return "ok"

    agent = CappuccinoAgent(tool_manager=tm, llm=fake_llm)
    response = await agent.call_llm("hello")
    assert response == "ok"
    cached = await agent.get_cached_result("llm:hello")
    assert cached == "ok"
