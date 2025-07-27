# agents/base_agent.py (Web検索を禁止する最終完成版)
import logging
import os
from openai import AsyncOpenAI
from typing import List, Dict, Optional

class BaseAgent:
    def __init__(self, api_key: Optional[str], api_base: Optional[str], model: str, system_prompt: str):
        from config import settings
        self.api_key = api_key or settings.openai_api_key
        self.api_base = api_base or (settings.openai_api_base or "")
        self.model = model
        self.system_prompt = system_prompt
        
        logging.info(f"エージェント初期化中... Model: {self.model}, Role: '{self.system_prompt[:30]}...'")
        self.llm_client = AsyncOpenAI(api_key=self.api_key, base_url=self.api_base)

    async def call_llm(self, prompt: str) -> str:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        try:
            logging.info(f"LLM呼び出し中... Model: {self.model}")
            
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0, # 創造性をゼロにし、指示に絶対服従させる
                tool_choice="none" # ★ GrokやOllamaに「ツールを使うな」と厳命する
            )

            content = response.choices[0].message.content
            return content.strip() if content else ""

        except Exception as e:
            logging.error(f"LLM呼び出しエラー (Model: {self.model}): {e}", exc_info=True)
            return f"LLMとの通信中にエラーが発生しました: {e}"