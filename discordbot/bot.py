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

# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
# ★★★ これが最重要の修正点です ★★★
#
# poker.pyが同じフォルダにいるので、.(ドット)を付けて
# 「このフォルダにあるpoker.py」と明示します。
from .poker import PokerMatch, PokerView
#
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★


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
# api_baseがNoneの場合はデフォルト値を使用
api_base = OPENAI_API_BASE if OPENAI_API_BASE else "https://api.openai.com/v1"
cappuccino_agent = CappuccinoAgent(api_key=OPENAI_API_KEY, api_base=api_base)
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

# GPU監視機能のインポート
try:
    from docker_tools import nvidia_smi_status, nvidia_smi_memory_usage, nvidia_smi_processes
    GPU_MONITORING_AVAILABLE = True
except ImportError:
    GPU_MONITORING_AVAILABLE = False
    logger.warning("GPU monitoring tools not available")
# ───────────────── ヘルパー関数 ─────────────────
async def _gather_reply_chain(msg: discord.Message, limit: int | None = None) -> list[discord.Message]:
    chain: list[discord.Message] = []
    current = msg
    while getattr(current, "reference", None):
        if limit is not None and len(chain) >= limit: break
        try: 
            # message_idがNoneでないことを確認
            if current.reference and current.reference.message_id:
                current = await msg.channel.fetch_message(current.reference.message_id)
            else:
                break
        except Exception: break
        chain.append(current)
    chain.reverse()
    return chain
def _strip_bot_mention(text: str) -> str:
    if bot.user is None: return text.strip()
    return re.sub(fr"<@!?{bot.user.id}>", "", text).strip()
# ───────────────── AI応答処理 ─────────────────
async def handle_agent_request(message: discord.Message, user_text: str):
    if not user_text.strip():
        await message.reply("質問を書いてね！")
        return
    reply = await message.reply("思考中...")
    try:
        history = await _gather_reply_chain(message, limit=5)
        full_prompt = "\n".join([f"{m.author.display_name}: {m.content}" for m in history if m.content])
        full_prompt += f"\n{message.author.display_name}: {user_text}"

        final_answer = await cappuccino_agent.run(full_prompt)
        logger.info(f"エージェントからの最終回答: {final_answer}")

        # パスが含まれるかどうか厳密に判定
        image_path = None
        response_text = str(final_answer)

        import re
        # Windowsパスの正規表現（簡易）
        m = re.search(r"([A-Za-z]:\\(?:[^\\/:*?\"<>|\r\n]+\\)*[^\\/:*?\"<>|\r\n]+\.png)", final_answer)
        if m:
            path_str = m.group(1)
            if os.path.exists(path_str):
                image_path = path_str
                response_text = "画像を生成しました！"
            else:
                response_text = f"エラー: ファイルが存在しません。パス: {path_str}"

        if image_path:
            await reply.edit(content=response_text, attachments=[discord.File(image_path)])
            try:
                os.remove(image_path)
            except Exception as e:
                logger.error(f"一時ファイル削除失敗: {e}")
        else:
            if not response_text.strip():
                response_text = "(空の応答)"
            for i in range(0, len(response_text), 1950):
                chunk = response_text[i:i+1950]
                if i == 0:
                    await reply.edit(content=chunk)
                else:
                    await message.channel.send(chunk)

    except Exception as exc:
        logger.error(f"handle_agent_requestでエラー: {exc}", exc_info=True)
        await reply.edit(content=f"申し訳ありません、エラーが発生しました: {exc}")

# ───────────────── Discordイベントハンドラ ─────────────────
@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user: return
    # 参照メッセージの安全なチェック
    is_reply_to_bot = False
    if message.reference and message.reference.resolved:
        try:
            # DeletedReferencedMessageの場合はauthorが存在しない可能性がある
            resolved = message.reference.resolved
            # 型チェックを回避するためにgetattrを使用
            author = getattr(resolved, 'author', None)
            if (author is not None and 
                bot.user is not None and 
                author == bot.user):
                is_reply_to_bot = True
        except (AttributeError, TypeError):
            pass
    
    if bot.user in message.mentions or is_reply_to_bot:
        await handle_agent_request(message, _strip_bot_mention(message.content))
    if message.content.startswith("r?"): # コマンドは r? のまま
        await handle_agent_request(message, message.content[2:].strip())
@bot.event
async def on_ready():
    await bot.change_presence(status=Status.online, activity=Activity(type=ActivityType.playing, name="r? | @メンション | /gpu"))
    if bot.user:
        logger.info(f"LOGIN: {bot.user} (ID: {bot.user.id})")
    else:
        logger.info("LOGIN: Bot user not available")
    
    # スラッシュコマンドを同期
    try:
        # グローバルコマンドとして同期
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} global command(s): {[cmd.name for cmd in synced]}")
        
        # 開発用：特定のギルドにコマンドを同期
        # 注意: 本番環境ではグローバル同期のみを使用
        for guild in bot.guilds:
            try:
                synced_guild = await bot.tree.sync(guild=guild)
                logger.info(f"Synced {len(synced_guild)} command(s) to guild {guild.name}: {[cmd.name for cmd in synced_guild]}")
            except Exception as e:
                logger.error(f"Failed to sync commands to guild {guild.name}: {e}")
                
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")
        
    # コマンド一覧をログに出力
    logger.info(f"Available commands: {[cmd.name for cmd in bot.tree.get_commands()]}")


# ───────────────── スラッシュコマンド ─────────────────
@bot.tree.command(name="gpu", description="GPU使用率を確認します")
@app_commands.describe()
async def gpu_status(interaction: discord.Interaction):
    """GPU使用率を確認するスラッシュコマンド"""
    if not GPU_MONITORING_AVAILABLE:
        await interaction.response.send_message("❌ GPU監視機能が利用できません。", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    try:
        # GPU状態を取得
        status = nvidia_smi_status()
        
        if "error" in status:
            await interaction.followup.send(f"❌ GPU状態の取得に失敗しました: {status['error']}")
            return
        
        # メモリ使用量を取得
        memory = nvidia_smi_memory_usage()
        
        # プロセス情報を取得
        processes = nvidia_smi_processes()
        
        # レスポンスを作成
        embed = discord.Embed(
            title="🖥️ GPU Status",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        if "gpu_info" in status and status["gpu_info"]:
            for gpu in status["gpu_info"]:
                memory_usage = "Unknown"
                if "memory_usage" in memory and memory["memory_usage"]:
                    for mem in memory["memory_usage"]:
                        if mem["gpu_index"] == gpu["index"]:
                            memory_usage = f"{mem['used_mb']}MB / {mem['total_mb']}MB ({mem['usage_percent']}%)"
                            break
                
                embed.add_field(
                    name=f"🎮 GPU {gpu['index']}: {gpu['name']}",
                    value=f"💾 Memory: {memory_usage}\n"
                          f"⚡ Utilization: {gpu['utilization_percent']}%\n"
                          f"🌡️ Temperature: {gpu['temperature_c']}°C",
                    inline=False
                )
        else:
            embed.add_field(name="Info", value="No GPU information available", inline=False)
        
        # プロセス情報を追加
        if "processes" in processes and processes["processes"]:
            process_lines = processes["processes"].strip().split('\n')
            if len(process_lines) > 2:  # ヘッダー行を除く
                process_info = "\n".join(process_lines[2:5])  # 最初の3つのプロセス
                embed.add_field(name="🔄 Active Processes", value=f"```\n{process_info}\n```", inline=False)
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"GPU status command error: {e}")
        await interaction.followup.send(f"❌ GPU状態の取得中にエラーが発生しました: {e}")


@bot.tree.command(name="gpumemory", description="GPUメモリ使用量の詳細を表示します")
@app_commands.describe()
async def gpu_memory(interaction: discord.Interaction):
    """GPUメモリ使用量の詳細を表示するスラッシュコマンド"""
    if not GPU_MONITORING_AVAILABLE:
        await interaction.response.send_message("❌ GPU監視機能が利用できません。", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    try:
        memory = nvidia_smi_memory_usage()
        
        if "error" in memory:
            await interaction.followup.send(f"❌ メモリ使用量の取得に失敗しました: {memory['error']}")
            return
        
        embed = discord.Embed(
            title="💾 GPU Memory Usage",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        
        if "memory_usage" in memory and memory["memory_usage"]:
            for mem in memory["memory_usage"]:
                # メモリ使用率に基づいて色を決定
                usage_percent = mem["usage_percent"]
                if usage_percent > 80:
                    color = discord.Color.red()
                elif usage_percent > 60:
                    color = discord.Color.orange()
                else:
                    color = discord.Color.green()
                
                embed.add_field(
                    name=f"🎮 GPU {mem['gpu_index']}: {mem['name']}",
                    value=f"💾 Used: {mem['used_mb']}MB\n"
                          f"📊 Free: {mem['free_mb']}MB\n"
                          f"📈 Total: {mem['total_mb']}MB\n"
                          f"📊 Usage: {usage_percent}%",
                    inline=True
                )
        else:
            embed.add_field(name="Info", value="No memory information available", inline=False)
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"GPU memory command error: {e}")
        await interaction.followup.send(f"❌ メモリ使用量の取得中にエラーが発生しました: {e}")


@bot.tree.command(name="gpuprocesses", description="GPUを使用しているプロセスを表示します")
@app_commands.describe()
async def gpu_processes(interaction: discord.Interaction):
    """GPUを使用しているプロセスを表示するスラッシュコマンド"""
    if not GPU_MONITORING_AVAILABLE:
        await interaction.response.send_message("❌ GPU監視機能が利用できません。", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    try:
        processes = nvidia_smi_processes()
        
        if "error" in processes:
            await interaction.followup.send(f"❌ プロセス情報の取得に失敗しました: {processes['error']}")
            return
        
        embed = discord.Embed(
            title="🔄 GPU Processes",
            color=discord.Color.purple(),
            timestamp=discord.utils.utcnow()
        )
        
        if "processes" in processes and processes["processes"]:
            process_lines = processes["processes"].strip().split('\n')
            if len(process_lines) > 2:  # ヘッダー行を除く
                # プロセス情報を整形
                process_info = "\n".join(process_lines[2:10])  # 最初の8つのプロセス
                embed.add_field(
                    name="Active Processes", 
                    value=f"```\n{process_info}\n```", 
                    inline=False
                )
            else:
                embed.add_field(name="Info", value="No processes using GPU", inline=False)
        else:
            embed.add_field(name="Info", value="No process information available", inline=False)
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"GPU processes command error: {e}")
        await interaction.followup.send(f"❌ プロセス情報の取得中にエラーが発生しました: {e}")

# ───────────────── 起動用関数 ─────────────────
async def start_bot():
    """ボットを起動するための非同期関数"""
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if not TOKEN:
        logger.error("DISCORD_BOT_TOKEN is not set.")
        return
    await bot.start(TOKEN)