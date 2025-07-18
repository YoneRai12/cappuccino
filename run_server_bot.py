# run_bot.py (Webサーバーを完全に削除した、ボット起動専用の最終版)

import asyncio
import os
import sys

# プロジェクトルートをパスに追加 (これは正しい)
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from discordbot.bot import start_bot

async def main():
    """Discordボットのみを起動する"""
    print("Discordボットを起動します...")
    await start_bot()

if __name__ == "__main__":
    # Windowsでasyncioのイベントループポリシーを設定
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
