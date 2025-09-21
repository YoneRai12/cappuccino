"""Light-weight base class shared by planner, executor and analyzer agents."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional

LLMCallable = Callable[[str], Awaitable[Any]]


class BaseAgent:
    """Provide a tiny abstraction around an asynchronous LLM callable."""

    def __init__(self, llm: Optional[LLMCallable] = None) -> None:
        self.llm = llm

    async def call_llm(self, prompt: str) -> str:
        """Invoke the configured LLM and normalise the response to a string."""
        if self.llm is None:
            return "error: llm unavailable"

        result = await self.llm(prompt)
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            if "choices" in result and result["choices"]:
                message = result["choices"][0].get("message", {})
                content = message.get("content")
                if content is not None:
                    return content
            if "text" in result:
                return str(result["text"])
        return str(result)
