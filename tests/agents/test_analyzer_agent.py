import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import asyncio
import pytest

from agents import AnalyzerAgent


@pytest.mark.asyncio
async def test_analyzer_collects_results():
    result_q = asyncio.Queue()
    await result_q.put({"step": 1, "result": "ok"})
    await result_q.put({"step": 2, "result": "done"})
    await result_q.put(None)

    agent = AnalyzerAgent()
    results = await agent.analyze(result_q)

    assert results == [
        {"step": 1, "result": "ok"},
        {"step": 2, "result": "done"},
    ]
