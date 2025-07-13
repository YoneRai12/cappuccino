import asyncio
from planner import Planner

class PlannerAgent:
    """Agent responsible for generating a task plan."""

    def __init__(self, planner: Planner | None = None) -> None:
        self.planner = planner or Planner()

    async def plan(self, query: str, queue: asyncio.Queue) -> None:
        """Generate a plan and put each step into the provided queue.

        A ``None`` value is placed onto the queue when planning is complete.
        """
        steps = self.planner.create_plan(query)
        for step in steps:
            await queue.put(step)
        await queue.put(None)
