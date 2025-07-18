# cappuccino_agent.py (AnalyzerAgentの呼び出しバグを修正した最終版)
import asyncio
import logging
from typing import Any, Dict, List, Optional

from agents import PlannerAgent, ExecutorAgent, AnalyzerAgent
from tool_manager import ToolManager
from state_manager import StateManager
from self_improver import SelfImprover
import torch

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class CappuccinoAgent:
    def __init__(
        self,
        api_key: str,
        api_base: str,
        db_path: str = "agent_state.db",
        tool_manager: Optional[ToolManager] = None
    ) -> None:
        self.api_key = api_key
        self.api_base = api_base
        self.tool_manager = tool_manager or ToolManager(db_path=db_path)
        self.state_manager = StateManager(db_path=db_path)
        self.planner_agent: Optional[PlannerAgent] = None
        self.executor_agent: Optional[ExecutorAgent] = None
        self.analyzer_agent: Optional[AnalyzerAgent] = None
        self.self_improver = SelfImprover(self.state_manager, self.tool_manager, self.api_key)
        self.messages: List[Dict[str, Any]] = []
        self._initialize_system_prompt()
        self.tool_manager.set_agent(self)

    def load_agents(self):
        if self.planner_agent is None:
            logging.info("子エージェントをVRAMにロードしています...")
            agent_kwargs = {"api_key": self.api_key, "api_base": self.api_base}
            self.planner_agent = PlannerAgent(**agent_kwargs)
            self.executor_agent = ExecutorAgent(tool_manager=self.tool_manager, **agent_kwargs)
            self.analyzer_agent = AnalyzerAgent(**agent_kwargs)
            logging.info("子エージェントのロードが完了しました。")

    def unload_agents(self):
        if self.planner_agent is not None:
            logging.info("子エージェントをVRAMからアンロードしています...")
            self.planner_agent = None
            self.executor_agent = None
            self.analyzer_agent = None
            import gc
            gc.collect()
            torch.cuda.empty_cache()
            logging.info("子エージェントのアンロードが完了しました。")

    def _initialize_system_prompt(self) -> None:
        system_prompt = (
            "あなたはCappuccinoという名前の、ユーザーの多様な要求に応えることができる汎用AIアシスタントです。\n"
            "思考プロセスは日本語で行い、ユーザーへの応答も日本語で行ってください。"
        )
        self.messages.append({"role": "system", "content": system_prompt})

    async def run(self, user_query: str) -> str:
        self.load_agents()
        try:
            plan_queue = asyncio.Queue()
            result_queue = asyncio.Queue()
            await self.add_message("user", user_query)
            tools_schema = await self.tool_manager.get_tools_schema()
            
            planner_task = asyncio.create_task(self.planner_agent.plan(user_query, plan_queue, tools_schema))
            executor_task = asyncio.create_task(self.executor_agent.execute_task_from_queue(plan_queue, result_queue))
            
            await planner_task
            await plan_queue.join()
            
            executor_task.cancel()
            try: await executor_task
            except asyncio.CancelledError: logging.info("ExecutorAgentタスクは正常にキャンセルされました。")

            results = []
            while not result_queue.empty():
                results.append(await result_queue.get())
            
            if not results:
                logging.warning("結果キューが空です。Analyzerは実行されません。")
                analysis = "タスクを実行しましたが、明確な結果は得られませんでした。"
            else:
                # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
                # ★★★ ここがバグの修正点です ★★★
                # AnalyzerAgentに渡す引数を修正
                analysis = await self.analyzer_agent.analyze(user_query, results)
                # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
            
            await self.add_message("assistant", analysis)
            return analysis
        
        except Exception as e:
            logging.error(f"CappuccinoAgent.runでエラー: {e}", exc_info=True)
            return f"申し訳ありません、処理中にエラーが発生しました: {e}"

    async def add_message(self, role: str, content: str, **kwargs) -> None:
        message: Dict[str, Any] = {"role": role, "content": content}
        message.update(kwargs)
        self.messages.append(message)
        logging.info(f"Added message: {message}")