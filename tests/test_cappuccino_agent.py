
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest

from cappuccino_agent import CappuccinoAgent


@pytest.mark.asyncio
async def test_agent_runs_without_llm():
    agent = CappuccinoAgent(api_key=None, api_base=None)
    result = await agent.run("do this. then that")
    assert "エラー" in result or "error" in result.lower()


@pytest.mark.asyncio
async def test_agent_with_llm():
    agent = CappuccinoAgent(api_key="test", api_base="test")
    result = await agent.run("step one. step two")
    assert isinstance(result, str)
