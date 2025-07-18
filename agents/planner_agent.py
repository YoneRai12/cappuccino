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
                f"You are a planning AI. Your task is to create a JSON array of tasks to fulfill the user's request by selecting tools from the provided list.\n"
                f"### Available Tools:\n{tools_json}\n\n"
                f"### User Request:\n\"{user_query}\"\n\n"
                f"### INSTRUCTIONS:\n"
                f"- Your response MUST be ONLY the raw JSON array (`[...]`), with no other text or explanations.\n"
                f"- DO NOT use image generation unless the user explicitly asks for it.\n"
                f"- Avoid suggesting image generation as a default response.\n"
                f"- If using `generate_image`, you MAY include optional fields:\n"
                f"    - `num_inference_steps`: (e.g. 40)\n"
                f"    - `guidance_scale`: (e.g. 12.5)\n"
                f"    - `seed`: fixed number for reproducibility\n"
                f"    - `width`, `height`: up to 1024px each\n"
            )

            raw_response = await self.call_llm(prompt)
            logging.info(f"LLMからの生計画応答: {raw_response}")

            match = re.search(r'\[.*\]', raw_response, re.DOTALL)
            if not match:
                raise ValueError("Response does not contain a valid JSON array.")

            json_str = match.group(0)
            json_str_no_trailing_comma = re.sub(r',\s*([]}])', r'\1', json_str)
            plan = json.loads(json_str_no_trailing_comma)

            # 👇 画像生成タスクのプロンプトを強化する
            for task in plan:
                if task.get("function") == "generate_image" and "prompt" in task:
                    original_prompt = task["prompt"]
                    enhanced_prompt = await self.enhance_prompt(original_prompt)
                    task["prompt"] = enhanced_prompt
                    logging.info(f"🔧 プロンプト強化: {original_prompt} → {enhanced_prompt}")
                await plan_queue.put(task)

        except Exception as e:
            logging.error(f"計画作成エラー: {e}", exc_info=True)
            await plan_queue.put({
                "function": "respond_to_user", "text": "計画の作成に失敗しました。"
            })

    async def enhance_prompt(self, original: str) -> str:
        """プロンプトをより美しく、詳細にする"""
        enhance_prompt = (
            f"以下の画像生成指示を、より詳細で美しく、構図や光・質感なども加味して英語でリライトしてください。\n"
            f"ユーザーの指示: {original}\n\n"
            f"条件:\n"
            f"- 出力は英語のみ。\n"
            f"- 説明や補足はつけない。\n"
            f"- 写実的、幻想的、またはアートスタイルの指定も含めてよい。\n"
        )
        result = await self.call_llm(enhance_prompt)
        return result.strip().strip('"')
