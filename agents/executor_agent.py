# agents/executor_agent.py (最終・確定版)
import sys
import os
import asyncio
import logging
import json
import re
from typing import Dict, Any

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from .base_agent import BaseAgent
from tool_manager import ToolManager

class ExecutorAgent(BaseAgent):
    def __init__(self, tool_manager: ToolManager, llm):
        super().__init__(llm); self.tool_manager = tool_manager
    async def execute(self, plan_queue: asyncio.Queue, result_queue: asyncio.Queue):
        while True:
            try:
                task = await plan_queue.get()
                if not task or not task.get("task"):
                    plan_queue.task_done()
                    continue
                    
                logging.info(f"タスク実行中: {task['task']}")
                tools_schema = await self.tool_manager.get_tools_schema()
                prompt = (f"あなたは与えられたタスクを実行するAIです。最適なツールを選択・使用し、結果を返してください。\n"
                          f"利用可能なツール:\n{json.dumps(tools_schema, indent=2, ensure_ascii=False)}\n\n"
                          f"実行すべきタスク: \"{task['task']}\"\n\n"
                          f"ツールを呼び出す場合は、'tool_calls'を含むJSONコードブロックのみを、他のテキストは含めずに返してください。例:\n"
                          f"```json\n{{\"tool_calls\": [{{\"function\": {{\"name\": \"ツール名\", \"arguments\": \"{{\\\"引数名\\\": \\\"値\\\"}}\"}}}}], ...}}\n```")
                
                response = await self.call_llm(prompt)

                # ★★★★★ ここからが最も重要な変更点 ★★★★★
                result = response # デフォルトはLLMの生応答
                
                # 正規表現を使って、おしゃべりな返答の中からJSON部分だけを賢く抜き出す
                match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
                json_str = ""
                if match:
                    json_str = match.group(1)
                else:
                    # コードブロックが見つからない場合は、応答全体がJSONかもしれないと仮定
                    if response.strip().startswith("{"):
                        json_str = response.strip()

                if json_str:
                    try:
                        tool_call_data = json.loads(json_str)
                        if "tool_calls" in tool_call_data:
                            calls = tool_call_data["tool_calls"]
                            # ここでツールを実行し、その結果をresultに格納する
                            result = await self.handle_tool_call(calls[0] if isinstance(calls, list) else calls)
                    except json.JSONDecodeError:
                        logging.error(f"JSONパースに失敗: {json_str}")
                        # パースに失敗した場合は、LLMの応答をそのまま結果とする
                        result = response
                # ★★★★★★★★★★★★★★★★★★★★★★★★★★★

                logging.info(f"タスク結果: {result}")
                await result_queue.put({"task": task, "result": result}); plan_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"タスク実行エラー: {e}", exc_info=True)
                plan_queue.task_done()

    async def handle_tool_call(self, tool_call: Dict[str, Any]) -> Any:
        function_details = tool_call.get("function", {})
        tool_name = function_details.get("name")
        tool_args_str = function_details.get("arguments", "{}")

        try:
            tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
            if isinstance(tool_args, str): tool_args = json.loads(tool_args)
        except json.JSONDecodeError:
             return f"エラー: 引数の形式が不正です。 ({tool_args_str})"
        
        if hasattr(self.tool_manager, tool_name):
            tool_method = getattr(self.tool_manager, tool_name)
            import inspect
            sig = inspect.signature(tool_method)
            filtered_args = {k: v for k, v in tool_args.items() if k in sig.parameters}
            
            if asyncio.iscoroutinefunction(tool_method):
                return await tool_method(**filtered_args)
            else:
                return await asyncio.get_running_loop().run_in_executor(None, lambda: tool_method(**filtered_args))
        return f"エラー: ツール '{tool_name}' が見つかりません。"