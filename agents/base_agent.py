# agents/base_agent.py (Web検索を禁止する最終完成版)
import logging
from typing import List, Dict, Optional

import os
from config import settings
from local_llm import LocalLLM

try:
    from openai import AsyncOpenAI
except Exception:
    AsyncOpenAI = None

class BaseAgent:
    def __init__(self, api_key: Optional[str], api_base: Optional[str], model: str, system_prompt: str):
        self.api_key = api_key or settings.openai_api_key
        self.api_base = api_base or (settings.openai_api_base or "")
        self.model = model
        self.system_prompt = system_prompt

        logging.info(
            f"エージェント初期化中... Model: {self.model}, Role: '{self.system_prompt[:30]}...'"
        )

        use_local = bool(settings.local_model_path) or not settings.openai_api_key
        if use_local:
            model_path = settings.local_model_path
            if not model_path:
                raise RuntimeError(
                    "OPENAI_API_KEY が設定されていないため LOCAL_MODEL_PATH の指定が必要です"
                )
            logging.info(f"ローカルモデルを使用します: {model_path}")
            self.llm_client = LocalLLM(model_path)
        else:
            if AsyncOpenAI is None:
                raise RuntimeError(
                    "OpenAI client unavailable and LOCAL_MODEL_PATH not set"
                )
            self.llm_client = AsyncOpenAI(api_key=self.api_key, base_url=self.api_base)

    async def call_llm(self, prompt: str) -> str:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        try:
            logging.info(f"LLM呼び出し中... Model: {self.model}")

            if isinstance(self.llm_client, LocalLLM):
                content = await self.llm_client.chat(prompt)
                return content.strip()

            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0,
                tool_choice="none"
            )

            content = response.choices[0].message.content
            return content.strip() if content else ""

        except Exception as e:
            logging.error(f"LLM呼び出しエラー (Model: {self.model}): {e}", exc_info=True)
            return f"LLMとの通信中にエラーが発生しました: {e}"