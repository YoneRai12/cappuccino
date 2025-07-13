import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
import pytest
import api


class DummySession:
    def __init__(self, model: str, voice: str):
        self.model = model
        self.voice = voice
        self.client_secret = {"value": "tok"}

    def model_dump(self):
        return {"model": self.model, "voice": self.voice, "client_secret": self.client_secret}


@pytest.mark.asyncio
async def test_realtime_session(monkeypatch):
    async def fake_create(model: str, voice: str):
        return DummySession(model, voice)

    monkeypatch.setattr(api.openai_client.beta.realtime.sessions, "create", fake_create)
    client = TestClient(api.app)
    resp = client.get("/session")
    assert resp.status_code == 200
    data = resp.json()
    assert data["client_secret"]["value"] == "tok"
