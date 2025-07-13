import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient

import api
from state_manager import StateManager
from goal_manager import GoalManager
from planner import Planner


@pytest.mark.asyncio
async def test_goal_creation_and_plan_execution(tmp_path, monkeypatch):
    db_path = tmp_path / "state.db"
    state = StateManager(db_path=str(db_path))
    await state.save([], [{"role": "user", "content": "I want to learn Python"}], 0)

    gm = GoalManager(state, {"interests": ["Python"]})
    pln = Planner()

    monkeypatch.setattr(api, "state_manager", state)
    monkeypatch.setattr(api, "goal_manager", gm)
    monkeypatch.setattr(api, "planner", pln)

    client = TestClient(api.app)

    resp = client.get("/agent/goals")
    assert resp.status_code == 200
    assert resp.json()["suggested"]

    resp = client.post("/agent/goals", json={"goals": ["Master Python"]})
    assert resp.status_code == 200
    assert resp.json()["plan"]

    resp = client.post("/agent/plan/advance", json={"step": 1})
    assert resp.status_code == 200
    assert resp.json()["current_step"] == 1

    await state.close()
