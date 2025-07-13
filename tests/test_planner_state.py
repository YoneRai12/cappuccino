import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest

from planner import Planner
from state_manager import StateManager


@pytest.mark.asyncio
async def test_planner_and_state(tmp_path):
    planner = Planner()
    context = "step one. step two. step three"
    plan = planner.create_plan(context)
    assert len(plan) == 3
    assert plan[0]["action"] == "step one"

    db_path = tmp_path / "state.db"
    state = StateManager(db_path=str(db_path))
    await state.save_plan(plan, current_step=1)

    loaded = await state.load_plan()
    assert loaded["task_plan"] == plan
    assert loaded["current_step"] == 1

    await state.update_step(2)
    loaded = await state.load_plan()
    assert loaded["current_step"] == 2


