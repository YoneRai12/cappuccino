"""Collect execution results from the executor."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from .base_agent import BaseAgent


class AnalyzerAgent(BaseAgent):
    async def analyze(self, result_queue: asyncio.Queue) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        while True:
            item = await result_queue.get()
            if item is None:
                break
            results.append(item)
        return results
