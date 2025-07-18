# cappuccino_agent.py (最終・確定版)
import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Any, Dict, List, Optional, AsyncGenerator

from openai import AsyncOpenAI

# ★★★★★ ここが重要！ 正しい場所からインポート ★★★★★
from agents import PlannerAgent, ExecutorAgent, AnalyzerAgent, BaseAgent
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

from tool_manager import ToolManager
from state_manager import StateManager
from self_improver import SelfImprover

DEFAULT_AGENT_CONFIG = {
    "model": "llama3",
    "temperature": 0.7,
    "max_tokens": 4096,
    "top_p": 1.0,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0,
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class CappuccinoAgent:
    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        db_path: str | None = None,
        tool_manager: Optional[ToolManager] = None,
        llm: Optional[Any] = None,
        *,
        thread_workers: Optional[int] = None,
        process_workers: Optional[int] = None,
    ) -> None:
        self.client = AsyncOpenAI(api_key=api_key, base_url=api_base) if api_key and llm is None else None
        self.llm = llm
        self.api_key = api_key
        
        self.tool_manager = tool_manager or ToolManager(db_path or "agent_state.db")
        
        # ★★★★★ ここが最重要！ 全ての子エージェントにLLMクライアントを渡す ★★★★★
        self.planner_agent = PlannerAgent(llm=self.client)
        self.executor_agent = ExecutorAgent(self.tool_manager, llm=self.client)
        self.analyzer_agent = AnalyzerAgent(llm=self.client)
        # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
        
        self.messages: List[Dict[str, Any]] = []
        self.task_plan: List[Dict[str, Any]] = []
        self.current_phase_id = 0
        self.thread_executor = ThreadPoolExecutor(max_workers=thread_workers)
        self.process_executor = ProcessPoolExecutor(max_workers=process_workers) if process_workers is not None else None
        self.state_manager = StateManager(db_path or "agent_state.db")
        self.self_improver = SelfImprover(self.state_manager, self.tool_manager, api_key)
        self._initialize_system_prompt()

    @classmethod
    async def create(
        cls,
        db_path: str,
        api_key: str | None = None,
        api_base: str | None = None,
        *,
        llm: Optional[Any] = None,
        tool_manager: Optional[ToolManager] = None,
        thread_workers: Optional[int] = None,
        process_workers: Optional[int] = None,
    ) -> "CappuccinoAgent":
        self = cls(
            api_key=api_key, api_base=api_base, db_path=db_path, llm=llm,
            tool_manager=tool_manager, thread_workers=thread_workers, process_workers=process_workers,
        )
        data = await self.state_manager.load()
        self.task_plan = data.get("task_plan", [])
        self.messages = data.get("history", self.messages)
        self.current_phase_id = data.get("phase", 0)
        return self

    def _initialize_system_prompt(self) -> None:
        system_prompt = (
            "あなたはCappuccinoという名前の、ユーザーの多様な要求に応えることができる汎用AIアシスタントです。\n"
            "思考プロセスは日本語で行い、ユーザーへの応答も日本語で行ってください。"
        )
        self.messages.append({"role": "system", "content": system_prompt})

    # (runメソッドと他のメソッドは変更なし)
    async def run(self, user_query: str, tools_schema: Optional[List[Dict[str, Any]]] = None) -> Any:
        plan_queue: asyncio.Queue = asyncio.Queue()
        result_queue: asyncio.Queue = asyncio.Queue()
        await self.add_message("user", user_query)
        
        planner_task = asyncio.create_task(self.planner_agent.plan(user_query, plan_queue, tools_schema or []))
        executor_task = asyncio.create_task(self.executor_agent.execute(plan_queue, result_queue))
        
        await planner_task
        await executor_task
        
        results = await self.analyzer_agent.analyze(result_queue)
        
        if results:
            output = results[0].get("result", results[0]) if isinstance(results[0], dict) else results[0]
        else:
            output = "タスクを実行しましたが、明確な結果は得られませんでした。"
            
        await self.add_message("assistant", str(output))
        return output
    
    # (他のヘルパーメソッドも変更なし)
    async def add_message(self, role: str, content: str) -> None:
        await self._add_message(role, content)
        await self.state_manager.save(self.task_plan, self.messages, self.current_phase_id)
        
    async def _add_message(self, role: str, content: str, **kwargs) -> None:
        message: Dict[str, Any] = {"role": role, "content": content}
        message.update(kwargs)
        self.messages.append(message)
        logging.info(f"Added message: {message}")