#!/usr/bin/env python3
"""
Discord Bot実行スクリプト
"""

import os
import sys

# 現在のディレクトリをPythonパスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 環境変数の設定
os.environ['PYTHONPATH'] = current_dir + os.pathsep + os.environ.get('PYTHONPATH', '')

# Discord Botを起動
if __name__ == "__main__":
    from discordbot.bot import start_bot
    import asyncio
    
    print("Discord Botを起動中...")
    asyncio.run(start_bot()) 