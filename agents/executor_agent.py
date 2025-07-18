# agents/executor_agent.py（最終完成版）
import asyncio
import logging
from typing import Dict, Any
from .base_agent import BaseAgent
from tool_manager import ToolManager

class ExecutorAgent(BaseAgent):
    def __init__(self, tool_manager: ToolManager, api_key: str, api_base: str, model: str, system_prompt: str):
        super().__init__(api_key=api_key, api_base=api_base, model=model, system_prompt=system_prompt)
        self.tool_manager = tool_manager

    async def execute_task_from_queue(self, plan_queue: asyncio.Queue, result_queue: asyncio.Queue):
        while True:
            try:
                task = await plan_queue.get()
                logging.info(f"🛠️ ExecutorAgentが受け取ったタスク: {task}")

                function_name = None
                parameters = {}

                if isinstance(task, dict):
                    if "function" in task:
                        function_name = task["function"]
                        parameters = task.get("parameters", {})
                    elif "task" in task:
                        function_name = task["task"]
                        parameters = task.get("parameters", {})

                if not function_name:
                    raise ValueError("タスクに 'function' もしくは 'task' がありません。")

                tool_func = self.tool_manager.get_tool_by_name(function_name)
                if not tool_func:
                    raise ValueError(f"ツール '{function_name}' が見つかりません。")

                output = await tool_func(**parameters)

                result = {
                    "function": function_name,
                    "parameters": parameters,
                    "output": output
                }

                logging.info(f"✅ ExecutorAgentの結果: {result}")
                await result_queue.put(result)
                plan_queue.task_done()

            except asyncio.CancelledError:
                break  # 終了指示
            except Exception as e:
                logging.error(f"ExecutorAgentでタスク実行中にエラー: {e}", exc_info=True)
                plan_queue.task_done()
