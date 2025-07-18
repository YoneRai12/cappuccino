# agents/executor_agent.py (最適化・安定化版)
import asyncio
import logging
import json
import re
import inspect
from typing import Dict, Any, List

from .base_agent import BaseAgent
from tool_manager import ToolManager

class ExecutorAgent(BaseAgent):
    """
    計画されたタスクを解釈し、ツールを実行するエージェント。
    LLMからの多様な応答形式に対応し、堅牢なエラーハンドリングを行う。
    """
    def __init__(self, tool_manager: ToolManager, **kwargs):
        # 継承元の__init__を呼び出す
        super().__init__(**kwargs)
        self.tool_manager = tool_manager

    async def execute_task_from_queue(self, plan_queue: asyncio.Queue, result_queue: asyncio.Queue):
        """キューからタスクを取得し、実行サイクルを回す"""
        while True:
            try:
                task_info = await plan_queue.get()
                
                # タスクの形式を正規化 (文字列で来ても辞書で来ても対応)
                if isinstance(task_info, str):
                    task_description = task_info
                elif isinstance(task_info, dict):
                    task_description = task_info.get("task", "名前のないタスク")
                else:
                    logging.warning(f"不明な形式のタスクをスキップ: {task_info}")
                    plan_queue.task_done()
                    continue
                
                logging.info(f"タスク実行開始: '{task_description}'")
                
                result = await self.run_single_task(task_description)
                
                logging.info(f"タスク結果: {result}")
                await result_queue.put({"task": task_info, "result": result})
                
                plan_queue.task_done()

            except asyncio.CancelledError:
                logging.info("ExecutorAgentのタスク実行がキャンセルされました。")
                break
            except Exception as e:
                logging.error(f"タスク実行ループで予期せぬエラー: {e}", exc_info=True)
                # エラーが発生しても、キューの処理は続ける
                if 'plan_queue' in locals() and not plan_queue.empty():
                    plan_queue.task_done()

    async def run_single_task(self, task_description: str) -> Any:
        """単一のタスク記述を解釈し、ツール呼び出しまたはLLMによる応答生成を行う"""
        try:
            tools_schema = await self.tool_manager.get_tools_schema()
            prompt = (
                f"あなたは与えられたタスクを実行するAIアシスタントです。\n"
                f"以下のツールが利用可能です:\n{json.dumps(tools_schema, indent=2, ensure_ascii=False)}\n\n"
                f"実行すべきタスク: \"{task_description}\"\n\n"
                f"このタスクを達成するために、上記リストから最適なツールを一つだけ選択し、"
                f"引数をJSON形式で指定してください。\n"
                f"応答は必ず 'tool_calls' キーを含むJSONコードブロックのみで返してください。他のテキストは一切不要です。\n"
                f"例:\n```json\n{{\"tool_calls\": [{{\"function\": {{\"name\": \"ツール名\", \"arguments\": {{\"引数名\": \"値\"}} }} }}]}}\n```\n"
                f"もし適切なツールがない、またはタスクが挨拶のような単純な応答の場合は、"
                f"ツールの代わりに最終的な答えを平文で直接返答してください。"
            )
            
            raw_response = await self.call_llm(prompt)
            logging.info(f"LLMからの生応答: {raw_response}")

            # 正規表現でJSONコードブロックを安全に抽出
            match = re.search(r"```json\s*(\{.*?\})\s*```", raw_response, re.DOTALL)
            if match:
                json_str = match.group(1)
                try:
                    data = json.loads(json_str)
                    tool_calls = data.get("tool_calls")
                    if isinstance(tool_calls, list) and len(tool_calls) > 0:
                        # ツール呼び出しを実行
                        return await self.handle_tool_call(tool_calls[0])
                except json.JSONDecodeError:
                    logging.warning(f"JSONの解析に失敗。LLMの応答をそのまま返します。JSON: {json_str}")
                    return raw_response
            
            # JSONが見つからない、またはtool_callsが含まれない場合は、LLMの応答が最終結果
            return raw_response

        except Exception as e:
            logging.error(f"単一タスクの実行中にエラー: {e}", exc_info=True)
            return f"エラー: タスクの処理中に問題が発生しました - {e}"

    async def handle_tool_call(self, tool_call: Dict[str, Any]) -> Any:
        """単一のツール呼び出しを処理する"""
        function_details = tool_call.get("function", {})
        tool_name = function_details.get("name")
        # 引数は辞書型で渡されることを期待
        tool_args = function_details.get("arguments", {})

        if not tool_name:
            return "エラー: 呼び出すツール名が指定されていません。"
        if not hasattr(self.tool_manager, tool_name):
            return f"エラー: ツール '{tool_name}' が見つかりません。"
        
        try:
            tool_method = getattr(self.tool_manager, tool_name)
            
            # 関数のシグネチャをチェックし、必要な引数のみを渡す
            sig = inspect.signature(tool_method)
            valid_args = {k: v for k, v in tool_args.items() if k in sig.parameters}
            
            logging.info(f"ツール '{tool_name}' を引数 {valid_args} で呼び出します。")
            
            if asyncio.iscoroutinefunction(tool_method):
                return await tool_method(**valid_args)
            else:
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(None, lambda: tool_method(**valid_args))
        except Exception as e:
            logging.error(f"ツール '{tool_name}' の実行中にエラー: {e}", exc_info=True)
            return f"エラー: ツール '{tool_name}' の実行に失敗しました - {e}"