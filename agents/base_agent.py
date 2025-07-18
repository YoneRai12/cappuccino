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
        
        # agents/base_agent.py (VRAM管理の土台を追加した版)
import logging
from openai import AsyncOpenAI
import os

class BaseAgent:
    def __init__(self, api_key: str, api_base: str):
        self.api_key = api_key
        self.api_base = api_base
        self.llm_client = None
        self.load_model() # 初期化時にモデルをロード

    def load_model(self):
        """LLMクライアントを初期化（VRAMにロード）"""
        if self.llm_client is None:
            logging.info(f"LLMクライアントをロードしています... Base: {self.api_base}")
            self.llm_client = AsyncOpenAI(api_key=self.api_key, base_url=self.api_base)

    def unload_model(self):
        """LLMクライアントを破棄（VRAMからアンロード）"""
        if self.llm_client is not None:
            logging.info("LLMクライアントをアンロードしています...")
            self.llm_client = None
            # Pythonのガベージコレクションを促す
            import gc
            gc.collect()

    async def call_llm(self, prompt: str, chat_history: list = None):
        if self.llm_client is None:
            # モデルがアンロードされている場合は一時的にロードして実行
            logging.warning("LLMがアンロードされていました。一時的にロードして実行します。")
            self.load_model()

        messages = [{"role": "system", "content": "You are a helpful assistant."}]
        if chat_history:
            messages.extend(chat_history)
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = await self.llm_client.chat.completions.create(
                model=os.getenv("OLLAMA_MODEL", "llama3.1"), # .envからモデル名を取得、なければllama3.1
                messages=messages,
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"LLM呼び出しエラー: {e}", exc_info=True)
            return f"LLMとの通信エラー: {e}"