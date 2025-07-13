import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import asyncio
import pytest

from agents import PlannerAgent


@pytest.mark.asyncio
async def test_plan_queue_population():
    agent = PlannerAgent()
    q: asyncio.Queue = asyncio.Queue()
    await agent.plan("step one. step two", q)
    steps = []
    while True:
        item = await q.get()
        if item is None:
            break
        steps.append(item)
    assert steps == [
        {"step": 1, "action": "step one"},
        {"step": 2, "action": "step two"},
    ]
