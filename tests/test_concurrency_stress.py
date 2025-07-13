import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import asyncio
import pytest

from cappuccino_agent import CappuccinoAgent
from tool_manager import ToolManager


@pytest.mark.asyncio
async def test_concurrent_agent_runs(tmp_path):
    async def fake_llm(messages):
        return {"choices": [{"message": {"content": "ok"}}]}

    db_path = tmp_path / "state.db"
    tm = ToolManager(db_path=str(db_path))
    agent = CappuccinoAgent(
        llm=fake_llm,
        tool_manager=tm,
        thread_workers=2,
        process_workers=1,
        db_path=str(db_path),
    )

    async def run_once(i: int):
        result = await agent.run(f"hi {i}")
        assert result == "ok"

    await asyncio.gather(*[run_once(i) for i in range(5)])
    # system prompt + 5 user + 5 assistant messages
    assert len(agent.history) == 1 + 10
    await agent.close()
