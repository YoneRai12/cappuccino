# cappuccino_agent.py (VRAM管理＋役割分担の完全無欠・最終版)
import asyncio
import logging
from typing import Any, Dict, List, Optional
import os
import torch

# ★★★ 私が消してしまっていたインポートを、ここに戻しました ★★★
from agents import PlannerAgent, ExecutorAgent, AnalyzerAgent
from tool_manager import ToolManager
from state_manager import StateManager
from self_improver import SelfImprover
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class CappuccinoAgent:
    def __init__(self, api_key: str, api_base: str, db_path: str = "agent_state.db", tool_manager: Optional[ToolManager] = None):
        self.api_key = api_key
        self.api_base = api_base
        self.tool_manager = tool_manager or ToolManager()
        
        # 初期化時にはエージェントをロードしない (Noneのまま)
        self.planner_agent: Optional[PlannerAgent] = None
        self.executor_agent: Optional[ExecutorAgent] = None
        self.analyzer_agent: Optional[AnalyzerAgent] = None
        
        self.tool_manager.set_agent(self)
        self.state_manager = StateManager(db_path=db_path)
        self.self_improver = SelfImprover(self.state_manager, self.tool_manager, self.api_key)
        self.messages: List[Dict[str, Any]] = []
        self._initialize_system_prompt()

    def load_agents(self):
        """子エージェントをVRAMにロードする"""
        if self.planner_agent is None:
            logging.info("子エージェントをVRAMにロードしています...")
            planner_model = os.getenv("OLLAMA_PLANNER_MODEL", "gemma:latest")
            analyzer_model = os.getenv("OLLAMA_ANALYZER_MODEL", "llama3.1:latest")
            
            planner_system_prompt = "You are an AI assistant that strictly converts user requests into a JSON array of tasks. You must only output the raw JSON array, with no explanatory text before or after."
            analyzer_system_prompt = "You are an AI assistant that analyzes task results and generates a final, friendly, and natural user-facing response in Japanese."
            
            self.planner_agent = PlannerAgent(api_key=self.api_key, api_base=self.api_base, model=planner_model, system_prompt=planner_system_prompt)
            self.executor_agent = ExecutorAgent(tool_manager=self.tool_manager, api_key=self.api_key, api_base=self.api_base, model=planner_model, system_prompt=planner_system_prompt)
            self.analyzer_agent = AnalyzerAgent(api_key=self.api_key, api_base=self.api_base, model=analyzer_model, system_prompt=analyzer_system_prompt)
            logging.info("子エージェントのロードが完了しました。")

    def unload_agents(self):
        """子エージェントをVRAMからアンロードする"""
        if self.planner_agent is not None:
            logging.info("子エージェントをVRAMからアンロードしています...")
            self.planner_agent = None
            self.executor_agent = None
            self.analyzer_agent = None
            import gc; gc.collect(); torch.cuda.empty_cache()
            logging.info("子エージェントのアンロードが完了しました。")

    def _initialize_system_prompt(self):
        """システムプロンプトを初期化"""
        system_prompt = (
            "あなたはCappuccinoという名前の、ユーザーの多様な要求に応えることができる汎用AIアシスタントです。\n"
            "思考プロセスは日本語で行い、ユーザーへの応答も日本語で行ってください。"
        )
        self.messages.append({"role": "system", "content": system_prompt})

    async def run(self, user_query: str) -> str:
        """エージェントの実行サイクルを非同期で管理する"""
        self.load_agents() # 実行前に必ずロード
        results = [] # resultsをここで初期化
        try:
            plan_queue, result_queue = asyncio.Queue(), asyncio.Queue()
            await self.add_message("user", user_query)
            tools_schema = await self.tool_manager.get_tools_schema()
            
            planner_task = asyncio.create_task(self.planner_agent.plan(user_query, plan_queue, tools_schema))
            executor_task = asyncio.create_task(self.executor_agent.execute_task_from_queue(plan_queue, result_queue))
            
            await planner_task
            await plan_queue.join()
            executor_task.cancel()
            try: await executor_task
            except asyncio.CancelledError: pass

            while not result_queue.empty(): results.append(await result_queue.get())
            
            if not results: analysis = "タスクを実行しましたが、明確な結果は得られませんでした。"
            else: analysis = await self.analyzer_agent.analyze(user_query, results)
            
            await self.add_message("assistant", analysis)
            return analysis
        
        except Exception as e:
            logging.error(f"CappuccinoAgent.runでエラー: {e}", exc_info=True)
            return f"エラーが発生しました: {e}"
        
        finally:
            image_generated = any("画像を生成しました" in str(r.get("result", "")) for r in results)
            if image_generated:
                logging.info("画像生成タスクが完了したため、LLMをアンロードします。")
                self.unload_agents()

    async def add_message(self, role: str, content: str, **kwargs):
        """メッセージを追加する"""
        self.messages.append({"role": role, "content": content, **kwargs})