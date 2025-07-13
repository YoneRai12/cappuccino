import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import pytest

from cappuccino_agent import CappuccinoAgent
from tool_manager import ToolManager


@pytest.mark.asyncio
async def test_positive_prompt_includes_emotion():
    captured = {}

    async def fake_llm(prompt: str):
        captured['prompt'] = prompt
        return 'cheerful'

    agent = CappuccinoAgent(llm=fake_llm, tool_manager=ToolManager(db_path=':memory:'))
    result = await agent.call_llm('I love this product!')
    assert result == 'cheerful'
    assert 'positive' in captured['prompt']


@pytest.mark.asyncio
async def test_negative_prompt_includes_emotion():
    captured = {}

    async def fake_llm(prompt: str):
        captured['prompt'] = prompt
        return 'concerned'

    agent = CappuccinoAgent(llm=fake_llm, tool_manager=ToolManager(db_path=':memory:'))
    result = await agent.call_llm('I hate everything.')
    assert result == 'concerned'
    assert 'negative' in captured['prompt']
