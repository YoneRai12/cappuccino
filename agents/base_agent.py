# agents/base_agent.py (新規作成・最終確定版)
import logging
from openai import AsyncOpenAI

class BaseAgent:
    """すべてのエージェントの基本となるクラス。LLMクライアントを保持します。"""
    def __init__(self, llm: AsyncOpenAI):
        self.llm_client = llm

    async def call_llm(self, prompt: str) -> str:
        """LLMを呼び出すための共通関数。"""
        if not self.llm_client:
            raise RuntimeError("LLM client not configured in BaseAgent")
        try:
            response = await self.llm_client.chat.completions.create(
                model="llama3", 
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            content = response.choices[0].message.content
            return content.strip() if content else ""
        except Exception as e:
            logging.error(f"Error calling LLM: {e}", exc_info=True)
            return f"エラー: LLMの呼び出しに失敗しました。 {e}"