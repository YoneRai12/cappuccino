import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import asyncio
import pytest

from agents import ExecutorAgent


@pytest.mark.asyncio
async def test_execute_with_llm():
    async def fake_llm(text):
        return text.upper()

    plan_q = asyncio.Queue()
    result_q = asyncio.Queue()
    await plan_q.put({"step": 1, "action": "hello"})
    await plan_q.put(None)

    agent = ExecutorAgent(tool_manager=None, llm=fake_llm)
    await agent.execute(plan_q, result_q)

    item = await result_q.get()
    end = await result_q.get()
    assert item == {"step": 1, "result": "HELLO"}
    assert end is None
