# agents/executor_agent.py (LLMへの再確認をやめ、直接ツールを実行する最終版)
import asyncio
import logging
import json
import inspect
from typing import Dict, Any, List

from .base_agent import BaseAgent
from tool_manager import ToolManager

class ExecutorAgent(BaseAgent):
    """
    計画されたタスクを忠実に実行し、ツールを呼び出すエージェント。
    """
    def __init__(self, tool_manager: ToolManager, **kwargs):
        super().__init__(**kwargs)
        self.tool_manager = tool_manager

    async def execute_task_from_queue(self, plan_queue: asyncio.Queue, result_queue: asyncio.Queue):
        """キューからタスクを取得し、実行サイクルを回す"""
        while True:
            try:
                task_info = await plan_queue.get()
                
                # ★★★ ここが最重要の修正点 ★★★
                #
                # 計画されたタスク情報(task_info)を直接ツールハンドラに渡す。
                # これにより、LLMに再度問い合わせるという無駄で危険な処理を完全にスキップする。
                #
                if isinstance(task_info, dict):
                    logging.info(f"計画されたタスクを実行します: {task_info}")
                    result = await self.handle_planned_task(task_info)
                else:
                    # 予期せぬ形式の場合は、そのまま最終結果として扱う
                    logging.warning(f"不明な形式のタスクのため、そのまま結果として扱います: {task_info}")
                    result = str(task_info)
                
                logging.info(f"タスク結果: {result}")
                await result_queue.put({"task": task_info, "result": result})
                
                plan_queue.task_done()

            except asyncio.CancelledError:
                logging.info("ExecutorAgentのタスク実行がキャンセルされました。")
                break
            except Exception as e:
                logging.error(f"タスク実行ループで予期せぬエラー: {e}", exc_info=True)
                if 'plan_queue' in locals() and not plan_queue.empty():
                    plan_queue.task_done()

    async def handle_planned_task(self, task_info: Dict[str, Any]) -> Any:
        """計画されたタスク情報に基づいて、ツールを直接呼び出す"""
        # Plannerが生成したタスク名とパラメータを取得
        tool_name = task_info.get("task")
        tool_args = task_info.get("parameters", {})

        if not tool_name:
            return "エラー: 実行すべきタスク名が計画に含まれていません。"
        if not hasattr(self.tool_manager, tool_name):
            # ツールが見つからない場合、それは通常の会話かもしれないのでLLMに最終回答を生成させる
            logging.warning(f"ツール '{tool_name}' が見つかりません。LLMに最終回答を依頼します。")
            prompt = f"以下のユーザーの要求、または中間タスクに対して、最終的な応答を生成してください: '{tool_name}'"
            return await self.call_llm(prompt)
        
        try:
            tool_method = getattr(self.tool_manager, tool_name)
            
            sig = inspect.signature(tool_method)
            valid_args = {k: v for k, v in tool_args.items() if k in sig.parameters}
            
            logging.info(f"ツール '{tool_name}' を引数 {valid_args} で直接呼び出します。")
            
            if asyncio.iscoroutinefunction(tool_method):
                return await tool_method(**valid_args)
            else:
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(None, lambda: tool_method(**valid_args))
        except Exception as e:
            logging.error(f"ツール '{tool_name}' の実行中にエラー: {e}", exc_info=True)
            return f"エラー: ツール '{tool_name}' の実行に失敗しました - {e}"