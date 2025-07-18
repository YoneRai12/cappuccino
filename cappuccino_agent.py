# cappuccino_agent.py
import asyncio
import logging
from typing import Any, Dict, List, Optional
import os

from agents import PlannerAgent, ExecutorAgent, AnalyzerAgent
from tool_manager import ToolManager
from state_manager import StateManager
from self_improver import SelfImprover

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class CappuccinoAgent:
    def __init__(self, api_key: str, api_base: str, db_path: str = "agent_state.db", tool_manager: Optional[ToolManager] = None):
        """
        エージェントを初期化し、必要なコンポーネントをすべて準備します。
        """
        self.api_key = api_key
        self.api_base = api_base
        self.tool_manager = tool_manager or ToolManager()
        
        planner_model = os.getenv("OLLAMA_PLANNER_MODEL", "gemma:latest")
        analyzer_model = os.getenv("OLLAMA_ANALYZER_MODEL", "llama3.1:latest")
        
        planner_system_prompt = (
            "You are a task planning AI. Your ONLY job is to convert a user request into a JSON array of tasks using ONLY the provided tools. "
            "Follow these rules STRICTLY:\n"
            "1. Analyze the user's request.\n"
            "2. If the user is explicitly asking for an image, plan to use the 'generate_image' tool.\n"
            "3. For ANY other request (greetings, questions, etc.), you MUST plan to use ONLY the 'respond_to_user' tool.\n"
            "4. Do NOT add any extra tasks. Do NOT try to be helpful by adding image generation for simple questions.\n"
            "5. Your output MUST be ONLY the raw JSON array."
        )
        analyzer_system_prompt = "You are an AI assistant that analyzes task results and generates a final, friendly, and natural user-facing response in Japanese."
        
        self.planner_agent = PlannerAgent(api_key=api_key, api_base=api_base, model=planner_model, system_prompt=planner_system_prompt)
        self.executor_agent = ExecutorAgent(tool_manager=self.tool_manager, api_key=api_key, api_base=api_base, model=planner_model, system_prompt=planner_system_prompt)
        self.analyzer_agent = AnalyzerAgent(api_key=api_key, api_base=api_base, model=analyzer_model, system_prompt=analyzer_system_prompt)
        
        self.state_manager = StateManager(db_path=db_path)
        self.self_improver = SelfImprover(self.state_manager, self.tool_manager, self.api_key)
        self.messages: List[Dict[str, Any]] = []
        self._initialize_system_prompt()

    def _initialize_system_prompt(self):
        """システムプロンプトを初期化"""
        system_prompt = (
            "あなたはCappuccinoという名前の、ユーザーの多様な要求に応えることができる汎用AIアシスタントです。\n"
            "思考プロセスは日本語で行い、ユーザーへの応答も日本語で行ってください。"
        )
        self.messages.append({"role": "system", "content": system_prompt})
    async def run(self, user_query: str) -> str:
        """エージェントの実行サイクルを非同期で管理する"""
        try:
            plan_queue = asyncio.Queue()
            result_queue = asyncio.Queue()

            await self.add_message("user", user_query)
            logging.info("📥 PlannerAgent にタスクを依頼します...")
            tools_schema = await self.tool_manager.get_tools_schema()
            
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
                # ↓ デバッグ用にAnalyzerを強制的に呼び出す
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

        

  

    async def add_message(self, role: str, content: str, **kwargs) -> None:
        """会話履歴にメッセージを追加する"""
        message: Dict[str, Any] = {"role": role, "content": content}
        message.update(kwargs)
        self.messages.append(message)
        logging.info(f"Added message: {message}")

