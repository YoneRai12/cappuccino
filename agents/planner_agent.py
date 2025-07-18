# agents/planner_agent.py (バグ修正・最終版)
import asyncio
import logging
import json
import re
from typing import List, Dict, Any

from .base_agent import BaseAgent

class PlannerAgent(BaseAgent):
    """
    ユーザーの要求を分析し、タスク計画を生成するエージェント。
    Llama 3.1のようなモデルからの非構造的な応答にも対応できるように修正済み。
    """
    async def plan(self, user_query: str, plan_queue: asyncio.Queue, tools_schema: List[Dict[str, Any]]):
        try:
            tools_json = json.dumps(tools_schema, indent=2, ensure_ascii=False)
            prompt = (f"あなたは、ユーザーの要求を分析し、実行可能なタスク計画をJSON形式で出力する計画AIです。\n"
                      f"利用可能なツール:\n{tools_json}\n\n"
                      f"ユーザーの要求: \"{user_query}\"\n\n"
                      f"思考プロセスは出力せず、JSON形式の計画のみを出力してください。各ステップには'task'と'dependencies'を含めてください。")
            
            raw_response = await self.call_llm(prompt)
            logging.info(f"LLMからの生応答: {raw_response}")

            # --- ここからが重要な変更点 (バグ修正) ---
            
            # 1. LLMの応答からJSON部分だけを正規表現で安全に抽出する
            match = re.search(r'```json\s*([\s\S]*?)\s*```', raw_response)
            if match:
                json_str = match.group(1)
            else:
                # ```json ``` が見つからない場合、応答全体がJSONであると仮定する
                json_str = raw_response

            # 2. 抽出した文字列をJSONとして解析
            plan = json.loads(json_str)
            logging.info(f"生成された計画: {plan}")
            for task in plan:
                await plan_queue.put(task)
            
            # --- ここまでが重要な変更点 ---

        except json.JSONDecodeError:
            logging.warning(f"計画JSONの解析に失敗。応答を直接の回答タスクとして扱います。応答: {raw_response}")
            await plan_queue.put({"task": raw_response, "dependencies": []})

        except Exception as e:
            logging.error(f"計画作成時に予期せぬエラーが発生: {e}", exc_info=True)
            await plan_queue.put({"task": user_query, "dependencies": []})