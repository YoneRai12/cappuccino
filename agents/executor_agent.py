# agents/executor_agent.py (すべての関数を復元した最終完成版)
import asyncio
import logging
import json
import inspect
from typing import Dict, Any, List

from .base_agent import BaseAgent
from tool_manager import ToolManager

class ExecutorAgent(BaseAgent):
    def __init__(self, tool_manager: ToolManager, api_key: str, api_base: str, model: str, system_prompt: str):
        # ★★★ ここが重要！ ★★★
        # 親クラスの__init__を呼び出す
        super().__init__(api_key=api_key, api_base=api_base, model=model, system_prompt=system_prompt)
        self.tool_manager = tool_manager

    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
    # ★★★ 省略していた、すべての関数の中身をここに戻しました ★★★
    
    async def execute_task_from_queue(self, plan_queue: asyncio.Queue, result_queue: asyncio.Queue):
        while True:
            try:
                task_info = await plan_queue.get()
                
                if isinstance(task_info, dict) and "function" in task_info:
                    function_details = task_info.get("function", {})
                    tool_name = function_details.get("name")
                    tool_args = function_details.get("parameters", {})
                    result = await self.handle_tool_call(tool_name, tool_args)
                elif isinstance(task_info, dict) and "task" in task_info:
                    tool_name = task_info.get("task")
                    tool_args = task_info.get("parameters", {})
                    result = await self.handle_tool_call(tool_name, tool_args)
                else:
                    result = str(task_info)
                
                await result_queue.put({"task": task_info, "result": result})
                plan_queue.task_done()

            except asyncio.CancelledError: break
            except Exception as e:
                if 'plan_queue' in locals() and not plan_queue.empty(): plan_queue.task_done()

    async def handle_tool_call(self, tool_name: str, tool_args: Dict) -> Any:
        if not hasattr(self.tool_manager, tool_name):
            return f"エラー: ツール '{tool_name}' が見つかりません。"
        
        try:
            tool_method = getattr(self.tool_manager, tool_name)
            sig = inspect.signature(tool_method)
            valid_args = {k: v for k, v in tool_args.items() if k in sig.parameters}
            
            if asyncio.iscoroutinefunction(tool_method):
                return await tool_method(**valid_args)
            else:
                return await asyncio.get_running_loop().run_in_executor(None, lambda: tool_method(**valid_args))
        except Exception as e:
            return f"エラー: ツール '{tool_name}' の実行に失敗しました - {e}"
    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★