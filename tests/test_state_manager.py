import sys
import pathlib
import os
import pytest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
from cappuccino_agent import CappuccinoAgent

@pytest.mark.asyncio
async def test_state_persistence(tmp_path):
    db_path = os.path.join(tmp_path, "state.db")
    agent = await CappuccinoAgent.create(db_path)
    await agent.set_task_plan([{"task": "demo"}])
    await agent.add_message("user", "hello")
    await agent.advance_phase()
    await agent.close()

    # reload
    agent2 = await CappuccinoAgent.create(db_path)
    assert agent2.task_plan == [{"task": "demo"}]
    assert agent2.history[-1]["content"] == "hello"
    assert agent2.phase == 1
    await agent2.close()
