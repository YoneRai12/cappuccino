# agents/planner_agent.py (最終・確定版)
import asyncio
import logging
import json
from typing import List, Dict, Any

from .base_agent import BaseAgent

class PlannerAgent(BaseAgent):
    async def plan(self, user_query: str, plan_queue: asyncio.Queue, tools_schema: List[Dict[str, Any]]):
        try:
            tools_json = json.dumps(tools_schema, indent=2, ensure_ascii=False)
            prompt = (f"あなたは、ユーザーの要求を分析し、実行可能なタスク計画をJSON形式で出力する計画AIです。\n"
                      f"利用可能なツール:\n{tools_json}\n\n"
                      f"ユーザーの要求: \"{user_query}\"\n\n"
                      f"JSON形式の計画のみを出力してください。各ステップには'task'と'dependencies'を含めてください。")
            response_json = await self.call_llm(prompt)
            if response_json.strip().startswith("```json"): response_json = response_json.strip()[7:-3].strip()
            plan = json.loads(response_json)
            logging.info(f"生成された計画: {plan}")
            for task in plan: await plan_queue.put(task)
        except Exception as e:
            logging.error(f"計画作成エラー: {e}", exc_info=True)
            await plan_queue.put({"task": user_query, "dependencies": []})