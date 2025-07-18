# tool_manager.py （完成版・コピペ用）
import asyncio
import json
from typing import Any, Dict, List, Optional
import aiosqlite
from datetime import datetime

# ★★★★★ ここで新しい道具をインポート ★★★★★
from image_generator import generate_image
# ★★★★★★★★★★★★★★★★★★★★★★★★

class ToolManager:
    def __init__(self, db_path: str = "agent_state.db"):
        self.db_path = db_path
        self.conn: Optional[aiosqlite.Connection] = None

    async def _get_db_connection(self) -> aiosqlite.Connection:
        if self.conn is None:
            self.conn = await aiosqlite.connect(self.db_path)
        return self.conn

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()
            self.conn = None

    # ★★★★★ ここに画像生成ツールを追加 ★★★★★
    async def generate_image(self, prompt: str) -> str:
        """
        ユーザーの指示に基づいて画像を生成します。非同期で実行されます。
        Generates an image based on the user's prompt. Runs asynchronously.
        """
        loop = asyncio.get_running_loop()
        # 画像生成はVRAMを大量に使う重い処理なので、別スレッドで実行する
        file_path = await loop.run_in_executor(None, generate_image, prompt)
        return f"画像を生成しました。パス: {file_path}"
    # ★★★★★★★★★★★★★★★★★★★★★★★★★★

    async def get_tools_schema(self) -> List[Dict[str, Any]]:
        """Returns the JSON schema for the available tools."""
        return [
            # ★★★★★ ここに画像生成ツールの定義を追加 ★★★★★
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
                                "description": "生成したい画像の内容を詳細に記述したプロンプト。例: 'An astronaut riding a horse on mars, photorealistic'",
                            },
                        },
                        "required": ["prompt"],
                    },
                },
            },
            # ★★★★★★★★★★★★★★★★★★★★★★★★★★★
            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "description": "ウェブを検索して最新の情報や特定のトピックに関する情報を取得します。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "検索したいキーワードや質問。",
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
        ]

    async def search_web(self, query: str) -> str:
        # この機能はまだ実装されていません
        return f"ウェブ検索は現在準備中です。'{query}'を検索することはできませんでした。"

    async def get_cached_result(self, key: str) -> Optional[str]:
        conn = await self._get_db_connection()
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT, timestamp REAL)"
        )
        cursor = await conn.execute("SELECT value FROM cache WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row[0] if row else None

    async def set_cached_result(self, key: str, value: str) -> None:
        conn = await self._get_db_connection()
        await conn.execute(
            "INSERT OR REPLACE INTO cache (key, value, timestamp) VALUES (?, ?, ?)",
            (key, value, datetime.now().timestamp()),
        )
        await conn.commit()

        # tool_manager.py (VRAM管理機能を追加した最終版)
import logging
import torch
from image_generator import generate_image

class ToolManager:
    def __init__(self, db_path=":memory:", agent=None):
        self.db_path = db_path
        self._agent = agent

    def set_agent(self, agent):
        """VRAM管理のためにエージェント本体への参照を保持する"""
        self._agent = agent

    async def get_tools_schema(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "generate_image",
                    "description": "テキストプロンプトに基づいて画像を生成します。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompt": {"type": "string", "description": "生成したい画像の説明。詳細であるほど良い。"},
                        },
                        "required": ["prompt"],
                    },
                },
            }
        ]

    async def generate_image(self, prompt: str):
        """VRAMを管理しながら画像を生成する"""
        if not self._agent:
            logging.error("VRAM管理エラー: AgentがToolManagerにセットされていません。")
            return "エラー: VRAM管理の初期化に失敗しました。"

        try:
            # 1. LLMをアンロード
            logging.info("画像生成のため、LLMをVRAMからアンロードします...")
            await self._agent.unload_llm()

            # 2. 画像を生成
            image_path = await generate_image(prompt)

            return f"画像を生成しました。パス: {image_path}"
        
        except Exception as e:
            logging.error(f"画像生成中のエラー: {e}", exc_info=True)
            return f"エラー: 画像の生成に失敗しました - {e}"
        
        finally:
            # 3. LLMを再ロード
            logging.info("LLMをVRAMに再ロードします...")
            await self._agent.load_llm()