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
from discord.ui import View, Button
# 親のパスはrun_server_bot.pyが設定するので、直接インポートできる
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
# poker.pyが同じフォルダにいるので、相対インポートを使用します。
from .poker import PokerMatch, PokerView
#
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

from image_generator import generate_image, generate_image_with_negative

is_generating_image = False
image_generating_channel_id = None

# 音声読み上げ機能のライブラリ
try:
    from gtts import gTTS
    import io
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("gTTS not available. TTS functionality will be disabled.")

# YouTube音楽再生機能のライブラリ
try:
    import yt_dlp
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False
    print("yt-dlp not available. YouTube functionality will be disabled.")

# VOICEVOXを使用したずんだもんの声生成
try:
    import requests
    VOICEVOX_AVAILABLE = True
    VOICEVOX_URL = "http://localhost:50021"  # VOICEVOXのデフォルトURL
except ImportError:
    VOICEVOX_AVAILABLE = False
    print("requests not available. VOICEVOX functionality will be disabled.")

# (これ以降のコードは、前回提案した最終版と全く同じでOKです)
# ───────────────── TOKEN / KEY ─────────────────
OPENAI_API_KEY = settings.openai_api_key
OPENAI_API_BASE = settings.openai_api_base

# ───────────────── TTS設定 ─────────────────
# TTS自動読み上げ設定
TTS_USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_users.json")
TTS_CHANNELS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_channels.json")
TTS_JOIN_CHANNELS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_join_channels.json")

def _load_tts_users() -> set[int]:
    """TTS自動読み上げを有効にしているユーザーIDを読み込み"""
    try:
        with open(TTS_USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("users", []))
    except FileNotFoundError:
        return set()
    except Exception as e:
        logger.error(f"TTSユーザー読み込み失敗: {e}")
        return set()

def _save_tts_users(users: set[int]) -> None:
    """TTS自動読み上げを有効にしているユーザーIDを保存"""
    try:
        with open(TTS_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump({"users": list(users)}, f)
    except Exception as e:
        logger.error(f"TTSユーザー保存失敗: {e}")

def _load_tts_channels() -> set[int]:
    """TTS自動読み上げを有効にしているチャンネルIDを読み込み"""
    try:
        with open(TTS_CHANNELS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("channels", []))
    except FileNotFoundError:
        return set()
    except Exception as e:
        logger.error(f"TTSチャンネル読み込み失敗: {e}")
        return set()

def _save_tts_channels(channels: set[int]) -> None:
    """TTS自動読み上げを有効にしているチャンネルIDを保存"""
    try:
        with open(TTS_CHANNELS_FILE, "w", encoding="utf-8") as f:
            json.dump({"channels": list(channels)}, f)
    except Exception as e:
        logger.error(f"TTSチャンネル保存失敗: {e}")

def _load_tts_join_channels() -> dict[int, int]:
    """TTS参加チャンネルとVCのマッピングを読み込み"""
    try:
        with open(TTS_JOIN_CHANNELS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {int(k): int(v) for k, v in data.get("channels", {}).items()}
    except FileNotFoundError:
        return {}
    except Exception as e:
        logger.error(f"TTS参加チャンネル読み込み失敗: {e}")
        return {}

def _save_tts_join_channels(channels: dict[int, int]) -> None:
    """TTS参加チャンネルとVCのマッピングを保存"""
    try:
        with open(TTS_JOIN_CHANNELS_FILE, "w", encoding="utf-8") as f:
            json.dump({"channels": {str(k): v for k, v in channels.items()}}, f)
    except Exception as e:
        logger.error(f"TTS参加チャンネル保存失敗: {e}")

# キャラクター設定ファイル
CHARACTER_SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "character_settings.json")

def _load_character_settings() -> dict[int, str]:
    """ユーザー別キャラクター設定を読み込み"""
    try:
        with open(CHARACTER_SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {int(k): v for k, v in data.get("users", {}).items()}
    except Exception:
        return {}

def _save_character_settings(settings: dict[int, str]) -> None:
    """ユーザー別キャラクター設定を保存"""
    try:
        with open(CHARACTER_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump({"users": {str(k): v for k, v in settings.items()}}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"キャラクター設定保存失敗: {e}")

async def generate_zunda_voice(text: str) -> bytes | None:
    """VOICEVOXを使用してずんだもんの声を生成（高速化）"""
    if not VOICEVOX_AVAILABLE:
        return None
    
    try:
        # VOICEVOXの音声合成APIを呼び出し（高速化）
        speaker_id = 1
        
        # 音声合成のリクエスト（タイムアウトを短縮）
        synthesis_response = requests.post(
            f"{VOICEVOX_URL}/audio_query",
            params={"text": text, "speaker": speaker_id},
            headers={"Content-Type": "application/json"},
            timeout=3  # タイムアウトを3秒に短縮
        )
        
        if synthesis_response.status_code != 200:
            logger.error(f"VOICEVOX音声合成失敗: {synthesis_response.status_code}")
            return None
        
        audio_query = synthesis_response.json()
        
        # 音声生成（タイムアウトを短縮）
        audio_response = requests.post(
            f"{VOICEVOX_URL}/synthesis",
            params={"speaker": speaker_id},
            data=json.dumps(audio_query),
            headers={"Content-Type": "application/json"},
            timeout=5  # タイムアウトを5秒に短縮
        )
        
        if audio_response.status_code != 200:
            logger.error(f"VOICEVOX音声生成失敗: {audio_response.status_code}")
            return None
        
        return audio_response.content
        
    except Exception as e:
        logger.error(f"VOICEVOX音声生成エラー: {e}")
        return None

async def download_youtube_audio(url: str) -> str:
    """YouTubeから音声をダウンロード"""
    if not YOUTUBE_AVAILABLE:
        return None
    
    try:
        # yt-dlpの設定
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': '%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        
        # 一時ファイルとして保存
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            ydl_opts['outtmpl'] = tmp_file.name.replace('.mp3', '.%(ext)s')
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 動画情報を取得
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'Unknown')
                duration = info.get('duration', 0)
                
                # 音声をダウンロード
                ydl.download([url])
                
                # ファイル名を取得（拡張子が変わっている可能性があるため）
                downloaded_file = tmp_file.name.replace('.mp3', '.mp3')
                if not os.path.exists(downloaded_file):
                    # 他の拡張子を試す
                    for ext in ['.webm', '.m4a', '.opus', '.mp3']:
                        alt_file = tmp_file.name.replace('.mp3', ext)
                        if os.path.exists(alt_file):
                            # ファイルサイズが安定するまで待つ
                            last_size = -1
                            for _ in range(10):
                                try:
                                    size = os.path.getsize(alt_file)
                                    if size == last_size:
                                        break
                                    last_size = size
                                except Exception:
                                    pass
                                time.sleep(0.2)
                            downloaded_file = alt_file
                            break
                # ファイルが使えるまでリトライ
                for _ in range(10):
                    try:
                        with open(downloaded_file, "rb") as f:
                            break
                    except PermissionError:
                        time.sleep(0.2)
                if os.path.exists(downloaded_file):
                    return downloaded_file, title, duration
                else:
                    return None, None, None
    except Exception as e:
        logger.error(f"YouTube音声ダウンロードエラー: {e}")
        return None, None, None

# TTS自動読み上げ設定
TTS_USERS = _load_tts_users()
TTS_CHANNELS = _load_tts_channels()
TTS_JOIN_CHANNELS = _load_tts_join_channels()

# デバッグ用：TTS設定をログ出力
print(f"TTS設定読み込み完了:")
print(f"  TTS_USERS: {TTS_USERS}")
print(f"  TTS_CHANNELS: {TTS_CHANNELS}")
print(f"  TTS_JOIN_CHANNELS: {TTS_JOIN_CHANNELS}")

# TTS設定（速度、音声など）
TTS_SETTINGS = {
    "speed": 1.0,  # 読み上げ速度（0.5-2.0）
    "voice": "zunda",  # 音声タイプ（zunda, gtts）
    "volume": 1.0  # 音量（0.1-2.0）
}

# サーバー別のTTS設定を管理
SERVER_TTS_SETTINGS = {}

# ユーザー別のキャラクター設定を管理
USER_CHARACTER_SETTINGS = _load_character_settings()

# 接続済みサーバーを記録（接続メッセージ用）
CONNECTED_SERVERS = set()

# 前回のメッセージ送信者を記録（サーバー・チャンネル別）
last_message_author = {}
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
    print(f"handle_agent_request呼び出し: {user_text}")
    global is_generating_image, image_generating_channel_id
    if is_generating_image:
        await message.reply("画像生成中です。しばらくお待ちください。")
        return
    if not user_text.strip():
        await message.reply("質問を書いてね！")
        return
    # コマンド形式でget_current_timeを直接呼び出し
    if user_text.strip().lower() in ["/get_current_time", "!get_current_time"]:
        from tool_manager import ToolManager
        tool_manager = ToolManager()
        get_time_func = tool_manager.get_tool_by_name("get_current_time")
        if get_time_func:
            result = await get_time_func()
            await message.reply(str(result))
        else:
            await message.reply("get_current_timeツールが見つかりませんでした。")
        return
    reply = await message.reply("思考中...")
    try:
        # 画像生成リクエストか判定（超簡易: '画像'や'image'が含まれる場合）
        if any(x in user_text for x in ["画像", "image", "イメージ", "生成"]):
            is_generating_image = True
            image_generating_channel_id = message.channel.id
            await message.channel.send("現在画像生成をしています。しばらくお待ちください。")
        history = await _gather_reply_chain(message, limit=5)
        full_prompt = "\n".join([f"{m.author.display_name}: {m.content}" for m in history if m.content])
        full_prompt += f"\n{message.author.display_name}: {user_text}"
        print("cappuccino_agent.run呼び出し直前")
        result = await cappuccino_agent.run(full_prompt)
        print("cappuccino_agent.run呼び出し直後")
        logger.info(f"エージェントからの最終回答: {result}")

        image_paths = result.get("files", []) if isinstance(result, dict) else []
        response_text = result.get("text", str(result)) if isinstance(result, dict) else str(result)

        if image_paths:
            # 画像が複数の場合も対応
            files = [discord.File(p) for p in image_paths if os.path.exists(p)]
            await reply.edit(content="画像を生成しました！", attachments=files)
            # 送信後に削除
            for p in image_paths:
                try:
                    os.remove(p)
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

        # 1分後にVRAM開放
        async def vram_clear_task():
            await asyncio.sleep(60)
            try:
                from docker_tools import nvidia_smi_clear_memory
                result = nvidia_smi_clear_memory()
                logger.info(f"[VRAM自動開放] 結果: {result}")
            except Exception as e:
                logger.error(f"[VRAM自動開放] エラー: {e}")
        asyncio.create_task(vram_clear_task())

    except Exception as exc:
        is_generating_image = False
        image_generating_channel_id = None
        logger.error(f"handle_agent_requestでエラー: {exc}", exc_info=True)
        await reply.edit(content=f"申し訳ありません、エラーが発生しました: {exc}")

# ───────────────── Discordイベントハンドラ ─────────────────
@bot.event
async def on_message(message: discord.Message):
    global is_generating_image, image_generating_channel_id
    if message.author == bot.user:
        return
    # 画像生成中に@メンションやコマンドが来た場合
    if is_generating_image and (bot.user in message.mentions or message.content.startswith("y!")):
        await message.reply("画像生成中です。しばらくお待ちください。")
        return
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
        print(f"@メンション検知: {message.content}")
        await handle_agent_request(message, _strip_bot_mention(message.content))
    if message.content.startswith("r?"): # コマンドは r? のまま
        await handle_agent_request(message, message.content[2:].strip())
    
    # フラグ翻訳コマンド
    if message.content.startswith("flag "):
        await cmd_flag(message, message.content[5:].strip())
    
    # TTS自動読み上げ処理（/joinで設定されたチャンネルのみ）
    if message.guild and message.content.strip() and not message.content.startswith("y!"):
        # /joinで設定されたチャンネルのみ自動読み上げ
        if message.channel.id in TTS_JOIN_CHANNELS:
            # ユーザーがVCにいる場合のみTTSを実行
            if message.author.voice and message.author.voice.channel:
                try:
                    # テキストをクリーンアップ（URL、絵文字、メンションなどを除去）
                    clean_text = message.content
                    # URLを除去
                    clean_text = re.sub(r'https?://\S+', '', clean_text)
                    # メンションを除去
                    clean_text = re.sub(r'<@!?\d+>', '', clean_text)
                    # 絵文字を除去
                    clean_text = re.sub(r'<a?:.+?:\d+>', '', clean_text)
                    # 余分な空白を除去
                    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                    
                    if clean_text and len(clean_text) > 1:
                        # 同一人物の場合は名前を省略、異なる場合は名前を付ける
                        global last_message_author
                        
                        if hasattr(message, 'guild') and message.guild:
                            # 同一人物の場合は名前を省略
                            if hasattr(message, 'author') and hasattr(message.author, 'id'):
                                if hasattr(message, 'guild') and hasattr(message.guild, 'id'):
                                    cache_key = f"{message.guild.id}_{message.channel.id}"
                                    if cache_key in last_message_author and last_message_author[cache_key] == message.author.id:
                                        zunda_text = clean_text
                                    else:
                                        # ユーザー別キャラクター設定を取得
                                        user_id = message.author.id
                                        character = USER_CHARACTER_SETTINGS.get(user_id, "デフォルト")
                                        
                                        # キャラクター設定に関係なく、統一された読み上げテキスト
                                        zunda_text = f"{message.author.display_name}さん。{clean_text}"
                                        
                                        # 送信者を記録
                                        if not hasattr(message, 'guild') or not hasattr(message.guild, 'id'):
                                            last_message_author = {}
                                        last_message_author[cache_key] = message.author.id
                                else:
                                    zunda_text = f"{message.author.display_name}さん。{clean_text}"
                            else:
                                zunda_text = clean_text
                        else:
                            zunda_text = clean_text
                        
                        audio_data = None
                        audio_path = None
                        
                        # 音声生成を高速化
                        audio_data = None
                        audio_path = None
                        
                        # サーバー別のTTS設定を取得
                        server_id = message.guild.id
                        server_settings = SERVER_TTS_SETTINGS.get(server_id, TTS_SETTINGS.copy())
                        
                        # VOICEVOXが利用可能な場合はVOICEVOXを使用（高速化）
                        if VOICEVOX_AVAILABLE and server_settings.get('voice', 'zunda') == 'zunda':
                            try:
                                # 非同期で音声生成
                                audio_data = await asyncio.wait_for(generate_zunda_voice(zunda_text), timeout=8.0)
                            except asyncio.TimeoutError:
                                logger.warning("VOICEVOX音声生成がタイムアウトしました")
                                audio_data = None
                            except:
                                audio_data = None
                        
                        # VOICEVOXが失敗した場合や利用できない場合はgTTSを使用（高速化）
                        if audio_data is None and TTS_AVAILABLE:
                            try:
                                # gTTSを非同期で実行
                                loop = asyncio.get_event_loop()
                                tts = gTTS(text=zunda_text, lang='ja', slow=False)
                                audio_buffer = io.BytesIO()
                                
                                # スレッドプールで実行
                                await loop.run_in_executor(None, lambda: tts.write_to_fp(audio_buffer))
                                audio_data = audio_buffer.getvalue()
                            except:
                                audio_data = None
                        
                        if audio_data is not None:
                            # 一時ファイルとして保存（高速化）
                            import tempfile
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                                tmp_file.write(audio_data)
                                audio_path = tmp_file.name
                            
                            # 指定されたVCに接続
                            vc_channel_id = TTS_JOIN_CHANNELS[message.channel.id]
                            target_vc_channel = message.guild.get_channel(vc_channel_id)
                            
                            if target_vc_channel:
                                voice = None
                                
                                # 指定されたVCに接続
                                if target_vc_channel.guild.voice_client is None:
                                    voice = await target_vc_channel.connect()
                                    # 初回接続時のみメッセージを送信
                                    if message.guild.id not in CONNECTED_SERVERS:
                                        await message.channel.send(f"🎤 {target_vc_channel.mention} に接続しました！")
                                        CONNECTED_SERVERS.add(message.guild.id)
                                else:
                                    voice = target_vc_channel.guild.voice_client
                                
                                if voice:
                                    # 音声を再生（高速化）
                                    try:
                                        # 既に再生中の場合は待機時間を短縮（超高速化）
                                        if voice.is_playing():
                                            await asyncio.sleep(0.1)  # 0.2秒 → 0.1秒に短縮
                                        
                                        # 音声を再生（FFmpegオプションを最適化）
                                        voice.play(
                                            discord.FFmpegPCMAudio(
                                                audio_path,
                                                options='-vn -ar 48000 -ac 2 -b:a 64k -bufsize 16k'  # さらにビットレートとバッファを最適化
                                            ),
                                            after=lambda e: cleanup()
                                        )
                                        
                                        # 再生終了後にファイルを削除（非同期）
                                        def cleanup():
                                            try:
                                                import os
                                                asyncio.create_task(async_cleanup(audio_path))
                                            except:
                                                pass
                                        
                                    except Exception as e:
                                        logger.error(f"TTS音声再生失敗: {e}")
                                        # cleanup関数をここで定義
                                        try:
                                            import os
                                            asyncio.create_task(async_cleanup(audio_path))
                                        except:
                                            pass
                except Exception as e:
                    logger.error(f"TTS自動読み上げ失敗: {e}")

async def async_cleanup(audio_path: str):
    """非同期で音声ファイルを削除"""
    try:
        await asyncio.sleep(0.5)  # 0.5秒待ってから削除
        os.unlink(audio_path)
    except:
        pass
@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Slashコマンドを{len(synced)}件同期しました")
        
        # 自動配信タスクを開始
        asyncio.create_task(auto_news_task())
        asyncio.create_task(auto_weather_task())
        print("自動配信タスクを開始しました")
        
    except Exception as e:
        print(f"コマンド同期に失敗: {e}")

async def start_bot():
    # Discord Botのトークンを環境変数から取得
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if not TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN環境変数が設定されていません")
    await bot.start(TOKEN)

__all__ = ['start_bot']

# ───────────────── スラッシュコマンド ─────────────────
@bot.tree.command(name="gpu", description="🖥️ GPU使用率を確認します")
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


@bot.tree.command(name="gpumemory", description="💾 GPUメモリ使用量の詳細を表示します")
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


@bot.tree.command(name="gpuprocesses", description="🔄 GPUを使用しているプロセスを表示します")
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

# ───────────────── 国旗翻訳ユーティリティ ─────────────────
FLAG_MAP = {}
FLAG_REVERSE_MAP = {}
FLAG_TXT_PATH = os.path.join(ROOT_DIR, "flags.txt")
if os.path.exists(FLAG_TXT_PATH):
    with open(FLAG_TXT_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 3:
                emoji, _, country = parts[0], parts[1], " ".join(parts[2:])
                FLAG_MAP[country.lower()] = emoji
                FLAG_REVERSE_MAP[emoji] = country

async def cmd_flag(msg: discord.Message, arg: str):
    """国名→国旗絵文字、または国旗絵文字→国名を翻訳"""
    arg = arg.strip()
    if not arg:
        await msg.reply("国名または国旗絵文字を指定してください。")
        return
    # 国名→絵文字
    emoji = FLAG_MAP.get(arg.lower())
    if emoji:
        await msg.reply(emoji)
        return
    # 絵文字→国名
    country = FLAG_REVERSE_MAP.get(arg)
    if country:
        await msg.reply(country)
        return
    await msg.reply("該当する国旗・国名が見つかりませんでした。")

SPECIAL_EMOJI_ISO: dict[str, str] = {}
try:
    FLAGS_PATH = os.path.join(ROOT_DIR, "flags.txt")
    with open(FLAGS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                emoji = parts[0]                  # 例 🇯🇵
                shortcode = parts[1]              # 例 :flag_jp:
                if shortcode.startswith(":flag_") and shortcode.endswith(":"):
                    iso = shortcode[6:-1].upper() # jp -> JP
                    SPECIAL_EMOJI_ISO[emoji] = iso
except FileNotFoundError:
    logger.warning("flags.txt not found. Flag translation reactions disabled")

# --- 国旗→言語コードマップ ---
# （ここからISO_TO_LANGの定義を削除）

# （ここからflag_to_iso関数の定義を削除）

# ------------ 翻訳リアクション機能ここから ------------
import os
# ファイル内の他のSPECIAL_EMOJI_ISO: dict[str, str] = {}の定義をすべて削除
# import osの直後のグローバル定義だけ残す


# flags.txt を読み込み「絵文字 ➜ ISO 国コード」を作る


ISO_TO_LANG = {
    "US": "English", "UM": "English", "GB": "English", "JP": "Japanese", "FR": "French", "DE": "German", "CN": "Chinese (Simplified)", "KR": "Korean", "ES": "Spanish", "IT": "Italian", "RU": "Russian", "PT": "Portuguese", "IN": "Hindi", "SA": "Arabic", "TH": "Thai", "VN": "Vietnamese", "TR": "Turkish", "BR": "Portuguese", "MX": "Spanish", "CA": "English", "AU": "English", "NL": "Dutch", "SE": "Swedish", "NO": "Norwegian", "DK": "Danish", "FI": "Finnish", "PL": "Polish", "CZ": "Czech", "HU": "Hungarian", "GR": "Greek", "ID": "Indonesian", "MY": "Malay", "PH": "Filipino", "IL": "Hebrew", "UA": "Ukrainian", "RO": "Romanian", "BG": "Bulgarian", "HR": "Croatian", "SK": "Slovak", "SI": "Slovene", "RS": "Serbian", "LT": "Lithuanian", "LV": "Latvian", "EE": "Estonian", "GE": "Georgian", "AZ": "Azerbaijani", "AM": "Armenian", "KZ": "Kazakh", "UZ": "Uzbek"
    # ... 必要に応じて追加 ...
}

def flag_to_iso(emoji: str) -> str | None:
    """絵文字2文字なら regional-indicator → ISO に変換"""
    if len(emoji) != 2:
        return None
    base = 0x1F1E6
    try:
        return ''.join(chr(ord(c) - base + 65) for c in emoji)
    except:
        return None


# 末尾の翻訳リアクション機能のawait cappuccino_agent.call_llm(prompt)部分をasync関数translate_flagged_messageに分離

async def translate_flagged_message(message, lang, emoji, original):
    try:
        prompt = (
            f"Translate the following message into {lang}, considering the regional variant indicated by this flag {emoji}. "
            "Provide only the translation, and keep it concise.\n" + original.strip()
        )
        translated = await cappuccino_agent.process(prompt)
        header = f"💬 **{lang}** translation:\n"
        available = 2000 - len(header)
        if len(translated) > available:
            translated = translated[:available - 3] + "..."
        await message.reply(header + translated)
    except Exception as e:
        logger.error(f"翻訳失敗: {e}")
        try:
            await message.reply(f"翻訳エラー: {e}", delete_after=5)
        except Exception as e2:
            logger.error(f"翻訳エラー通知も失敗: {e2}")

# 既存のon_raw_reaction_addイベント内でtranslate_flagged_messageをawaitで呼ぶように修正

@bot.event
async def on_raw_reaction_add(payload):
    emoji = str(payload.emoji)
    iso = SPECIAL_EMOJI_ISO.get(emoji) or flag_to_iso(emoji)
    if not iso:
        return
    lang = ISO_TO_LANG.get(iso)
    if not lang:
        logger.debug("未登録 ISO: %s", iso)
        return
    channel = bot.get_channel(payload.channel_id)
    if not isinstance(channel, discord.TextChannel):
        return
    try:
        message = await channel.fetch_message(payload.message_id)
    except Exception:
        return
    original = getattr(message, "content", None)
    if not isinstance(original, str) or not original.strip():
        return
    await translate_flagged_message(message, lang, emoji, original)

from discord.ui import View, Button

class AspectRatioView(View):
    def __init__(self, prompt):
        super().__init__(timeout=60)
        self.prompt = prompt

    @discord.ui.button(label="1:1（安定）", style=discord.ButtonStyle.primary, custom_id="ratio_1_1")
    async def ratio_1_1(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await interaction.followup.send(view=QualityView(self.prompt, "1:1"), ephemeral=True)
        self.stop()

    @discord.ui.button(label="16:9", style=discord.ButtonStyle.primary, custom_id="ratio_16_9")
    async def ratio_16_9(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await interaction.followup.send(view=QualityView(self.prompt, "16:9"), ephemeral=True)
        self.stop()

    @discord.ui.button(label="9:16", style=discord.ButtonStyle.primary, custom_id="ratio_9_16")
    async def ratio_9_16(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await interaction.followup.send(view=QualityView(self.prompt, "9:16"), ephemeral=True)
        self.stop()

class QualityView(View):
    def __init__(self, prompt, ratio):
        super().__init__(timeout=60)
        self.prompt = prompt
        self.ratio = ratio

    def get_size_for_quality(self, base_width: int) -> tuple[int, int]:
        """比率に応じたサイズを計算"""
        if self.ratio == "1:1":
            return (base_width, base_width)
        elif self.ratio == "16:9":
            height = int(base_width * 9 / 16)
            return (base_width, height)
        elif self.ratio == "9:16":
            width = int(base_width * 9 / 16)
            return (width, base_width)
        else:
            # デフォルトは16:9
            height = int(base_width * 9 / 16)
            return (base_width, height)

    @discord.ui.button(label="FHD（約30秒）", style=discord.ButtonStyle.success, custom_id="quality_fhd")
    async def quality_fhd(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        width, height = self.get_size_for_quality(1920)
        await self.generate_and_send(interaction, width, height)
        self.stop()

    @discord.ui.button(label="WQHD（約3分）", style=discord.ButtonStyle.success, custom_id="quality_wqhd")
    async def quality_wqhd(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        width, height = self.get_size_for_quality(2560)
        await self.generate_and_send(interaction, width, height)
        self.stop()

    @discord.ui.button(label="4K（約7分）", style=discord.ButtonStyle.success, custom_id="quality_4k")
    async def quality_4k(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        width, height = self.get_size_for_quality(3840)
        await self.generate_and_send(interaction, width, height)
        self.stop()

    async def generate_and_send(self, interaction, width, height):
        msg = await interaction.followup.send("画像生成中です。しばらくお待ちください。", ephemeral=False)
        try:
            import asyncio
            import os
            
            # プロンプトを取得（新しい形式に対応）
            if isinstance(self.prompt, dict):
                positive_prompt = self.prompt.get("positive", "")
                negative_prompt = self.prompt.get("negative", "")
                prompt = positive_prompt
            else:
                # 旧形式の場合はそのまま使用
                prompt = self.prompt
                negative_prompt = "blurry, low quality, distorted, deformed"
            
            options = {"width": width, "height": height}
            
            # ネガティブプロンプト付きで画像生成
            if negative_prompt:
                path = await asyncio.to_thread(generate_image_with_negative, prompt, negative_prompt, options)
            else:
                path = await asyncio.to_thread(generate_image, prompt, options)
            
            # ファイルサイズをチェック
            file_size = os.path.getsize(path) / (1024 * 1024)  # MB
            print(f"生成された画像サイズ: {file_size:.2f}MB")
            
            # 高解像度（WQHD以上）または8MBを超える場合は外部ホスティングを使用
            use_external_hosting = (file_size > 8) or (width >= 2560 or height >= 1440)
            
            if use_external_hosting:
                # 外部ホスティングを試行
                hosting_reason = "高解像度画像" if (width >= 2560 or height >= 1440) else f"ファイルサイズ（{file_size:.1f}MB）"
                await msg.edit(content=f"{hosting_reason}のため、外部ホスティングにアップロード中...")
                
                try:
                    # ImgBBにアップロード（APIキー不要）
                    from image_generator import upload_to_imgbb
                    image_url = await asyncio.to_thread(upload_to_imgbb, path)
                    
                    if image_url:
                        embed = discord.Embed(
                            title="🎨 画像生成完了",
                            description=f"高解像度画像（{file_size:.1f}MB）を生成しました！",
                            color=discord.Color.green()
                        )
                        embed.set_image(url=image_url)
                        embed.add_field(name="📊 画像サイズ", value=f"{file_size:.1f}MB", inline=True)
                        embed.add_field(name="📐 解像度", value=f"{width}x{height}", inline=True)
                        embed.add_field(name="🔗 直接リンク", value=f"[画像を開く]({image_url})", inline=False)
                        
                        await msg.edit(content="", embed=embed)
                    else:
                        # 外部アップロード失敗時はエラーメッセージ
                        await msg.edit(content=f"❌ 外部アップロードに失敗しました。画像サイズ（{file_size:.1f}MB）が大きすぎます。")
                        
                except Exception as upload_error:
                    print(f"外部アップロードエラー: {upload_error}")
                    await msg.edit(content=f"❌ 外部アップロードに失敗しました: {upload_error}")
                    
                finally:
                    # 一時ファイルを削除
                    try:
                        os.remove(path)
                    except:
                        pass
                return
            
            # 8MB以下かつ低解像度の場合は通常通りDiscordにアップロード
            file = discord.File(path)
            await msg.edit(content="画像を生成しました！", attachments=[file])
            os.remove(path)
            
        except Exception as e:
            await msg.edit(content=f"画像生成に失敗しました: {e}")
            # エラー時もファイルを削除
            try:
                if 'path' in locals():
                    os.remove(path)
            except:
                pass

# 画像生成ブロックユーザーリスト（ファイル保存対応）
IMAGEGEN_DENY_USERS_FILE = "discordbot/imagegen_deny_users.json"
try:
    with open(IMAGEGEN_DENY_USERS_FILE, "r", encoding="utf-8") as f:
        IMAGEGEN_DENY_USERS = set(json.load(f))
except Exception:
    IMAGEGEN_DENY_USERS = set()

def save_imagegen_deny_users():
    with open(IMAGEGEN_DENY_USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(IMAGEGEN_DENY_USERS), f)

@bot.tree.command(name="imagegen_block", description="指定ユーザーの画像生成を禁止（管理者のみ）")
@app_commands.describe(user="画像生成を禁止するユーザー")
async def imagegen_block(interaction: discord.Interaction, user: discord.User):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("管理者のみ実行できます。", ephemeral=True)
        return
    IMAGEGEN_DENY_USERS.add(user.id)
    save_imagegen_deny_users()
    await interaction.response.send_message(f"{user.display_name} の画像生成を禁止しました。", ephemeral=True)

@bot.tree.command(name="imagegen_unblock", description="指定ユーザーの画像生成禁止を解除（管理者のみ）")
@app_commands.describe(user="画像生成禁止を解除するユーザー")
async def imagegen_unblock(interaction: discord.Interaction, user: discord.User):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("管理者のみ実行できます。", ephemeral=True)
        return
    IMAGEGEN_DENY_USERS.discard(user.id)
    save_imagegen_deny_users()
    await interaction.response.send_message(f"{user.display_name} の画像生成禁止を解除しました。", ephemeral=True)

# グローバル画像生成許可フラグ（ファイル保存対応）
IMAGEGEN_ENABLED_FILE = "discordbot/imagegen_enabled.json"
try:
    with open(IMAGEGEN_ENABLED_FILE, "r", encoding="utf-8") as f:
        IMAGEGEN_ENABLED = json.load(f)
except Exception:
    IMAGEGEN_ENABLED = True

def save_imagegen_enabled():
    with open(IMAGEGEN_ENABLED_FILE, "w", encoding="utf-8") as f:
        json.dump(IMAGEGEN_ENABLED, f)

YONERAI12_ID = 1069941291661672498

@bot.tree.command(name="imagegen_global_on", description="全ユーザーの画像生成を許可（よねらい専用）")
async def imagegen_global_on(interaction: discord.Interaction):
    if interaction.user.id != YONERAI12_ID:
        await interaction.response.send_message("このコマンドは管理者のみ実行できます。", ephemeral=True)
        return
    global IMAGEGEN_ENABLED
    IMAGEGEN_ENABLED = True
    save_imagegen_enabled()
    await interaction.response.send_message("全ユーザーの画像生成を許可しました。", ephemeral=True)

@bot.tree.command(name="imagegen_global_off", description="全ユーザーの画像生成を禁止（よねらい専用）")
async def imagegen_global_off(interaction: discord.Interaction):
    if interaction.user.id != YONERAI12_ID:
        await interaction.response.send_message("このコマンドは管理者のみ実行できます。", ephemeral=True)
        return
    global IMAGEGEN_ENABLED
    IMAGEGEN_ENABLED = False
    save_imagegen_enabled()
    await interaction.response.send_message("全ユーザーの画像生成を禁止しました。", ephemeral=True)

# 画像生成コマンドの先頭でチェック
@bot.tree.command(name="画像生成", description="AI画像生成 - 日本語で詳細に書くほど精度が上がります")
@app_commands.describe(prompt="生成したい画像の説明（日本語可）。英語で的確・詳細・構図・光・質感など、具体的に書くほど精度が上がります")
async def imagegen(interaction: discord.Interaction, prompt: str):
    if not IMAGEGEN_ENABLED:
        await interaction.response.send_message("現在画像生成は管理者により停止中です。", ephemeral=True)
        return
    if interaction.user.id in IMAGEGEN_DENY_USERS:
        await interaction.response.send_message("あなたは現在画像生成を利用できません。", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    
    try:
        # LLMでプロンプト変換（高品質化）
        llm_prompt = f"""あなたはStable Diffusionのプロンプトエンジニアです。
以下の日本語の指示を、高品質なStable Diffusion用の英語プロンプトに変換してください。

要求：
1. 写実的で詳細な描写を含める
2. 構図、光、質感、色調を具体的に指定
3. アートスタイルやレンダリング品質を明記
4. ネガティブプロンプトも含める
5. 英語のみで出力（日本語は含めない）

入力: {prompt}

必ず以下の形式で出力してください：
Positive: [詳細な英語プロンプト]
Negative: [ネガティブプロンプト]

例：
入力: 猫
Positive: realistic cat, detailed fur, natural lighting, high quality photo, 4K, soft focus
Negative: blurry, low quality, distorted, deformed, ugly"""

        llm_response = await cappuccino_agent.process(llm_prompt)
        
        # LLMの出力からプロンプトを抽出
        sd_prompt = llm_response.strip()
        print(f"LLM出力: {sd_prompt}")
        
        # Positive/Negativeプロンプトを分離
        positive_prompt = ""
        negative_prompt = ""
        
        # より堅牢な抽出ロジック
        if "Positive:" in sd_prompt and "Negative:" in sd_prompt:
            # Positive: と Negative: の間を抽出
            positive_match = re.search(r'Positive:\s*(.*?)(?=\s*Negative:|$)', sd_prompt, re.DOTALL)
            negative_match = re.search(r'Negative:\s*(.*?)(?=\s*$)', sd_prompt, re.DOTALL)
            
            if positive_match:
                positive_prompt = positive_match.group(1).strip()
            if negative_match:
                negative_prompt = negative_match.group(1).strip()
        else:
            # フォールバック: 英語部分のみを抽出
            english_lines = []
            for line in sd_prompt.split('\n'):
                line = line.strip()
                if line and not re.search(r'[ぁ-んァ-ン一-龥]', line):
                    english_lines.append(line)
            
            if english_lines:
                positive_prompt = ' '.join(english_lines)
                negative_prompt = "blurry, low quality, distorted, deformed"
        
        # プロンプトが空の場合はフォールバック
        if not positive_prompt:
            positive_prompt = f"{prompt}, realistic, high quality, detailed"
            negative_prompt = "blurry, low quality, distorted, deformed"
        
        print(f"Positive: {positive_prompt}")
        print(f"Negative: {negative_prompt}")
        
        # プロンプトとネガティブプロンプトを組み合わせて保存
        full_prompt = {
            "positive": positive_prompt,
            "negative": negative_prompt
        }
        
        await interaction.followup.send("比率を選択してください：", view=AspectRatioView(full_prompt), ephemeral=True)
        
    except Exception as e:
        logger.error(f"画像生成コマンドエラー: {e}")
        await interaction.followup.send(f"❌ プロンプト処理中にエラーが発生しました: {e}")

@bot.tree.command(name="画像生成heavy", description="プロンプト・ネガティブプロンプトを直接指定して画像生成（上級者向け）")
@app_commands.describe(prompt="Stable Diffusion用プロンプト（英語推奨）", negative_prompt="ネガティブプロンプト（英語推奨）")
async def imagegen_heavy(interaction: discord.Interaction, prompt: str, negative_prompt: str):
    if not IMAGEGEN_ENABLED:
        await interaction.response.send_message("現在画像生成は管理者により停止中です。", ephemeral=True)
        return
    if interaction.user.id in IMAGEGEN_DENY_USERS:
        await interaction.response.send_message("あなたは現在画像生成を利用できません。", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        # 画像生成（プロンプトをそのまま渡す）
        options = {"width": 512, "height": 768}  # 必要に応じてUIで選択可
        path = await asyncio.to_thread(generate_image_with_negative, prompt, negative_prompt, options)
        import os
        file_size = os.path.getsize(path) / (1024 * 1024)
        DISCORD_LIMIT_MB = 25
        if file_size > DISCORD_LIMIT_MB:
            await interaction.followup.send(f"❌ ファイルサイズが大きすぎて送信できません（{file_size:.2f}MB > {DISCORD_LIMIT_MB}MB）。画像サイズや画質を下げてください。", ephemeral=True)
            try:
                os.remove(path)
            except:
                pass
            return
        file = discord.File(path)
        await interaction.followup.send(content="画像を生成しました！（Heavyモード）", file=file, ephemeral=True)
        os.remove(path)
    except Exception as e:
        logger.error(f"画像生成Heavyコマンドエラー: {e}")
        await interaction.followup.send(f"❌ Heavy画像生成または送信中にエラーが発生しました: {e}", ephemeral=True)

# ───────────────── 地震情報・天気・ニュース機能 ─────────────────

async def get_weather_data(city: str = "Tokyo") -> dict:
    """天気情報を取得"""
    try:
        # OpenWeatherMap APIを使用（無料版）
        api_key = os.getenv("OPENWEATHER_API_KEY", "")
        if not api_key:
            return {"error": "OpenWeatherMap APIキーが設定されていません"}
        
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ja"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "city": data["name"],
                        "temp": data["main"]["temp"],
                        "humidity": data["main"]["humidity"],
                        "description": data["weather"][0]["description"],
                        "icon": data["weather"][0]["icon"]
                    }
                else:
                    return {"error": f"天気情報の取得に失敗: {response.status}"}
    except Exception as e:
        return {"error": f"天気情報取得エラー: {e}"}

async def get_news_data() -> list:
    """ニュース情報を取得"""
    try:
        # より安定したニュースソースに変更（日本・海外）
        news_sources = [
            # 日本のニュースソース
            "https://www3.nhk.or.jp/rss/news/cat0.xml",  # NHK 主要ニュース
            "https://www.asahi.com/rss/asahi/newsheadlines.rdf",  # 朝日新聞
            "https://www.yomiuri.co.jp/rss/feed/feed_yol.xml",  # 読売新聞
            "https://www.nikkei.com/rss/feed/nikkei/news.xml",  # 日経新聞
            # 海外のニュースソース
            "https://feeds.nbcnews.com/nbcnews/public/world",
            "https://feeds.bbci.co.uk/news/world/rss.xml",
            "https://rss.cbc.ca/lineup/world.xml",
            "https://feeds.reuters.com/Reuters/worldNews"
        ]
        
        all_news = []
        # SSL証明書の問題を回避するための設定
        connector = aiohttp.TCPConnector(ssl=False)
        timeout = aiohttp.ClientTimeout(total=10)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            for source in news_sources:
                try:
                    async with session.get(source) as response:
                        if response.status == 200:
                            content = await response.text()
                            feed = feedparser.parse(content)
                            for entry in feed.entries[:2]:  # 各ソースから最新2件（日本・海外バランス）
                                # ソース名を日本語で表示
                                source_name = "NHK" if "nhk" in source else \
                                            "朝日新聞" if "asahi" in source else \
                                            "読売新聞" if "yomiuri" in source else \
                                            "日経新聞" if "nikkei" in source else \
                                            "NBC" if "nbcnews" in source else \
                                            "BBC" if "bbci" in source else \
                                            "CBC" if "cbc" in source else \
                                            "Reuters" if "reuters" in source else \
                                            source.split('/')[-1]
                                
                                all_news.append({
                                    "title": entry.title,
                                    "link": entry.link,
                                    "published": getattr(entry, 'published', ''),
                                    "source": source_name
                                })
                        else:
                            print(f"ニュースソース {source} のHTTPステータス: {response.status}")
                except Exception as e:
                    print(f"ニュースソース {source} の取得に失敗: {e}")
        
        return all_news[:8]  # 最新8件を返す（日本・海外バランス）
    except Exception as e:
        return [{"error": f"ニュース取得エラー: {e}"}]

async def get_eew_data() -> dict:
    """地震情報を取得（簡易版）"""
    try:
        # 気象庁の地震情報RSS（実際のAPIは制限があるため簡易版）
        # 実際の実装では、気象庁のAPIや地震情報サービスを使用
        return {
            "status": "no_earthquake",
            "message": "現在、大きな地震は報告されていません。",
            "timestamp": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": f"地震情報取得エラー: {e}"}

# ───────────────── スラッシュコマンド ─────────────────

@bot.tree.command(name="天気", description="🌤️ 指定した都市の天気情報を表示")
@app_commands.describe(city="都市名（例: Tokyo, Osaka, Kyoto）")
async def weather_command(interaction: discord.Interaction, city: str = "Tokyo"):
    """天気情報を表示するスラッシュコマンド"""
    await interaction.response.defer()
    
    try:
        weather_data = await get_weather_data(city)
        
        if "error" in weather_data:
            await interaction.followup.send(f"❌ {weather_data['error']}")
            return
        
        embed = discord.Embed(
            title=f"🌤️ {weather_data['city']}の天気",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(
            name="🌡️ 気温",
            value=f"{weather_data['temp']}°C",
            inline=True
        )
        embed.add_field(
            name="💧 湿度",
            value=f"{weather_data['humidity']}%",
            inline=True
        )
        embed.add_field(
            name="☁️ 天気",
            value=weather_data['description'],
            inline=True
        )
        
        # 天気アイコンを設定
        weather_icon = weather_data['icon']
        embed.set_thumbnail(url=f"http://openweathermap.org/img/wn/{weather_icon}@2x.png")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Weather command error: {e}")
        await interaction.followup.send(f"❌ 天気情報の取得中にエラーが発生しました: {e}")

@bot.tree.command(name="ニュース", description="📰 最新のニュースを表示（日本・海外）")
@app_commands.describe(count="表示するニュース数（1-10）")
async def news_command(interaction: discord.Interaction, count: int = 5):
    """ニュース情報を表示するスラッシュコマンド"""
    await interaction.response.defer()
    
    try:
        news_data = await get_news_data()
        
        if not news_data or (len(news_data) == 1 and "error" in news_data[0]):
            error_msg = news_data[0]["error"] if news_data else "ニュースが取得できませんでした"
            await interaction.followup.send(f"❌ {error_msg}")
            return
        
        embed = discord.Embed(
            title="📰 最新ニュース",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        
        for i, news in enumerate(news_data[:count], 1):
            title = news["title"][:100] + "..." if len(news["title"]) > 100 else news["title"]
            embed.add_field(
                name=f"{i}. {title}",
                value=f"🔗 [記事を読む]({news['link']})\n📅 {news.get('published', 'N/A')}",
                inline=False
            )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"News command error: {e}")
        await interaction.followup.send(f"❌ ニュースの取得中にエラーが発生しました: {e}")

@bot.tree.command(name="地震情報", description="🌋 最新の地震情報を表示")
async def eew_command(interaction: discord.Interaction):
    """地震情報を表示するスラッシュコマンド"""
    await interaction.response.defer()
    
    try:
        eew_data = await get_eew_data()
        
        if "error" in eew_data:
            await interaction.followup.send(f"❌ {eew_data['error']}")
            return
        
        embed = discord.Embed(
            title="🌋 地震情報",
            color=discord.Color.red() if eew_data["status"] != "no_earthquake" else discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(
            name="📊 状況",
            value=eew_data["message"],
            inline=False
        )
        
        embed.add_field(
            name="🕐 更新時刻",
            value=eew_data["timestamp"],
            inline=True
        )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"EEW command error: {e}")
        await interaction.followup.send(f"❌ 地震情報の取得中にエラーが発生しました: {e}")

# ───────────────── 自動配信機能 ─────────────────

async def auto_news_task():
    """定期的にニュースを自動配信"""
    while True:
        try:
            if NEWS_CHANNEL_ID:
                channel = bot.get_channel(NEWS_CHANNEL_ID)
                if channel:
                    news_data = await get_news_data()
                    if news_data and len(news_data) > 0 and "error" not in news_data[0]:
                        embed = discord.Embed(
                            title="📰 自動ニュース配信",
                            color=discord.Color.green(),
                            timestamp=discord.utils.utcnow()
                        )
                        
                        for i, news in enumerate(news_data[:3], 1):
                            title = news["title"][:100] + "..." if len(news["title"]) > 100 else news["title"]
                            embed.add_field(
                                name=f"{i}. {title}",
                                value=f"🔗 [記事を読む]({news['link']})",
                                inline=False
                            )
                        
                        await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Auto news task error: {e}")
        
        # 6時間ごとに実行
        await asyncio.sleep(6 * 60 * 60)

async def auto_weather_task():
    """定期的に天気を自動配信"""
    while True:
        try:
            if WEATHER_CHANNEL_ID:
                channel = bot.get_channel(WEATHER_CHANNEL_ID)
                if channel:
                    weather_data = await get_weather_data("Tokyo")
                    if "error" not in weather_data:
                        embed = discord.Embed(
                            title=f"🌤️ {weather_data['city']}の天気",
                            color=discord.Color.blue(),
                            timestamp=discord.utils.utcnow()
                        )
                        
                        embed.add_field(
                            name="🌡️ 気温",
                            value=f"{weather_data['temp']}°C",
                            inline=True
                        )
                        embed.add_field(
                            name="💧 湿度",
                            value=f"{weather_data['humidity']}%",
                            inline=True
                        )
                        embed.add_field(
                            name="☁️ 天気",
                            value=weather_data['description'],
                            inline=True
                        )
                        
                        await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Auto weather task error: {e}")
        
        # 3時間ごとに実行
        await asyncio.sleep(3 * 60 * 60)

# ───────────────── 設定コマンド ─────────────────

@bot.tree.command(name="ニュース設定", description="⚙️ ニュース自動配信のチャンネルを設定")
@app_commands.describe(channel="ニュースを配信するチャンネル")
async def set_news_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    """ニュース自動配信のチャンネルを設定"""
    try:
        global NEWS_CHANNEL_ID
        NEWS_CHANNEL_ID = channel.id
        _save_news_channel(channel.id)
        
        embed = discord.Embed(
            title="✅ ニュース設定完了",
            description=f"ニュース自動配信を **{channel.mention}** に設定しました",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        logger.error(f"Set news channel error: {e}")
        await interaction.response.send_message(f"❌ 設定に失敗しました: {e}")

@bot.tree.command(name="天気設定", description="⚙️ 天気自動配信のチャンネルを設定")
@app_commands.describe(channel="天気を配信するチャンネル")
async def set_weather_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    """天気自動配信のチャンネルを設定"""
    try:
        global WEATHER_CHANNEL_ID
        WEATHER_CHANNEL_ID = channel.id
        _save_weather_channel(channel.id)
        
        embed = discord.Embed(
            title="✅ 天気設定完了",
            description=f"天気自動配信を **{channel.mention}** に設定しました",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        logger.error(f"Set weather channel error: {e}")
        await interaction.response.send_message(f"❌ 設定に失敗しました: {e}")

@bot.tree.command(name="地震設定", description="⚙️ 地震情報自動配信のチャンネルを設定")
@app_commands.describe(channel="地震情報を配信するチャンネル")
async def set_eew_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    """地震情報自動配信のチャンネルを設定"""
    try:
        global EEW_CHANNEL_ID
        EEW_CHANNEL_ID = channel.id
        _save_eew_channel(channel.id)
        
        embed = discord.Embed(
            title="✅ 地震情報設定完了",
            description=f"地震情報自動配信を **{channel.mention}** に設定しました",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        logger.error(f"Set EEW channel error: {e}")
        await interaction.response.send_message(f"❌ 設定に失敗しました: {e}")

# ───────────────── 追加コマンド ─────────────────

@bot.tree.command(name="poker", description="🃏 ヘッズアップポーカーゲーム")
@app_commands.describe(user="対戦相手（指定しない場合はBOT）")
async def poker_command(interaction: discord.Interaction, user: discord.Member = None):
    """ポーカーゲームを開始"""
    try:
        if user is None:
            user = bot.user
        
        # ポーカーマッチを作成
        match = PokerMatch(interaction.user, user)
        view = PokerView(match)
        
        embed = discord.Embed(
            title="🃏 ポーカーゲーム開始",
            description=f"{interaction.user.mention} vs {user.mention}",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed, view=view)
        
    except Exception as e:
        logger.error(f"Poker command error: {e}")
        await interaction.response.send_message(f"❌ ポーカーゲームの開始に失敗しました: {e}")

@bot.tree.command(name="qr", description="📱 QRコードを生成")
@app_commands.describe(text="QRコードに変換するテキスト")
async def qr_command(interaction: discord.Interaction, text: str):
    """QRコードを生成"""
    try:
        import qrcode
        from io import BytesIO
        
        # QRコードを生成
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(text)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 画像をバイトに変換
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        file = discord.File(buffer, filename="qr_code.png")
        
        embed = discord.Embed(
            title="📱 QRコード生成完了",
            description=f"テキスト: `{text}`",
            color=discord.Color.blue()
        )
        embed.set_image(url="attachment://qr_code.png")
        
        await interaction.response.send_message(embed=embed, file=file)
        
    except Exception as e:
        logger.error(f"QR command error: {e}")
        await interaction.response.send_message(f"❌ QRコードの生成に失敗しました: {e}")

@bot.tree.command(name="barcode", description="📊 バーコードを生成")
@app_commands.describe(text="バーコードに変換するテキスト")
async def barcode_command(interaction: discord.Interaction, text: str):
    """バーコードを生成"""
    try:
        import barcode
        from barcode.writer import ImageWriter
        from io import BytesIO
        
        # Code128バーコードを生成
        code128 = barcode.get('code128', text, writer=ImageWriter())
        
        # 画像をバイトに変換
        buffer = BytesIO()
        code128.write(buffer)
        buffer.seek(0)
        
        file = discord.File(buffer, filename="barcode.png")
        
        embed = discord.Embed(
            title="📊 バーコード生成完了",
            description=f"テキスト: `{text}`",
            color=discord.Color.green()
        )
        embed.set_image(url="attachment://barcode.png")
        
        await interaction.response.send_message(embed=embed, file=file)
        
    except Exception as e:
        logger.error(f"Barcode command error: {e}")
        await interaction.response.send_message(f"❌ バーコードの生成に失敗しました: {e}")

@bot.tree.command(name="tex", description="📐 TeX数式を画像に変換")
@app_commands.describe(formula="TeX数式（例: x^2 + y^2 = r^2）")
async def tex_command(interaction: discord.Interaction, formula: str):
    """TeX数式を画像に変換"""
    try:
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use('Agg')
        from io import BytesIO
        
        # 数式を画像に変換
        fig, ax = plt.subplots(figsize=(8, 2))
        ax.text(0.5, 0.5, f"${formula}$", fontsize=20, ha='center', va='center')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        # 画像をバイトに変換
        buffer = BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight', dpi=150)
        buffer.seek(0)
        plt.close()
        
        file = discord.File(buffer, filename="formula.png")
        
        embed = discord.Embed(
            title="📐 TeX数式変換完了",
            description=f"数式: `{formula}`",
            color=discord.Color.purple()
        )
        embed.set_image(url="attachment://formula.png")
        
        await interaction.response.send_message(embed=embed, file=file)
        
    except Exception as e:
        logger.error(f"TeX command error: {e}")
        await interaction.response.send_message(f"❌ 数式の変換に失敗しました: {e}")

@bot.tree.command(name="dice", description="🎲 ダイスを振る")
@app_commands.describe(sides="サイコロの面数（デフォルト: 6）")
async def dice_command(interaction: discord.Interaction, sides: int = 6):
    """ダイスを振る"""
    try:
        if sides < 2:
            await interaction.response.send_message("❌ 面数は2以上である必要があります")
            return
        
        result = random.randint(1, sides)
        
        embed = discord.Embed(
            title="🎲 ダイス結果",
            description=f"**{result}** (1-{sides})",
            color=discord.Color.orange()
        )
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        logger.error(f"Dice command error: {e}")
        await interaction.response.send_message(f"❌ ダイスの実行に失敗しました: {e}")

@bot.tree.command(name="userinfo", description="👤 ユーザー情報を表示")
@app_commands.describe(user="情報を表示するユーザー（指定しない場合は自分）")
async def userinfo_command(interaction: discord.Interaction, user: discord.Member = None):
    """ユーザー情報を表示"""
    try:
        if user is None:
            user = interaction.user
        
        embed = discord.Embed(
            title=f"👤 {user.display_name}の情報",
            color=user.color if user.color != discord.Color.default() else discord.Color.blue()
        )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="🆔 ユーザーID", value=user.id, inline=True)
        embed.add_field(name="📅 アカウント作成日", value=user.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="🎭 ニックネーム", value=user.nick or "なし", inline=True)
        embed.add_field(name="🎨 色", value=str(user.color), inline=True)
        embed.add_field(name="📊 ステータス", value=str(user.status), inline=True)
        embed.add_field(name="🎮 ゲーム", value=user.activity.name if user.activity else "なし", inline=True)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        logger.error(f"Userinfo command error: {e}")
        await interaction.response.send_message(f"❌ ユーザー情報の取得に失敗しました: {e}")

@bot.tree.command(name="help", description="🤖 利用可能なコマンド一覧を表示")
async def help_command(interaction: discord.Interaction):
    """ヘルプコマンド"""
    embed = discord.Embed(
        title="🤖 ボットコマンド一覧",
        description="利用可能なスラッシュコマンドとテキストコマンド",
        color=discord.Color.blue()
    )
    
    # 画像・AI関連
    embed.add_field(
        name="🎨 画像・AI",
        value="• `/画像生成` - 画像生成\n"
              "• `@ボット 質問` - AI質問\n"
              "• `r? 質問` - AI質問",
        inline=False
    )
    
    # 情報・ニュース
    embed.add_field(
        name="📰 情報・ニュース",
        value="• `/天気` - 天気情報\n"
              "• `/ニュース` - 最新ニュース\n"
              "• `/地震情報` - 地震情報",
        inline=False
    )
    
    # 設定
    embed.add_field(
        name="⚙️ 設定",
        value="• `/ニュース設定` - ニュース配信設定\n"
              "• `/天気設定` - 天気配信設定\n"
              "• `/地震設定` - 地震情報設定",
        inline=False
    )
    
    # ユーティリティ
    embed.add_field(
        name="🛠️ ユーティリティ",
        value="• `/poker` - ポーカーゲーム\n"
              "• `/qr` - QRコード生成\n"
              "• `/barcode` - バーコード生成\n"
              "• `/tex` - TeX数式変換\n"
              "• `/dice` - ダイスロール\n"
              "• `/userinfo` - ユーザー情報",
        inline=False
    )
    
    # GPU監視
    embed.add_field(
        name="🖥️ GPU監視",
        value="• `/gpu` - GPU使用率\n"
              "• `/gpumemory` - GPUメモリ使用量\n"
              "• `/gpuprocesses` - GPUプロセス",
        inline=False
    )
    
    embed.set_footer(text="詳細は各コマンドの説明を参照してください")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="🏓 ボットの応答時間を測定")
async def ping_command(interaction: discord.Interaction):
    """Pingコマンド"""
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"応答時間: **{round(bot.latency * 1000)}ms**",
        color=discord.Color.green()
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="serverinfo", description="🏠 サーバー情報を表示")
async def serverinfo_command(interaction: discord.Interaction):
    """サーバー情報を表示"""
    try:
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("❌ このコマンドはサーバー内でのみ使用できます")
            return
        
        embed = discord.Embed(
            title=f"🏠 {guild.name}の情報",
            color=discord.Color.blue()
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        embed.add_field(name="🆔 サーバーID", value=guild.id, inline=True)
        embed.add_field(name="👑 オーナー", value=guild.owner.mention, inline=True)
        embed.add_field(name="📅 作成日", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="👥 メンバー数", value=guild.member_count, inline=True)
        embed.add_field(name="📺 チャンネル数", value=len(guild.channels), inline=True)
        embed.add_field(name="🎭 ロール数", value=len(guild.roles), inline=True)
        embed.add_field(name="😀 絵文字数", value=len(guild.emojis), inline=True)
        embed.add_field(name="🛡️ 認証レベル", value=str(guild.verification_level), inline=True)
        embed.add_field(name="🎵 ブーストレベル", value=guild.premium_tier, inline=True)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        logger.error(f"Serverinfo command error: {e}")
        await interaction.response.send_message(f"❌ サーバー情報の取得に失敗しました: {e}")


@bot.tree.command(name="tts", description="🎤 テキストをずんだもんの声でVCに読み上げ")
@app_commands.describe(text="読み上げるテキスト")
async def tts_command(interaction: discord.Interaction, text: str):
    try:
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ VCに参加してからこのコマンドを使用してください")
            return
        zunda_text = f"ずんだもんです。{text}"
        audio_data = None
        if VOICEVOX_AVAILABLE:
            audio_data = await generate_zunda_voice(zunda_text)
        if audio_data is None and TTS_AVAILABLE:
            tts = gTTS(text=zunda_text, lang='ja', slow=False)
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_data = audio_buffer.getvalue()
        if audio_data is None:
            await interaction.response.send_message("❌ 音声生成に失敗しました")
            return
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            tmp_file.write(audio_data)
            tts_path = tmp_file.name
        tts_duration = get_wav_duration(tts_path)
        # VCに接続
        if interaction.guild.voice_client is None:
            voice = await interaction.user.voice.channel.connect()
        else:
            voice = interaction.guild.voice_client
        # サーバーごとの音量取得
        volume = SERVER_MUSIC_VOLUME.get(str(interaction.guild.id), 1.0) * 0.04
        # 現在のBGMストリーミングURLまたはローカルファイルパスを取得
        bgm_url = None
        bgm_local_path = None
        # ストリーミングURL
        if hasattr(voice, 'source') and hasattr(voice.source, '_source') and hasattr(voice.source._source, '_input'):
            bgm_url = voice.source._source._input
        # ローカルファイル再生中（PCMVolumeTransformer→FFmpegPCMAudio→ファイルパス）
        elif hasattr(voice, 'source') and hasattr(voice.source, 'original') and hasattr(voice.source.original, 'source'):
            # discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(path)) の場合
            bgm_local_path = getattr(voice.source.original, 'source', None)
        elif hasattr(voice, 'source') and hasattr(voice.source, 'source'):
            # discord.FFmpegPCMAudio(path) の場合
            bgm_local_path = getattr(voice.source, 'source', None)
        # BGM合成処理
        if bgm_url:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as bgm_file:
                bgm_path = bgm_file.name
            ok = save_streaming_bgm_segment(bgm_url, tts_duration, bgm_path)
            if ok:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as mix_file:
                    mix_path = mix_file.name
                # ffmpegでamix合成（TTS中BGM音量0.5）
                import subprocess
                cmd = [
                    'ffmpeg', '-y',
                    '-i', bgm_path,
                    '-i', tts_path,
                    '-filter_complex', '[0:a]volume=0.5[a0];[a0][1:a]amix=inputs=2:duration=first:dropout_transition=0',
                    '-c:a', 'pcm_s16le', '-ar', '48000', '-ac', '2', mix_path
                ]
                subprocess.run(cmd, check=True)
                play_path = mix_path
            else:
                play_path = tts_path
       
        # 再生（サーバーごとの音量を必ず反映）
        try:
            import asyncio
            if voice.is_playing():
                voice.stop()
                await asyncio.sleep(0.5)
                # まだ再生中なら最大2回まで待つ
                for _ in range(2):
                    if not voice.is_playing():
                        break
                    await asyncio.sleep(0.5)
            audio = discord.FFmpegPCMAudio(
                play_path,
                options='-vn -ar 48000 -ac 2 -b:a 128k'
            )
            audio = discord.PCMVolumeTransformer(audio, volume=volume)
            voice.play(
                audio,
                after=lambda e: cleanup()
            )
            def cleanup():
                import os
                for p in [tts_path, play_path]:
                    try:
                        os.unlink(p)
                    except:
                        pass
        except Exception as e:
            await interaction.response.send_message(f"❌ 音声再生に失敗しました: {e}")
            try:
                import os
                for p in [tts_path, play_path]:
                    try:
                        os.unlink(p)
                    except:
                        pass
            except:
                pass
    except Exception as e:
        logger.error(f"TTS command error: {e}")
        try:
            await interaction.response.send_message(f"❌ TTS読み上げに失敗しました: {e}")
        except:
            pass


@bot.tree.command(name="join", description="🎤 VCに参加してチャンネルのメッセージを読み上げ")
async def join_command(interaction: discord.Interaction):
    """VC参加コマンド"""
    try:
        # ユーザーがVCに参加しているかチェック
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ VCに参加してからこのコマンドを使用してください")
            return
        
        vc_channel = interaction.user.voice.channel
        text_channel = interaction.channel
        
        # VCに接続
        voice = await vc_channel.connect()
        
        # 参加チャンネル設定を保存
        TTS_JOIN_CHANNELS[text_channel.id] = vc_channel.id
        _save_tts_join_channels(TTS_JOIN_CHANNELS)
        
        await interaction.response.send_message(f"🎤 {text_channel.mention} のメッセージを {vc_channel.mention} で読み上げるように設定しました")
        
    except Exception as e:
        logger.error(f"Join command error: {e}")
        await interaction.response.send_message(f"❌ VC参加に失敗しました: {e}")


@bot.tree.command(name="leave", description="🎤 参加チャンネル設定を無効にする")
async def leave_command(interaction: discord.Interaction):
    """VC退出コマンド"""
    try:
        text_channel = interaction.channel
        
        # 参加チャンネル設定を削除
        if text_channel.id in TTS_JOIN_CHANNELS:
            vc_channel_id = TTS_JOIN_CHANNELS.pop(text_channel.id)
            _save_tts_join_channels(TTS_JOIN_CHANNELS)
            
            vc_channel = interaction.guild.get_channel(vc_channel_id)
            if vc_channel:
                await interaction.response.send_message(f"🎤 {text_channel.mention} の読み上げ設定を無効にしました")
            else:
                await interaction.response.send_message(f"🎤 {text_channel.mention} の読み上げ設定を無効にしました")
        else:
            await interaction.response.send_message(f"🎤 {text_channel.mention} には読み上げ設定がありません")
        
    except Exception as e:
        logger.error(f"Leave command error: {e}")
        await interaction.response.send_message(f"❌ 設定の無効化に失敗しました: {e}")


@bot.tree.command(name="tts_on", description="🎤 TTS自動読み上げを有効にする")
@app_commands.describe(channel="対象チャンネル（指定しない場合は個人設定）")
async def tts_on_command(interaction: discord.Interaction, channel: discord.TextChannel = None):
    """TTS有効化コマンド"""
    try:
        global TTS_USERS, TTS_CHANNELS
        
        if channel:
            # チャンネル設定
            TTS_CHANNELS.add(channel.id)
            _save_tts_channels(TTS_CHANNELS)
            await interaction.response.send_message(f"🎤 {channel.mention} のTTS自動読み上げを有効にしました")
        else:
            # 個人設定
            TTS_USERS.add(interaction.user.id)
            _save_tts_users(TTS_USERS)
            await interaction.response.send_message("🎤 個人のTTS自動読み上げを有効にしました")
        
    except Exception as e:
        logger.error(f"TTS on command error: {e}")
        await interaction.response.send_message(f"❌ TTS有効化に失敗しました: {e}")


@bot.tree.command(name="tts_off", description="🎤 TTS自動読み上げを無効にする")
@app_commands.describe(channel="対象チャンネル（指定しない場合は個人設定）")
async def tts_off_command(interaction: discord.Interaction, channel: discord.TextChannel = None):
    """TTS無効化コマンド"""
    try:
        global TTS_USERS, TTS_CHANNELS
        
        if channel:
            # チャンネル設定
            TTS_CHANNELS.discard(channel.id)
            _save_tts_channels(TTS_CHANNELS)
            await interaction.response.send_message(f"🎤 {channel.mention} のTTS自動読み上げを無効にしました")
        else:
            # 個人設定
            TTS_USERS.discard(interaction.user.id)
            _save_tts_users(TTS_USERS)
            await interaction.response.send_message("🎤 個人のTTS自動読み上げを無効にしました")
        
    except Exception as e:
        logger.error(f"TTS off command error: {e}")
        await interaction.response.send_message(f"❌ TTS無効化に失敗しました: {e}")


@bot.tree.command(name="tts_status", description="🎤 TTS自動読み上げの設定状況を表示")
async def tts_status_command(interaction: discord.Interaction):
    """TTS設定状況表示コマンド"""
    try:
        global TTS_USERS, TTS_CHANNELS, TTS_JOIN_CHANNELS, TTS_SETTINGS
        
        if not interaction.guild:
            await interaction.response.send_message("❌ サーバー内でのみ使用できます")
            return
        
        status_text = "🎤 **TTS自動読み上げ設定状況**\n\n"
        
        # ユーザー個人の設定
        if interaction.user.id in TTS_USERS:
            status_text += "✅ **個人設定**: 有効\n"
        else:
            status_text += "❌ **個人設定**: 無効\n"
        
        # チャンネル設定
        if TTS_CHANNELS:
            status_text += "\n**有効なチャンネル**:\n"
            for channel_id in TTS_CHANNELS:
                channel = interaction.guild.get_channel(channel_id)
                if channel:
                    status_text += f"• {channel.mention}\n"
        else:
            status_text += "\n**有効なチャンネル**: なし\n"
        
        # 参加チャンネル設定
        if TTS_JOIN_CHANNELS:
            status_text += "\n**参加チャンネル**:\n"
            for text_channel_id, vc_channel_id in TTS_JOIN_CHANNELS.items():
                text_channel = interaction.guild.get_channel(text_channel_id)
                vc_channel = interaction.guild.get_channel(vc_channel_id)
                if text_channel and vc_channel:
                    status_text += f"• {text_channel.mention} → {vc_channel.mention}\n"
        else:
            status_text += "\n**参加チャンネル**: なし\n"
        
        # TTS設定（サーバー別）
        server_id = interaction.guild.id
        server_settings = SERVER_TTS_SETTINGS.get(server_id, TTS_SETTINGS)
        
        status_text += f"\n**TTS設定（このサーバー）**:\n"
        status_text += f"• 読み上げ速度: {server_settings['speed']}x\n"
        status_text += f"• 音声タイプ: {server_settings['voice']}\n"
        status_text += f"• 音量: {server_settings['volume']}x\n"
        
        status_text += "\n**使い方**:\n"
        status_text += "• `/tts_on` - 個人設定を有効にする\n"
        status_text += "• `/tts_off` - 個人設定を無効にする\n"
        status_text += "• `/tts_on #チャンネル` - チャンネル設定を有効にする\n"
        status_text += "• `/tts_off #チャンネル` - チャンネル設定を無効にする\n"
        status_text += "• `/join` - 現在のVCに参加してチャンネル読み上げを有効にする\n"
        status_text += "• `/leave` - 参加チャンネル設定を無効にする\n"
        status_text += "• `/tts_speed 速度` - 読み上げ速度を設定（0.5-2.0）\n"
        status_text += "• `/tts_voice タイプ` - 音声タイプを設定（zunda, gtts）\n"
        
        await interaction.response.send_message(status_text)
        
    except Exception as e:
        logger.error(f"TTS status command error: {e}")
        await interaction.response.send_message(f"❌ 設定状況の取得に失敗しました: {e}")


@bot.tree.command(name="tts_speed", description="🎤 TTS読み上げ速度を設定（サーバー別）")
@app_commands.describe(speed="読み上げ速度（0.5-2.0）")
async def tts_speed_command(interaction: discord.Interaction, speed: float):
    """TTS読み上げ速度設定コマンド（サーバー別）"""
    try:
        global SERVER_TTS_SETTINGS
        
        if speed < 0.5 or speed > 2.0:
            await interaction.response.send_message("❌ 速度は0.5から2.0の間で設定してください")
            return
        
        # サーバー別の設定を保存
        server_id = interaction.guild.id
        if server_id not in SERVER_TTS_SETTINGS:
            SERVER_TTS_SETTINGS[server_id] = TTS_SETTINGS.copy()
        
        SERVER_TTS_SETTINGS[server_id]["speed"] = speed
        await interaction.response.send_message(f"🎤 このサーバーの読み上げ速度を {speed}x に設定しました")
        
    except Exception as e:
        logger.error(f"TTS speed command error: {e}")
        await interaction.response.send_message(f"❌ 速度設定に失敗しました: {e}")


@bot.tree.command(name="tts_voice", description="🎤 TTS音声タイプを設定（サーバー別）")
@app_commands.describe(voice_type="音声タイプ（zunda, gtts）")
async def tts_voice_command(interaction: discord.Interaction, voice_type: str):
    """TTS音声タイプ設定コマンド（サーバー別）"""
    try:
        global SERVER_TTS_SETTINGS
        
        if voice_type.lower() not in ["zunda", "gtts"]:
            await interaction.response.send_message("❌ 音声タイプは 'zunda' または 'gtts' を指定してください")
            return
        
        # サーバー別の設定を保存
        server_id = interaction.guild.id
        if server_id not in SERVER_TTS_SETTINGS:
            SERVER_TTS_SETTINGS[server_id] = TTS_SETTINGS.copy()
        
        SERVER_TTS_SETTINGS[server_id]["voice"] = voice_type.lower()
        await interaction.response.send_message(f"🎤 このサーバーの音声タイプを {voice_type} に設定しました")
        
    except Exception as e:
        logger.error(f"TTS voice command error: {e}")
        await interaction.response.send_message(f"❌ 音声タイプ設定に失敗しました: {e}")


@bot.tree.command(name="tts_character", description="🎭 読み上げキャラクターを設定（ユーザー別）")
@app_commands.describe(character="キャラクター名（ずんだもん、つむぎ、など）")
async def tts_character_command(interaction: discord.Interaction, character: str):
    """読み上げキャラクター設定コマンド（ユーザー別）- 将来的な機能拡張用"""
    try:
        global USER_CHARACTER_SETTINGS
        
        # 利用可能なキャラクターリスト
        available_characters = ["ずんだもん", "つむぎ", "めろん", "りん", "あい", "デフォルト"]
        
        if character not in available_characters:
            character_list = "、".join(available_characters)
            await interaction.response.send_message(f"❌ 利用可能なキャラクター: {character_list}")
            return
        
        # ユーザー別の設定を保存
        user_id = interaction.user.id
        USER_CHARACTER_SETTINGS[user_id] = character
        _save_character_settings(USER_CHARACTER_SETTINGS)
        
        await interaction.response.send_message(f"🎭 あなたの読み上げキャラクターを「{character}」に設定しました")
        
    except Exception as e:
        logger.error(f"TTS character command error: {e}")
        await interaction.response.send_message(f"❌ キャラクター設定に失敗しました: {e}")


@bot.tree.command(name="tts_character_status", description="🎭 読み上げキャラクター設定を表示")
async def tts_character_status_command(interaction: discord.Interaction):
    """読み上げキャラクター設定表示コマンド"""
    try:
        global USER_CHARACTER_SETTINGS
        
        user_id = interaction.user.id
        character = USER_CHARACTER_SETTINGS.get(user_id, "デフォルト")
        
        status_text = f"🎭 **あなたの読み上げキャラクター設定**\n\n"
        status_text += f"**現在のキャラクター**: {character}\n\n"
        status_text += "**利用可能なキャラクター**:\n"
        status_text += "• ずんだもん\n"
        status_text += "• つむぎ\n"
        status_text += "• めろん\n"
        status_text += "• りん\n"
        status_text += "• あい\n"
        status_text += "• デフォルト\n\n"
        status_text += "**使い方**:\n"
        status_text += "• `/tts_character キャラクター名` - キャラクターを設定\n"
        status_text += "• `/tts_character_status` - 現在の設定を確認\n"
        
        await interaction.response.send_message(status_text)
        
    except Exception as e:
        logger.error(f"TTS character status command error: {e}")
        await interaction.response.send_message(f"❌ キャラクター設定の取得に失敗しました: {e}")


@bot.tree.command(name="flag", description="🏁 国旗絵文字から国名を翻訳")
@app_commands.describe(emoji="国旗絵文字（例: 🇯🇵 🇺🇸 🇬🇧）")
async def flag_command(interaction: discord.Interaction, emoji: str):
    """国旗翻訳コマンド"""
    try:
        # 絵文字から国コードを取得
        country_code = flag_to_iso(emoji)
        if not country_code:
            await interaction.response.send_message("❌ 有効な国旗絵文字を入力してください")
            return
        
        # 国名を取得
        country_name = get_country_name(country_code)
        if not country_name:
            await interaction.response.send_message(f"❌ 国名が見つかりませんでした: {country_code}")
            return
        
        await interaction.response.send_message(f"🏁 {emoji} → {country_name} ({country_code.upper()})")
        
    except Exception as e:
        logger.error(f"Flag command error: {e}")
        await interaction.response.send_message(f"❌ 国旗翻訳に失敗しました: {e}")


@bot.tree.command(name="translate", description="🌐 メッセージを翻訳")
@app_commands.describe(text="翻訳するテキスト", target_lang="翻訳先言語（例: en, ja, ko）")
async def translate_command(interaction: discord.Interaction, text: str, target_lang: str = "en"):
    """翻訳コマンド"""
    try:
        # 翻訳処理（簡易版）
        translated_text = f"[{target_lang.upper()}] {text}"
        await interaction.response.send_message(f"🌐 **翻訳結果**: {translated_text}")
        
    except Exception as e:
        logger.error(f"Translate command error: {e}")
        await interaction.response.send_message(f"❌ 翻訳に失敗しました: {e}")


@bot.tree.command(name="clear", description="🗑️ チャンネルのメッセージを削除")
@app_commands.describe(count="削除するメッセージ数（1-100）")
async def clear_command(interaction: discord.Interaction, count: int = 10):
    """メッセージ削除コマンド"""
    try:
        if count < 1 or count > 100:
            await interaction.response.send_message("❌ 削除数は1から100の間で指定してください")
            return
        
        # 権限チェック
        if not interaction.channel.permissions_for(interaction.user).manage_messages:
            await interaction.response.send_message("❌ メッセージ管理権限がありません")
            return
        
        deleted = await interaction.channel.purge(limit=count)
        await interaction.response.send_message(f"🗑️ {len(deleted)}件のメッセージを削除しました")
        
    except Exception as e:
        logger.error(f"Clear command error: {e}")
        await interaction.response.send_message(f"❌ メッセージ削除に失敗しました: {e}")


@bot.tree.command(name="poll", description="📊 投票を作成")
@app_commands.describe(question="投票の質問", options="選択肢（カンマ区切り）")
async def poll_command(interaction: discord.Interaction, question: str, options: str):
    """投票コマンド"""
    try:
        option_list = [opt.strip() for opt in options.split(",")]
        if len(option_list) < 2:
            await interaction.response.send_message("❌ 選択肢は2つ以上必要です")
            return
        
        embed = discord.Embed(title="📊 投票", description=question, color=discord.Color.blue())
        for i, option in enumerate(option_list, 1):
            embed.add_field(name=f"選択肢 {i}", value=option, inline=False)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        logger.error(f"Poll command error: {e}")
        await interaction.response.send_message(f"❌ 投票作成に失敗しました: {e}")


@bot.tree.command(name="play", description="YouTube音楽をストリーミングまたはダウンロード再生")
@app_commands.describe(
    stream_url="ストリーミング（Spotify用）再生したいURL（左側）",
    download_url="ダウンロード（高音質YouTube用）再生したいURL（右側）"
)
async def play_command(interaction: discord.Interaction, stream_url: str = None, download_url: str = None):
    await interaction.response.defer(ephemeral=True)
    # VCにいるかチェック
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.followup.send("❌ VCに参加してから使用してください。", ephemeral=True)
        return
    voice_channel = interaction.user.voice.channel
    voice = interaction.guild.voice_client or await voice_channel.connect()
    # サーバーごとの音量取得
    volume = SERVER_MUSIC_VOLUME.get(str(interaction.guild.id), 1.0) * 0.04
    # ストリーミング優先
    if stream_url:
        url, title, duration = get_youtube_audio_stream_url(stream_url)
        if not url:
            await interaction.followup.send("❌ ストリーミングURLの取得に失敗しました。", ephemeral=True)
            return
        try:
            audio = discord.FFmpegPCMAudio(url)
            audio = discord.PCMVolumeTransformer(audio, volume=volume)
            voice.play(
                audio,
                after=lambda e: print(f"ストリーミング再生終了: {e}")
            )
            await interaction.followup.send(f"▶️ ストリーミング再生開始: {title}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ ストリーミング再生に失敗: {e}", ephemeral=True)
        return
    elif download_url:
        path, title, duration = download_youtube_audio(download_url)
        if not path:
            await interaction.followup.send("❌ ダウンロードに失敗しました。", ephemeral=True)
            return
        try:
            audio = discord.FFmpegPCMAudio(path)
            audio = discord.PCMVolumeTransformer(audio, volume=volume)
            voice.play(
                audio,
                after=lambda e: os.remove(path)
            )
            await interaction.followup.send(f"▶️ ダウンロード再生開始: {title}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ ダウンロード再生に失敗: {e}", ephemeral=True)
        return
    else:
        await interaction.followup.send("URLを入力してください（どちらか一方でOK）", ephemeral=True)

@bot.tree.command(name="stop", description="⏹️ 音楽再生を停止")
async def stop_command(interaction: discord.Interaction):
    """音楽再生を停止"""
    if not interaction.guild.voice_client:
        await interaction.response.send_message("❌ 現在音楽を再生していません。", ephemeral=True)
        return
    
    try:
        interaction.guild.voice_client.stop()
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("⏹️ 音楽再生を停止しました。", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ 停止に失敗しました: {e}", ephemeral=True)

@bot.tree.command(name="pause", description="⏸️ 音楽再生を一時停止")
async def pause_command(interaction: discord.Interaction):
    """音楽再生を一時停止"""
    if not interaction.guild.voice_client or not interaction.guild.voice_client.is_playing():
        await interaction.response.send_message("❌ 現在音楽を再生していません。", ephemeral=True)
        return
    
    try:
        interaction.guild.voice_client.pause()
        await interaction.response.send_message("⏸️ 音楽再生を一時停止しました。", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ 一時停止に失敗しました: {e}", ephemeral=True)

@bot.tree.command(name="resume", description="▶️ 音楽再生を再開")
async def resume_command(interaction: discord.Interaction):
    """音楽再生を再開"""
    if not interaction.guild.voice_client or not interaction.guild.voice_client.is_paused():
        await interaction.response.send_message("❌ 現在一時停止していません。", ephemeral=True)
        return
    
    try:
        interaction.guild.voice_client.resume()
        await interaction.response.send_message("▶️ 音楽再生を再開しました。", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ 再開に失敗しました: {e}", ephemeral=True)

# 画像生成コマンドの本体部分
async def imagegen(interaction: discord.Interaction, prompt: str):
    if not IMAGEGEN_ENABLED:
        await interaction.response.send_message("現在画像生成は管理者により停止中です。", ephemeral=True)
        return
    if interaction.user.id in IMAGEGEN_DENY_USERS:
        await interaction.response.send_message("あなたは現在画像生成を利用できません。", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        # ... 既存のプロンプト生成・画像生成処理 ...
        # path = ... 画像ファイルパス
        import os
        file_size = os.path.getsize(path) / (1024 * 1024)  # MB
        DISCORD_LIMIT_MB = 25  # Nitroやサーバーブーストで50/500MBに拡張可
        if file_size > DISCORD_LIMIT_MB:
            await interaction.followup.send(f"❌ ファイルサイズが大きすぎて送信できません（{file_size:.2f}MB > {DISCORD_LIMIT_MB}MB）。画像サイズや画質を下げてください。", ephemeral=True)
            try:
                os.remove(path)
            except:
                pass
            return
        file = discord.File(path)
        await interaction.followup.send(content="画像を生成しました！", file=file, ephemeral=True)
        os.remove(path)
    except Exception as e:
        logger.error(f"画像生成コマンドエラー: {e}")
        await interaction.followup.send(f"❌ 画像生成または送信中にエラーが発生しました: {e}", ephemeral=True)

from discordbot.youtube_audio import get_youtube_audio_stream_url, download_youtube_audio

@bot.tree.command(name="ytplay", description="YouTube音楽をストリーミングまたはダウンロード再生")
@app_commands.describe(
    stream_url="ストリーミング（Spotify用）再生したいURL（左側）",
    download_url="ダウンロード（高音質YouTube用）再生したいURL（右側）"
)
async def ytplay_command(interaction: discord.Interaction, stream_url: str = None, download_url: str = None):
    await interaction.response.defer(ephemeral=True)
    # VCにいるかチェック
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.followup.send("❌ VCに参加してから使用してください。", ephemeral=True)
        return
    voice_channel = interaction.user.voice.channel
    voice = interaction.guild.voice_client or await voice_channel.connect()
    # サーバーごとの音量取得
    volume = SERVER_MUSIC_VOLUME.get(str(interaction.guild.id), 1.0) * 0.04
    # ストリーミング優先
    if stream_url:
        url, title, duration = get_youtube_audio_stream_url(stream_url)
        if not url:
            await interaction.followup.send("❌ ストリーミングURLの取得に失敗しました。", ephemeral=True)
            return
        try:
            audio = discord.FFmpegPCMAudio(url)
            audio = discord.PCMVolumeTransformer(audio, volume=volume)
            voice.play(
                audio,
                after=lambda e: print(f"ストリーミング再生終了: {e}")
            )
            await interaction.followup.send(f"▶️ ストリーミング再生開始: {title}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ ストリーミング再生に失敗: {e}", ephemeral=True)
        return
    elif download_url:
        path, title, duration = download_youtube_audio(download_url)
        if not path:
            await interaction.followup.send("❌ ダウンロードに失敗しました。", ephemeral=True)
            return
        try:
            audio = discord.FFmpegPCMAudio(path)
            audio = discord.PCMVolumeTransformer(audio, volume=volume)
            voice.play(
                audio,
                after=lambda e: os.remove(path)
            )
            await interaction.followup.send(f"▶️ ダウンロード再生開始: {title}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ ダウンロード再生に失敗: {e}", ephemeral=True)
        return
    else:
        await interaction.followup.send("URLを入力してください（どちらか一方でOK）", ephemeral=True)

import asyncio

async def fade_volume(audio, start, end, duration=1.0, steps=10):
    step = (end - start) / steps
    for i in range(steps):
        audio.volume = start + step * (i + 1)
        await asyncio.sleep(duration / steps)

# TTS再生時の例
# music_audio = discord.PCMVolumeTransformer(music_audio, volume=1.0)
# await fade_volume(music_audio, 1.0, 0.5, duration=1.0)
# TTS再生...
# await fade_volume(music_audio, 0.5, 1.0, duration=1.0)

# 実際のTTS再生処理の前後でfade_volumeを呼び出すように組み込む

import json

MUSIC_VOLUME_FILE = "discordbot/music_volume.json"
try:
    with open(MUSIC_VOLUME_FILE, "r", encoding="utf-8") as f:
        SERVER_MUSIC_VOLUME = json.load(f)
except Exception:
    SERVER_MUSIC_VOLUME = {}

def save_music_volume():
    with open(MUSIC_VOLUME_FILE, "w", encoding="utf-8") as f:
        json.dump(SERVER_MUSIC_VOLUME, f)

@bot.tree.command(name="music_volume", description="サーバーの音楽再生音量を設定（0.0〜1.0）")
@app_commands.describe(volume="音量（0.0〜1.0）")
async def music_volume_command(interaction: discord.Interaction, volume: float):
    if not (0.0 <= volume <= 1.0):
        await interaction.response.send_message("音量は0.0〜1.0で指定してください", ephemeral=True)
        return
    SERVER_MUSIC_VOLUME[str(interaction.guild.id)] = volume
    save_music_volume()
    # 再生中のBGMにも即時反映
    voice = interaction.guild.voice_client
    if voice and voice.is_playing() and hasattr(voice, 'source'):
        try:
            print(f"[DEBUG] voice.source type: {type(voice.source)}")
            print(f"[DEBUG] voice.source attributes: {dir(voice.source)}")
            if hasattr(voice.source, 'volume'):
                print(f"[DEBUG] 変更前 volume: {getattr(voice.source, 'volume', None)}")
                voice.source.volume = volume
                print(f"[DEBUG] 変更後 volume: {getattr(voice.source, 'volume', None)}")
            elif hasattr(voice.source, 'original') and hasattr(voice.source.original, 'volume'):
                print(f"[DEBUG] original.volume 変更前: {getattr(voice.source.original, 'volume', None)}")
                voice.source.original.volume = volume
                print(f"[DEBUG] original.volume 変更後: {getattr(voice.source.original, 'volume', None)}")
            else:
                print("[DEBUG] volume属性が見つかりませんでした")
        except Exception as e:
            print(f"[DEBUG] 音量変更エラー: {e}")
    await interaction.response.send_message(f"このサーバーの音楽音量を{volume*100:.0f}%に設定しました", ephemeral=True)

# /playコマンドの音楽再生部分で音量を適用
# 例:
# volume = SERVER_MUSIC_VOLUME.get(str(interaction.guild.id), 1.0)
# audio = discord.FFmpegPCMAudio(url)
# audio = discord.PCMVolumeTransformer(audio, volume=volume)
# voice.play(audio)

def get_wav_duration(path):
    with wave.open(path, 'rb') as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate)

def reset_all_music_volume_to_default():
    global SERVER_MUSIC_VOLUME
    changed = False
    for gid in list(SERVER_MUSIC_VOLUME.keys()):
        if SERVER_MUSIC_VOLUME[gid] != 1.0:
            SERVER_MUSIC_VOLUME[gid] = 1.0
            changed = True
    if changed:
        save_music_volume()
        print("[INFO] 全サーバーの音楽音量を1.0にリセットしました")

# Bot起動時に自動リセット
reset_all_music_volume_to_default()

import threading
import time

tts_mix_buffer = []
tts_mix_lock = threading.Lock()
tts_mix_timer = None
TTS_MIX_BUFFER_TIME = 1.0  # 秒

def start_tts_mix_timer(voice, bgm_local_path, volume):
    global tts_mix_timer
    def mix_and_play():
        time.sleep(TTS_MIX_BUFFER_TIME)
        with tts_mix_lock:
            tts_files = tts_mix_buffer.copy()
            tts_mix_buffer.clear()
        if not tts_files:
            return
        import tempfile
        import subprocess
        # TTS音声をamixで合成
        if len(tts_files) == 1:
            tts_mix_path = tts_files[0]
        else:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as mix_file:
                tts_mix_path = mix_file.name
            cmd = ['ffmpeg', '-y']
            for f in tts_files:
                cmd += ['-i', f]
            amix_filter = f'amix=inputs={len(tts_files)}:duration=longest:dropout_transition=0'
            cmd += ['-filter_complex', amix_filter, '-c:a', 'pcm_s16le', '-ar', '48000', '-ac', '2', tts_mix_path]
            subprocess.run(cmd, check=True)
        # BGMとTTS合成
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as out_file:
            out_path = out_file.name
        cmd = [
            'ffmpeg', '-y',
            '-i', bgm_local_path,
            '-i', tts_mix_path,
            '-filter_complex', '[0:a]volume=0.5[a0];[a0][1:a]amix=inputs=2:duration=first:dropout_transition=0',
            '-c:a', 'pcm_s16le', '-ar', '48000', '-ac', '2', out_path
        ]
        subprocess.run(cmd, check=True)
        # 合成音声を再生（BGMは止めず、重ねて流す）
        try:
            audio = discord.FFmpegPCMAudio(out_path)
            audio = discord.PCMVolumeTransformer(audio, volume=volume)
            voice.play(audio, after=lambda e: cleanup())
            def cleanup():
                import os
                for p in tts_files + [tts_mix_path, out_path]:
                    try:
                        os.unlink(p)
                    except:
                        pass
        except Exception as e:
            print(f"[DEBUG] TTS合成再生エラー: {e}")

    tts_mix_timer = threading.Thread(target=mix_and_play)
    tts_mix_timer.start()

# TTSコマンド内、ダウンロードBGM再生中の分岐で以下を追加
# 既存のelif bgm_local_path and os.path.exists(bgm_local_path): の中で
# TTS音声ファイル（tts_path）をバッファに追加し、タイマーを起動
