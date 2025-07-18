# agents/planner_agent.py (f-stringのバグを修正した最終完成版)
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
            
            # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
            # ★★★ ここが、f-stringのバグの修正点です ★★★
            #
            # f-stringの中で { や } をただの文字として使いたい場合は、
            # {{ や }} のように二重にする必要があります。
            prompt = (
                f"You are a planning AI. Your task is to create a JSON array of tasks to fulfill the user's request by selecting tools from the provided list.\n"
                f"### Available Tools:\n{tools_json}\n\n"
                f"### User Request:\n\"{user_query}\"\n\n"
                f"### INSTRUCTIONS:\n"
                f"- Your response MUST be ONLY the raw JSON array (`[...]`), with no other text or explanations."
            )
            # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

            raw_response = await self.call_llm(prompt)
            logging.info(f"LLMからの生計画応答: {raw_response}")
            
            match = re.search(r'\[.*\]', raw_response, re.DOTALL)
            if not match: raise ValueError("Response does not contain a valid JSON array.")

            json_str = match.group(0)
            json_str_no_trailing_comma = re.sub(r',\s*([]}])', r'\1', json_str)

            plan = json.loads(json_str_no_trailing_comma)
            logging.info(f"生成された計画: {plan}")
            for task in plan: await plan_queue.put(task)

        except Exception as e:
            logging.error(f"計画作成エラー: {e}", exc_info=True)
            await plan_queue.put({
                "task": "respond_to_user", "dependencies": [],
                "parameters": {"text": f"計画の作成に失敗しました。"}
            })