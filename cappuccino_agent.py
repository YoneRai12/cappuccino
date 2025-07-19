# cappuccino_agent.py

import asyncio
import logging
from typing import Any, Dict, Optional
from agents import PlannerAgent, ExecutorAgent, AnalyzerAgent
from tool_manager import ToolManager
from state_manager import StateManager
from self_improver import SelfImprover

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class CappuccinoAgent:
    def __init__(self, api_key: Optional[str] = None, api_base: Optional[str] = None):
        self.api_key = api_key
        self.api_base = api_base

        self.messages = []

        # モデルとシステムプロンプトの設定
        planner_model = "llama3.1:latest"
        planner_system_prompt = "You are a planner AI that plans tasks based on user input."

        executor_model = "llama3.1:latest"
        executor_system_prompt = "You are an executor AI that executes tasks."

        analyzer_model = "llama3.1:latest"
        analyzer_system_prompt = "You are an analyzer AI that analyzes task results."

        # ToolManager と StateManager を初期化
        self.tool_manager = ToolManager()
        self.state_manager = StateManager()

        # 各エージェントを初期化
        self.planner_agent = PlannerAgent(
            api_key=api_key or "",
            api_base=api_base or "",
            model=planner_model,
            system_prompt=planner_system_prompt
        )
        self.executor_agent = ExecutorAgent(
            tool_manager=self.tool_manager,
            api_key=api_key or "",
            api_base=api_base or "",
            model=executor_model,
            system_prompt=executor_system_prompt
        )
        self.analyzer_agent = AnalyzerAgent(
            api_key=api_key or "",
            api_base=api_base or "",
            model=analyzer_model,
            system_prompt=analyzer_system_prompt
        )

        # SelfImprover は state_manager と tool_manager を渡す
        self.self_improver = SelfImprover(
            state_manager=self.state_manager,
            tool_manager=self.tool_manager
        )

    async def run(self, user_query: str) -> str:
        try:
            await self.add_message("user", user_query)
            logging.info("📥 PlannerAgent にタスクを依頼します...")

            tools_schema = await self.tool_manager.get_tools_schema()
            plan_queue = asyncio.Queue()
            result_queue = asyncio.Queue()

            planner_task = asyncio.create_task(
                self.planner_agent.plan(user_query, plan_queue, tools_schema)
            )
            executor_task = asyncio.create_task(
                self.executor_agent.execute_task_from_queue(plan_queue, result_queue)
            )

            await planner_task
            logging.info("✅ PlannerAgent が完了しました。")

            await plan_queue.join()
            logging.info("✅ ExecutorAgent がタスクを全て処理しました。（plan_queue.join 完了）")

            executor_task.cancel()
            try:
                await executor_task
            except asyncio.CancelledError:
                logging.info("🛑 ExecutorAgentタスクは正常にキャンセルされました。")

            results = []
            while not result_queue.empty():
                result = await result_queue.get()
                logging.info(f"📦 ExecutorAgentの結果: {result}")
                results.append(result)

            if not results:
                logging.warning("⚠️ ExecutorAgentの結果が空です。Analyzerはスキップされます。")
                analysis = await self.analyzer_agent.analyze(
                    user_query,
                    [{"function": "respond_to_user", "output": "仮の出力です"}]
                )
                logging.info("🧪 Analyzer に仮出力を渡しました。")
            else:
                logging.info("🔍 AnalyzerAgent による分析を開始します...")
                analysis = await self.analyzer_agent.analyze(user_query, results)
                logging.info(f"💬 AnalyzerAgent の分析結果: {analysis}")

            await self.add_message("assistant", analysis)
            return analysis

        except Exception as e:
            logging.error(f"❌ CappuccinoAgent.runでエラー: {e}", exc_info=True)
            return f"申し訳ありません、処理中にエラーが発生しました: {e}"

    async def process(self, prompt: str) -> str:
        # 必要に応じてLLMやDBをここに追加
        return f"Processed: {prompt}"

    async def add_message(self, role: str, content: str, **kwargs) -> None:
        """会話履歴にメッセージを追加する"""
        message: Dict[str, Any] = {"role": role, "content": content}
        message.update(kwargs)
        self.messages.append(message)
        logging.info(f"📝 Added message: {message}")
