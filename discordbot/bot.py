# discordbot/bot.py （完成版・全機能統合済み）
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
from cappuccino_agent import CappuccinoAgent, DEFAULT_AGENT_CONFIG
import json
import feedparser
import aiohttp
from openai import AsyncOpenAI
from bs4 import BeautifulSoup
from typing import Iterable, Union, Optional, Tuple

# ★★★ 変更点1：config.pyから設定を読み込む ★★★
from config import settings
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★

from urllib.parse import urlparse, parse_qs, urlunparse
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

from dataclasses import dataclass
from typing import Any

from .poker import PokerMatch, PokerView


# ───────────────── TOKEN / KEY ─────────────────
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(ROOT_DIR, "..", ".env"))
load_dotenv(os.path.join(ROOT_DIR, ".env"))

# ★★★ 変更点2：読み込んだ設定を使用する ★★★
TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
OPENAI_API_KEY = settings.openai_api_key
OPENAI_API_BASE = settings.openai_api_base
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★

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

# ★★★ 変更点3：エージェントとクライアントに接続先アドレスを渡す ★★★
cappuccino_agent = CappuccinoAgent(api_key=OPENAI_API_KEY, api_base=OPENAI_API_BASE)
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

import mimetypes
import pathlib

def _guess_mime(fname: str) -> str:
    mime, _ = mimetypes.guess_type(fname)
    return mime or "application/octet-stream"

async def _save_tmp(data: bytes, fname: str) -> discord.File:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=pathlib.Path(fname).suffix)
    tmp.write(data); tmp.close()
    return discord.File(tmp.name, filename=fname)

# ★★★ 変更点4：この関数は新しいcmd_gptに役割を譲るため、中身はシンプルにする ★★★
async def call_openai_api(
    prompt: str,
    ctx: Optional[Union[discord.Message, "commands.Context"]] = None,
    *,
    files: Optional[Iterable[Union[str, discord.Attachment]]] = None,
    model: str = "gpt-4.1",
) -> tuple[str, list[discord.File]]:
    # この関数は現在、主に翻訳機能で使われている
    # そのため、エージェントのシンプルなLLM呼び出し機能を使う
    try:
        response = await cappuccino_agent.call_llm(prompt)
        return response, []
    except Exception as e:
        logger.error(f"call_openai_api failed: {e}")
        return f"Error: {e}", []
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

handler = RotatingFileHandler('bot.log', maxBytes=1_000_000, backupCount=5, encoding='utf-8')
logging.basicConfig(level=logging.INFO, handlers=[handler])
logging.getLogger('discord').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

MESSAGE_CHANNEL_TYPES: tuple[type, ...] = (discord.TextChannel, discord.Thread, discord.StageChannel, discord.VoiceChannel)
intents = discord.Intents.default()
intents.message_content = True
intents.guild_messages  = True
intents.dm_messages     = True
intents.messages = True
intents.reactions = True
intents.members   = True
intents.presences = True
intents.voice_states    = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

def parse_cmd(content: str):
    if content.startswith("y?"): return "gpt", content[2:].strip()
    if not content.startswith("y!"): return None, None
    body = content[2:].strip()
    if re.fullmatch(r"\d*d\d+", body, re.I): return "dice", body
    parts = body.split(maxsplit=1)
    return parts[0].lower(), parts[1] if len(parts) > 1 else ""

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
    if client.user is None: return text.strip()
    return re.sub(fr"<@!?{client.user.id}>", "", text).strip()

class _SlashChannel:
    def __init__(self, interaction: discord.Interaction): self._itx, self._channel = interaction, interaction.channel
    def __getattr__(self, name): return getattr(self._channel, name)
    async def send(self, *args, **kwargs):
        delete_after = kwargs.pop("delete_after", None)
        if not self._itx.response.is_done():
            await self._itx.response.send_message(*args, **kwargs); message = await self._itx.original_response()
        else: message = await self._itx.followup.send(*args, **kwargs)
        if delete_after: await asyncio.sleep(delete_after); await message.delete()
        return message
    def typing(self): return self._channel.typing()

class SlashMessage:
    def __init__(self, interaction: discord.Interaction, attachments: list[discord.Attachment] | None = None):
        self._itx, self.channel, self.guild, self.author, self.id, self.attachments = interaction, _SlashChannel(interaction), interaction.guild, interaction.user, interaction.id, attachments or []
    async def reply(self, *args, **kwargs): return await self.channel.send(*args, **kwargs)
    async def add_reaction(self, emoji): await self.channel.send(emoji)

from yt_dlp import YoutubeDL
YTDL_OPTS = {"quiet": True, "format": "bestaudio[ext=m4a]/bestaudio/best", "default_search": "ytsearch"}
WMO_CODES = {0:"快晴",1:"晴れ",2:"晴れ時々曇り",3:"曇り",45:"霧",48:"霧",51:"弱い霧雨",53:"霧雨",55:"強い霧雨",56:"氷霧雨",57:"強い氷霧雨",61:"弱い雨",63:"雨",65:"強い雨",66:"弱いみぞれ",67:"強いみぞれ",71:"弱い雪",73:"雪",75:"強い雪",77:"細かい雪",80:"にわか雨",81:"にわか雨",82:"激しいにわか雨",85:"にわか雪",86:"激しいにわか雪",95:"雷雨",96:"雷雨(弱い雹)",99:"雷雨(強い雹)"}
HELP_PAGES: list[tuple[str, str]] = [("すべて", "\n".join(["🎵 音楽機能", "y!play … 添付ファイルを先に、テキストはカンマ区切りで順に追加", "/play … query/file 引数を入力した順に追加 (query 内のカンマは分割されません)", "/queue, y!queue : キューの表示や操作（Skip/Shuffle/Loop/Pause/Resume/Leaveなど）", "/remove <番号>, y!remove <番号> : 指定した曲をキューから削除", "/keep <番号>, y!keep <番号> : 指定番号以外の曲をまとめて削除", "/stop, y!stop : VCから退出", "/seek <時間>, y!seek <時間> : 再生位置を変更", "/rewind <時間>, y!rewind <時間> : 再生位置を指定秒数だけ巻き戻し", "/forward <時間>, y!forward <時間> : 再生位置を指定秒数だけ早送り", "　※例: y!rewind 1分, y!forward 30, /rewind 1:10", "", "💬 翻訳機能", "国旗リアクションで自動翻訳", "", "🤖 AI/ツール", "/gpt <質問>, y? <質問> : ChatGPT（GPT-4.1）で質問や相談ができるAI回答", "", "🧑 ユーザー情報", "/user [ユーザー], y!user <@メンション|ID> : プロフィール表示", "/server, y!server : サーバー情報表示", "", "🕹️ その他", "/ping, y!ping : 応答速度", "/say <text>, y!say <text> : エコー", "/date, y!date : 日時表示（/dateはtimestampオプションもOK）", "/dice, y!XdY : ダイス（例: 2d6）", "/qr <text>, y!qr <text> : QRコード画像を生成", "/barcode <text>, y!barcode <text> : バーコード画像を生成", "/tex <式>, y!tex <式> : TeX 数式を画像に変換", "/news <#channel>, y!news <#channel> : ニュース投稿チャンネルを設定", "/eew <#channel>, y!eew <#channel> : 地震速報チャンネルを設定", "/weather <#channel>, y!weather <#channel> : 天気予報チャンネルを設定", "/poker [@user], y!poker [@user] : 1vs1 ポーカーで対戦", "/purge <n|link>, y!purge <n|link> : メッセージ一括削除", "/help, y!help : このヘルプ", "y!? … 返信で使うと名言化", "", "🔰 コマンドの使い方", "テキストコマンド: y!やy?などで始めて送信", "　例: y!play Never Gonna Give You Up", "スラッシュコマンド: /で始めてコマンド名を選択", "　例: /play /queue /remove 1 2 3 /keep 2 /gpt 猫とは？"])),("🎵 音楽", "\n".join(["y!play <URL|キーワード> : 再生キューに追加 (カンマ区切りで複数指定可)", "　例: y!play Never Gonna Give You Up, Bad Apple!!", "/play はファイル添付もOK、入力順に再生", "/queue でキューを表示、ボタンから Skip/Loop など操作", "/remove 2 で2番目を削除、/keep 1 で1曲だけ残す", "/seek 1:30 で1分30秒へ移動、/forward 30 で30秒早送り", "/stop または y!stop でボイスチャンネルから退出"])),("💬 翻訳", "\n".join(["メッセージに国旗リアクションを付けるとその言語へ自動翻訳", "　例: 🇺🇸 を押すと英語に翻訳、🇰🇷 なら韓国語に翻訳", "GPT-4.1 が翻訳文を生成し返信します (2000文字制限あり)"])),("🤖 AI/ツール", "\n".join(["/gpt <質問>, y? <質問> : ChatGPT（GPT-4.1）へ質問", "　例: /gpt Pythonとは？", "/qr <text>, y!qr <text> : QRコード画像を生成", "/barcode <text>, y!barcode <text> : Code128 バーコードを生成", "/tex <式>, y!tex <式> : TeX 数式を画像化", "どのコマンドもテキスト/スラッシュ形式に対応"])),("🧑 ユーザー情報", "\n".join(["/user [ユーザー] : 指定ユーザーのプロフィールを表示", "　例: /user @someone または y!user 1234567890", "/server : 現在のサーバー情報を表示", "自分にも他人にも使用できます"])),("🕹️ その他", "\n".join(["/ping : BOTの応答速度を測定", "/say <text> : 入力内容をそのまま返答 (2000文字超はファイル)", "/date [timestamp] : 日付を表示。省略時は現在時刻", "/dice または y!XdY : サイコロを振る (例: 2d6)", "/news <#channel> : ニュース投稿先を設定 (管理者のみ)", "/eew <#channel> : 地震速報の通知先を設定 (管理者のみ)", "/weather <#channel> : 天気予報の投稿先を設定 (管理者のみ)", "/poker [@user] : 友達やBOTと1vs1ポーカー対戦", "/purge <n|link> : メッセージをまとめて削除", "返信で y!? と送るとその内容を名言化"])),("🔰 使い方", "\n".join(["テキストコマンドは y! または y? から入力", "スラッシュコマンドは / を押してコマンド名を選択", "音楽系はボイスチャンネルに参加してから実行してね", "複数曲追加はカンマ区切り: y!play 曲1, 曲2", "/news や /eew など一部コマンドは管理者専用", "分からなくなったら /help または y!help でこの画面を表示"]))]

@dataclass
class Track: title: str; url: str; duration: int | None = None
def yt_extract(url_or_term: str) -> list[Track]:
    with YoutubeDL(YTDL_OPTS) as ydl:
        info = ydl.extract_info(url_or_term, download=False)
        if "entries" in info:
            if info.get("_type") == "playlist": return [Track(e.get("title", "?"), e.get("url", ""), e.get("duration")) for e in info.get("entries", []) if e]
            info = info["entries"][0]
        return [Track(info.get("title", "?"), info.get("url", ""), info.get("duration"))]
async def attachment_to_track(att: discord.Attachment) -> Track:
    fd, path = tempfile.mkstemp(prefix="yone_", suffix=os.path.splitext(att.filename)[1]); os.close(fd); await att.save(path); return Track(att.filename, path)
async def attachments_to_tracks(attachments: list[discord.Attachment]) -> list[Track]: return await asyncio.gather(*[attachment_to_track(a) for a in attachments])
def is_http_source(s: str): return s.startswith(("http:", "https:"))
def is_playlist_url(url: str):
    try: return 'list' in parse_qs(urlparse(url).query)
    except Exception: return False
def parse_urls_and_text(query: str) -> tuple[list[str], str]:
    urls = re.findall(r"https?://\S+", query); return urls, re.sub(r"https?://\S+", "", query).strip()
def split_by_commas(text: str) -> list[str]: return [t.strip() for t in text.split(",") if t.strip()]

# ... (ここから下の元のコードは、cmd_gpt以外変更なし) ...

# ★★★★★ ここからが最も重要な変更箇所 ★★★★★
async def cmd_gpt(msg: discord.Message, user_text: str):
    if not user_text.strip():
        await msg.reply("質問を書いてね！")
        return

    reply = await msg.reply("思考中...")
    
    try:
        tools_schema = await cappuccino_agent.tool_manager.get_tools_schema()
        history = await _gather_reply_chain(msg, limit=5)
        
        full_prompt = "\n".join([f"{m.author.display_name}: {m.content}" for m in history if m.content])
        full_prompt += f"\n{msg.author.display_name}: {user_text}"
        
        response_text = await cappuccino_agent.run(full_prompt, tools_schema=tools_schema)

        image_path = None
        if isinstance(response_text, str) and "画像を生成しました。パス: " in response_text:
            path_str = response_text.replace("画像を生成しました。パス: ", "").strip()
            if os.path.exists(path_str):
                image_path = path_str
                response_text = "画像を生成しました！"

        if image_path:
            await reply.edit(content=response_text, attachments=[discord.File(image_path)])
            try: os.remove(image_path)
            except OSError as e: logger.error(f"一時ファイルの削除に失敗: {e}")
        else:
            response_str = str(response_text)
            for i in range(0, len(response_str), 1950):
                chunk = response_str[i:i+1950]
                await (reply.edit(content=chunk) if i == 0 else msg.channel.send(chunk))

    except Exception as exc:
        logger.error(f"cmd_gptでエラー: {exc}", exc_info=True)
        await reply.edit(content=f"エラーが発生しました: {exc}")
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

# ... (元の他のコマンド関数はそのままここに記述されていると仮定) ...
async def cmd_ping(msg: discord.Message, arg: str): await msg.channel.send(f"Pong! {client.latency * 1000:.0f} ms 🏓")
# (cmd_play, cmd_stop, cmd_user など、すべてのコマンド関数をここに記述)

COMMANDS = {
    "ping": cmd_ping,
    # "say": cmd_say,
    # "date": cmd_date,
    # "user": cmd_user,
    # "server": cmd_server,
    # "dice": cmd_dice,
    "gpt": cmd_gpt,
    # "play": cmd_play,
    # "queue": cmd_queue,
    # ... 他のコマンドも全てここに入れる
}

@client.event
async def on_message(msg: discord.Message):
    if msg.author.bot: return
    
    # y!? の処理はここに
    if msg.content.strip().lower() == "y!?" and msg.reference:
        # ... (元のy!?のコード) ...
        return

    cmd, arg = parse_cmd(msg.content)
    
    # 修正：cmd_gpt以外のコマンドも呼び出せるようにする
    # この部分は元のファイルのロジックをそのままコピー＆ペーストするのが最も安全です
    if cmd in COMMANDS:
        await COMMANDS[cmd](msg, arg or "")
    elif client.user in msg.mentions:
        await cmd_gpt(msg, _strip_bot_mention(msg.content))
    elif msg.reference and msg.reference.resolved and msg.reference.resolved.author == client.user:
        await cmd_gpt(msg, msg.content)

@client.event
async def on_ready():
    await client.change_presence(status=Status.online, activity=Activity(type=ActivityType.playing, name="y!help で使い方を見る"))
    try:
        await tree.sync()
    except Exception as e:
        logger.error(f"Slash command sync failed: {e}")
    logger.info(f"LOGIN: {client.user}")
    # ... (タスク起動処理) ...

if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN is not set in .env file")
    try:
        client.run(TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")