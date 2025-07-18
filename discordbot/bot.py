# discordbot/bot.py (物理的にパス問題を解決する最終確定版)

import os
import re
import time
import random
import discord
from discord import Status, Activity, ActivityType
import tempfile
import logging
import datetime
import asyncio
import base64
import shutil
from discord import app_commands
from discord.ext import commands
# 親のパスはrun_server_bot.pyが設定するので、直接インポートできる
from cappuccino_agent import CappuccinoAgent
import json
import feedparser
import aiohttp
from openai import AsyncOpenAI
from bs4 import BeautifulSoup
from typing import Iterable, Union, Optional, Tuple

from config import settings
from urllib.parse import urlparse, parse_qs, urlunparse
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Any

# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
# ★★★ これが最重要の修正点です ★★★
#
# poker.pyが同じフォルダに移動したので、.(ドット)を付けて
# 「このフォルダにあるpoker.py」と明示します。
from .poker import PokerMatch, PokerView
#
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★


# (これ以降のコードは、前回提案した最終版と全く同じでOKです)
# ───────────────── TOKEN / KEY ─────────────────
OPENAI_API_KEY = settings.openai_api_key
OPENAI_API_BASE = settings.openai_api_base
# ───────────────── 設定ファイルの読み込み ─────────────────
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
NEWS_CONF_FILE = os.path.join(ROOT_DIR, "news_channel.json")
EEW_CONF_FILE = os.path.join(ROOT_DIR, "eew_channel.json")
EEW_LAST_FILE = os.path.join(ROOT_DIR, "last_eew.txt")
WEATHER_CONF_FILE = os.path.join(ROOT_DIR, "weather_channel.json")
def _load_news_channel() -> int:
    try:
        with open(NEWS_CONF_FILE, "r", encoding="utf-8") as f: return int(json.load(f).get("channel_id", 0))
    except Exception: return 0
def _save_news_channel(ch_id: int) -> None:
    try:
        with open(NEWS_CONF_FILE + ".tmp", "w", encoding="utf-8") as f: json.dump({"channel_id": ch_id}, f, ensure_ascii=False, indent=2)
        os.replace(NEWS_CONF_FILE + ".tmp", NEWS_CONF_FILE)
    except Exception as e: logger.error("failed to save news channel: %s", e)
def _load_eew_channel() -> int:
    try:
        with open(EEW_CONF_FILE, "r", encoding="utf-8") as f: return int(json.load(f).get("channel_id", 0))
    except Exception: return 0
def _save_eew_channel(ch_id: int) -> None:
    try:
        with open(EEW_CONF_FILE + ".tmp", "w", encoding="utf-8") as f: json.dump({"channel_id": ch_id}, f, ensure_ascii=False, indent=2)
        os.replace(EEW_CONF_FILE + ".tmp", EEW_CONF_FILE)
    except Exception as e: logger.error("failed to save eew channel: %s", e)
def _load_weather_channel() -> int:
    try:
        with open(WEATHER_CONF_FILE, "r", encoding="utf-8") as f: return int(json.load(f).get("channel_id", 0))
    except Exception: return 0
def _save_weather_channel(ch_id: int) -> None:
    try:
        with open(WEATHER_CONF_FILE + ".tmp", "w", encoding="utf-8") as f: json.dump({"channel_id": ch_id}, f, ensure_ascii=False, indent=2)
        os.replace(WEATHER_CONF_FILE + ".tmp", WEATHER_CONF_FILE)
    except Exception as e: logger.error("failed to save weather channel: %s", e)
def _load_last_eew() -> str:
    try:
        with open(EEW_LAST_FILE, "r", encoding="utf-8") as f: return f.read().strip()
    except Exception: return ""
def _save_last_eew(eid: str) -> None:
    try:
        with open(EEW_LAST_FILE, "w", encoding="utf-8") as f: f.write(eid)
    except Exception as e: logger.error("failed to save eew id: %s", e)
NEWS_CHANNEL_ID = _load_news_channel()
EEW_CHANNEL_ID = _load_eew_channel()
LAST_EEW_ID = _load_last_eew()
WEATHER_CHANNEL_ID = _load_weather_channel()
# ───────────────── エージェントの初期化 ─────────────────
cappuccino_agent = CappuccinoAgent(api_key=OPENAI_API_KEY, api_base=OPENAI_API_BASE)
# ───────────────── ロギング設定 ─────────────────
log_file_path = os.path.join(ROOT_DIR, "..", "bot.log")
handler = RotatingFileHandler(log_file_path, maxBytes=1_000_000, backupCount=5, encoding='utf-8')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[handler])
logging.getLogger('discord').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
# ───────────────── Discordクライアント設定 ─────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="y!", intents=intents)
# ───────────────── ヘルパー関数 ─────────────────
async def _gather_reply_chain(msg: discord.Message, limit: int | None = None) -> list[discord.Message]:
    chain: list[discord.Message] = []
    current = msg
    while getattr(current, "reference", None):
        if limit is not None and len(chain) >= limit: break
        try: current = await msg.channel.fetch_message(current.reference.message_id)
        except Exception: break
        chain.append(current)
    chain.reverse()
    return chain
def _strip_bot_mention(text: str) -> str:
    if bot.user is None: return text.strip()
    return re.sub(fr"<@!?{bot.user.id}>", "", text).strip()
# ───────────────── AI応答処理 ─────────────────
async def handle_agent_request(message: discord.Message, user_text: str):
    if not user_text.strip(): await message.reply("質問を書いてね！"); return
    reply = await message.reply("思考中...")
    try:
        history = await _gather_reply_chain(message, limit=5)
        full_prompt = "\n".join([f"{m.author.display_name}: {m.content}" for m in history if m.content])
        full_prompt += f"\n{message.author.display_name}: {user_text}"
        final_answer = await cappuccino_agent.run(full_prompt)
        logger.info(f"エージェントからの最終回答: {final_answer}")
        image_path = None
        if isinstance(final_answer, str) and "画像を生成しました。パス: " in final_answer:
            path_str = final_answer.replace("画像を生成しました。パス: ", "").strip()
            if os.path.exists(path_str): image_path = path_str; response_text = "画像を生成しました！"
            else: response_text = f"エラー: 生成された画像ファイルが見つかりませんでした。パス: {path_str}"
        else: response_text = str(final_answer)
        if image_path:
            await reply.edit(content=response_text, attachments=[discord.File(image_path)])
            try: os.remove(image_path)
            except OSError as e: logger.error(f"一時ファイルの削除に失敗: {e}")
        else:
            if not response_text.strip(): response_text = "(空の応答)"
            for i in range(0, len(response_text), 1950):
                chunk = response_text[i:i+1950]
                await (reply.edit(content=chunk) if i == 0 else message.channel.send(chunk))
    except Exception as exc: logger.error(f"handle_agent_requestでエラー: {exc}", exc_info=True); await reply.edit(content=f"申し訳ありません、エラーが発生しました: {exc}")
# ───────────────── Discordイベントハンドラ ─────────────────
@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user: return
    if bot.user in message.mentions or (message.reference and message.reference.resolved and message.reference.resolved.author == bot.user):
        await handle_agent_request(message, _strip_bot_mention(message.content))
    if message.content.startswith("y?"):
        await handle_agent_request(message, message.content[2:].strip())
@bot.event
async def on_ready():
    await bot.change_presence(status=Status.online, activity=Activity(type=ActivityType.playing, name="y!help | @メンションで会話"))
    logger.info(f"LOGIN: {bot.user} (ID: {bot.user.id})")

# ───────────────── 起動用関数 ─────────────────
async def start_bot():
    """ボットを起動するための非同期関数"""
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if not TOKEN:
        logger.error("DISCORD_BOT_TOKEN is not set.")
        return
    await bot.start(TOKEN)