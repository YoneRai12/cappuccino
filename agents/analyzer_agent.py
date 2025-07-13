import asyncio
from typing import Any, Dict, List

class AnalyzerAgent:
    """Agent that aggregates execution results."""

    async def analyze(self, result_queue: asyncio.Queue) -> List[Dict[str, Any]]:
        """Collect results from ``result_queue`` until ``None`` is received."""
        results = []
        while True:
            item = await result_queue.get()
            if item is None:
                break
            results.append(item)
        return results
