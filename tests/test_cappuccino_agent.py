
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest

from cappuccino_agent import CappuccinoAgent


@pytest.mark.asyncio
async def test_agent_runs_without_llm():
    agent = CappuccinoAgent(tool_manager=None, llm=None)
    with pytest.raises(RuntimeError):
        await agent.run("do this. then that")


@pytest.mark.asyncio
async def test_agent_with_llm():
    async def fake_llm(text):
        return f"done:{text}"

    agent = CappuccinoAgent(llm=fake_llm, tool_manager=None)
    result = await agent.run("step one. step two")
    assert result == [
        {"step": 1, "result": "done:step one"},
        {"step": 2, "result": "done:step two"},
    ]
