# agents/base_agent.py (Ollamaの仕様に完全に準拠した最終版)
import logging
import os
from openai import AsyncOpenAI
from typing import List, Dict

class BaseAgent:
    def __init__(self, api_key: str, api_base: str, model: str, system_prompt: str):
        self.api_key = os.getenv("OPENAI_API_KEY", api_key)
        self.api_base = os.getenv("OPENAI_API_BASE", api_base)
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
            
            # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
            # ★★★ ここが最重要の修正点 ★★★
            #
            # Ollamaが対応していない 'format' 引数を完全に削除。
            # これでAPI呼び出しは確実に成功する。
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1
            )
            #
            # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

            content = response.choices[0].message.content
            return content.strip() if content else ""

        except Exception as e:
            logging.error(f"LLM呼び出しエラー (Model: {self.model}): {e}", exc_info=True)
            return f"LLMとの通信中にエラーが発生しました: {e}"