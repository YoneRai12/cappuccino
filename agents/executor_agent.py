import asyncio
from typing import Any

from tool_manager import ToolManager

class ExecutorAgent:
    """Agent that executes planned steps."""

    def __init__(self, tool_manager: ToolManager | None = None, llm: Any | None = None) -> None:
        self.tool_manager = tool_manager or ToolManager()
        self.llm = llm

    async def execute(self, plan_queue: asyncio.Queue, result_queue: asyncio.Queue) -> None:
        """Consume steps from ``plan_queue`` and push execution results to ``result_queue``.

        A ``None`` value is pushed when execution is finished.
        """
        while True:
            step = await plan_queue.get()
            if step is None:
                await result_queue.put(None)
                break

            action = step.get("action", "")
            if self.llm:
                llm_result = await self.llm(action)
                if isinstance(llm_result, dict):
                    result = (
                        llm_result.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )
                else:
                    result = llm_result
            else:
                raise RuntimeError("No LLM client configured")
            await result_queue.put({"step": step.get("step"), "result": result})
