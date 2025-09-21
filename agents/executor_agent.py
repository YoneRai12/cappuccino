"""Execute planned steps using either tools or the configured LLM."""

from __future__ import annotations

import asyncio
from typing import Optional

from .base_agent import BaseAgent, LLMCallable
from tool_manager import ToolManager


class ExecutorAgent(BaseAgent):
    def __init__(self, tool_manager: Optional[ToolManager] = None, llm: Optional[LLMCallable] = None) -> None:
        super().__init__(llm=llm)
        self.tool_manager = tool_manager

    async def execute(self, plan_queue: asyncio.Queue, result_queue: asyncio.Queue) -> None:
        step_counter = 0
        while True:
            task = await plan_queue.get()
            if task is None:
                await result_queue.put(None)
                break

            step_counter += 1
            action = task.get("action", "")
            result = await self._execute_action(action, task)
            await result_queue.put({"step": task.get("step", step_counter), "result": result})

    async def _execute_action(self, action: str, task: dict) -> str:
        if self.tool_manager and self.tool_manager.get_tool_by_name(action):
            tool = self.tool_manager.get_tool_by_name(action)
            output = await tool(**task.get("parameters", {}))
            return output if isinstance(output, str) else str(output)
        return await self.call_llm(action)
