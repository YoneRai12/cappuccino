"""Simple planner that turns free-form text into actionable steps."""

from __future__ import annotations

import asyncio
import re
from typing import Iterable, List, Dict

from .base_agent import BaseAgent


class PlannerAgent(BaseAgent):
    """Split a user query into individual steps for the executor."""

    def __init__(self, llm=None) -> None:
        super().__init__(llm=llm)

    async def plan(self, user_query: str, plan_queue: asyncio.Queue) -> List[Dict[str, str]]:
        steps = [
            {"step": index, "action": action}
            for index, action in enumerate(self._extract_steps(user_query), start=1)
        ]
        for step in steps:
            await plan_queue.put(step)
        await plan_queue.put(None)
        return steps

    def _extract_steps(self, text: str) -> Iterable[str]:
        candidates = re.split(r"[.\n]+", text)
        return [candidate.strip() for candidate in candidates if candidate.strip()]
