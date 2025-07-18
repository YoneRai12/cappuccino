# agents/planner_agent.py (矛盾を解消した最終完成版)
import asyncio
import logging
import json
import re
from typing import List, Dict, Any

from .base_agent import BaseAgent

class PlannerAgent(BaseAgent):
    async def plan(self, user_query: str, plan_queue: asyncio.Queue, tools_schema: List[Dict[str, Any]]):
        try:
            tools_json = json.dumps(tools_schema, indent=2, ensure_ascii=False)
            prompt = (
                f"You are an AI assistant that converts user requests into a JSON array of tasks.\n"
                f"### Available Tools:\n{tools_json}\n\n"
                f"### User Request:\n\"{user_query}\"\n\n"
                f"### INSTRUCTIONS:\n"
                f"- Create a plan as a JSON array to fulfill the user request.\n"
                f"- Each task object in the array MUST contain a key named 'task' which specifies the tool to use.\n"
                f"- Your response MUST only be the raw JSON array, with no other text."
            )
            
            # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
            # ★★★ ここが最重要の修正点です ★★★
            #
            # 存在しない 'use_json_format' 引数を削除。
            # これで BaseAgent との連携が正しく行われる。
            raw_response = await self.call_llm(prompt)
            #
            # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
            
            logging.info(f"LLMからの生計画応答: {raw_response}")
            
            match = re.search(r'\[.*\]', raw_response, re.DOTALL)
            if not match: raise ValueError("Response does not contain a valid JSON array.")

            plan = json.loads(match.group(0))
            logging.info(f"生成された計画: {plan}")
            for task in plan: await plan_queue.put(task)

        except Exception as e:
            logging.error(f"計画作成エラー: {e}", exc_info=True)
            await plan_queue.put({
                "task": "respond_to_user", "dependencies": [],
                "parameters": {"text": f"計画の作成に失敗しました。"}
            })