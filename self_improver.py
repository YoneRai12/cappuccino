"""Self-improvement utilities for Cappuccino agent."""

from typing import Any, Dict, Optional, Tuple

from state_manager import StateManager
from tool_manager import ToolManager


class SelfImprover:
    """Analyze history and generate new tools based on failures."""

    def __init__(self, state_manager: StateManager, tool_manager: ToolManager, api_key: Optional[str] = None) -> None:
        self.state_manager = state_manager
        self.tool_manager = tool_manager
        self.api_key = api_key

    async def _get_latest_failure(self) -> Optional[Tuple[str, str]]:
        """Return the latest user task and error message if present."""
        data = await self.state_manager.load()
        history = data.get("history", [])
        for idx in range(len(history) - 1, -1, -1):
            msg = history[idx]
            if msg.get("role") == "assistant" and "error" in (msg.get("content") or "").lower():
                task = ""
                for prev in range(idx - 1, -1, -1):
                    if history[prev].get("role") == "user":
                        task = history[prev].get("content", "")
                        break
                return task, msg.get("content", "")
        return None

    async def improve(self) -> Optional[Dict[str, Any]]:
        """Attempt to generate a new tool from the latest failure."""
        if not self.api_key:
            return None
        failure = await self._get_latest_failure()
        if not failure:
            return None
        task_description, error_message = failure
        return await self.tool_manager.generate_tool_from_failure(
            task_description, error_message, self.api_key
        )

