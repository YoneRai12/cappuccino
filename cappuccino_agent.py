"""High level orchestration for the Cappuccino agent used in tests."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

from agents import AnalyzerAgent, ExecutorAgent, PlannerAgent
from state_manager import StateManager
from tool_manager import ToolManager
from agents.base_agent import BaseAgent
from self_improver import SelfImprover


class CappuccinoAgent:
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        tool_manager: Optional[ToolManager] = None,
        llm: Optional[Any] = None,
        state_manager: Optional[StateManager] = None,
        db_path: Optional[str] = None,
        thread_workers: int = 4,
        process_workers: int = 1,
    ) -> None:
        self.llm = llm
        self.tool_manager = tool_manager or ToolManager(db_path=db_path or ":memory:")
        self.state_manager = state_manager or (StateManager(db_path) if db_path else None)
        self.thread_workers = thread_workers
        self.process_workers = process_workers
        self.api_key = api_key
        self.api_base = api_base

        self.system_prompt = "You are Cappuccino, a helpful multitool assistant."
        self.history: List[Dict[str, Any]] = [{"role": "system", "content": self.system_prompt}]
        self.task_plan: List[Dict[str, Any]] = []
        self.phase = 0
        self._state_loaded = False if self.state_manager else True
        self._lock = asyncio.Lock()

        self.planner = PlannerAgent()
        self.executor = ExecutorAgent(tool_manager=self.tool_manager, llm=self.llm)
        self.analyzer = AnalyzerAgent()
        self.self_improver = SelfImprover(
            self.state_manager or StateManager(), self.tool_manager, api_key=api_key
        )

        self.client = None
        self.model = "gpt-4o"

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------
    @classmethod
    async def create(cls, db_path: str) -> "CappuccinoAgent":
        agent = cls(db_path=db_path)
        await agent._ensure_state_loaded()
        return agent

    async def close(self) -> None:
        if self.state_manager:
            await self.state_manager.close()
        await self.tool_manager.close()

    # ------------------------------------------------------------------
    # Core behaviour
    # ------------------------------------------------------------------
    async def run(self, user_query: str) -> str:
        async with self._lock:
            await self._ensure_state_loaded()
            self.history.append({"role": "user", "content": user_query})

            plan_queue: asyncio.Queue = asyncio.Queue()
            steps = await self.planner.plan(user_query, plan_queue)
            self.task_plan = steps

            result_queue: asyncio.Queue = asyncio.Queue()
            await self.executor.execute(plan_queue, result_queue)
            results = await self.analyzer.analyze(result_queue)

            final = results[-1]["result"] if results else "error: llm unavailable"
            self.history.append({"role": "assistant", "content": final})

            await self.tool_manager.set_cached_result(f"llm:{user_query}", final)
            await self._persist_state()
            return final

    async def stream_events(self, user_query: str):
        yield "planning"
        result = await self.run(user_query)
        yield result

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------
    async def set_task_plan(self, plan: List[Dict[str, Any]]) -> None:
        await self._ensure_state_loaded()
        self.task_plan = plan
        await self._persist_state()

    async def add_message(self, role: str, content: str, **extra: Any) -> None:
        await self._ensure_state_loaded()
        message = {"role": role, "content": content}
        message.update(extra)
        self.history.append(message)
        await self._persist_state()

    async def advance_phase(self) -> int:
        await self._ensure_state_loaded()
        self.phase += 1
        await self._persist_state()
        if self.self_improver:
            await self.self_improver.improve()
        return self.phase

    async def get_cached_result(self, key: str) -> Any:
        return await self.tool_manager.get_cached_result(key)

    async def call_llm(self, prompt: str) -> str:
        sentiment = "positive" if any(word in prompt.lower() for word in ("love", "great", "awesome")) else "negative"
        decorated = f"[sentiment={sentiment}] {prompt}"
        helper = BaseAgent(self.llm)
        result = await helper.call_llm(decorated)
        await self.tool_manager.set_cached_result(f"llm:{prompt}", result)
        return result

    async def call_llm_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]]) -> str:
        if not self.client:
            raise RuntimeError("LLM client not configured")
        initial = await self.client.responses.create(model=self.model, input=prompt, tools=tools_schema)
        for item in getattr(initial, "output", []):
            if getattr(item, "type", None) == "function_call":
                tool_name = getattr(item, "name", "")
                args = json.loads(getattr(item, "arguments", "{}"))
                tool = getattr(self.tool_manager, tool_name, None) or self.tool_manager.get_tool_by_name(tool_name)
                if tool is None:
                    continue
                result = await tool(**args)
                follow_up = await self.client.responses.create(
                    model=self.model,
                    input=json.dumps(result),
                    tools=tools_schema,
                )
                for follow_item in getattr(follow_up, "output", []):
                    if getattr(follow_item, "type", None) == "text":
                        return getattr(follow_item, "text", "")
        for item in getattr(initial, "output", []):
            if getattr(item, "type", None) == "text":
                return getattr(item, "text", "")
        return ""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _ensure_state_loaded(self) -> None:
        if self._state_loaded:
            return
        data = await self.state_manager.load() if self.state_manager else {}
        self.task_plan = data.get("task_plan", [])
        history = data.get("history")
        if history:
            self.history = history
        self.phase = data.get("phase", 0)
        self._state_loaded = True

    async def _persist_state(self) -> None:
        if self.state_manager:
            await self.state_manager.save(self.task_plan, self.history, self.phase)
