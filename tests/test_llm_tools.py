import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest

from cappuccino_agent import CappuccinoAgent
from tool_manager import ToolManager, log_tool

class DummyToolManager(ToolManager):
    def __init__(self):
        super().__init__(db_path=":memory:")
        self.called = False

    @log_tool
    async def dummy_tool(self, x: int) -> dict:
        self.called = True
        return {"x": x + 1}

class DummyClient:
    def __init__(self):
        self.calls = 0
        self.responses = self.Responses(self)

    class Responses:
        def __init__(self, outer):
            self.outer = outer

        async def create(self, model, input=None, tools=None):
            self.outer.calls += 1
            if self.outer.calls == 1:
                class Out:
                    type = "function_call"
                    name = "dummy_tool"
                    arguments = "{\"x\": 3}"
                    call_id = "1"

                return type("Resp", (), {"output": [Out()]})()
            else:
                class Out:
                    type = "text"
                    text = "done"

                return type("Resp", (), {"output": [Out()]})()

@pytest.mark.asyncio
async def test_call_llm_with_tools(monkeypatch):
    tm = DummyToolManager()
    agent = CappuccinoAgent(tool_manager=tm, llm=None)
    agent.client = DummyClient()
    schema = [{
        "type": "function",
        "function": {
            "name": "dummy_tool",
            "description": "dummy",
            "parameters": {
                "type": "object",
                "properties": {"x": {"type": "integer"}},
                "required": ["x"],
            },
        },
    }]
    out = await agent.call_llm_with_tools("hi", schema)
    assert out == "done"
    assert tm.called
