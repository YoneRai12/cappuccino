# tool_manager.py (VRAM管理に特化した最適化版)
import logging
import asyncio
from typing import Any, Dict, List, Optional

# 画像生成関数をインポート
from image_generator import generate_image

class ToolManager:
    """
    ツールのスキーマ管理と、特にVRAMを大量に消費するツールの実行を管理するクラス。
    """
    def __init__(self, agent: Optional[Any] = None):
        self._agent = agent
        self.llm_is_loaded = True  # 初期状態ではLLMはロードされていると仮定

    def set_agent(self, agent: Any):
        """
        VRAM管理のために、親であるエージェントへの参照を保持する。
        """
        self._agent = agent
        # 親エージェントの状態をToolManagerの状態に同期させる
        self.llm_is_loaded = getattr(self._agent, 'agents_are_loaded', True)

    async def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        LLMに提示するための、利用可能なツールのJSONスキーマを返す。
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "generate_image",
                    "description": "テキストの説明文から画像を生成します。プロンプトは創造的で詳細な英語が望ましいです。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "生成したい画像の内容を詳細に記述したプロンプト。例: 'An astronaut cat riding a rocket, photorealistic'",
                            },
                        },
                        "required": ["prompt"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "respond_to_user",
                    "description": "挨拶や単純な応答など、ツールを使わずにユーザーに直接テキストで返信します。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "ユーザーに返信するテキストメッセージ。"
                            },
                        },
                        "required": ["text"],
                    },
                },
            },
            # 必要に応じて他のツール(search_webなど)もここに追加
        ]

    async def respond_to_user(self, text: str) -> str:
        """
        このツールはExecutorに最終的なテキスト応答を伝えるためのものです。
        実際には何もしませんが、計画の一部として重要です。
        """
        return text

    async def generate_image(self, prompt: str) -> str:
        """
        VRAMを管理しながら画像を生成する。
        """
        if not self._agent:
            logging.error("VRAM管理エラー: AgentがToolManagerにセットされていません。")
            return "エラー: VRAM管理の初期化に失敗しました。"

        try:
            # Step 1: LLMがロードされていれば、アンロードする
            if self.llm_is_loaded:
                logging.info("画像生成のため、LLMをVRAMからアンロードします...")
                await self._agent.unload_agents()
                self.llm_is_loaded = False
            else:
                logging.info("LLMは既にアンロードされています。画像生成を続行します。")

            # Step 2: 画像生成を実行 (重い処理なので別スレッドで)
            loop = asyncio.get_running_loop()
            file_path = await loop.run_in_executor(None, generate_image, prompt)
            
            return f"画像を生成しました。パス: {file_path}"

        except Exception as e:
            logging.error(f"画像生成中のエラー: {e}", exc_info=True)
            return f"エラー: 画像の生成に失敗しました - {e}"
        
        finally:
            # Step 3: LLMを再ロードする準備ができたことを親エージェントに通知
            # 実際の再ロードは、次の会話リクエストが来た時にCappuccinoAgentが行う
            logging.info("LLMの再ロード準備ができました。次のリクエストでロードされます。")