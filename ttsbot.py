import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
import asyncio
import requests
import json
VOICEVOX_URL = "http://localhost:50021"

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

joined_text_channels = {}

import os
TTS_USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_users.json")
TTS_CHANNELS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_channels.json")
TTS_JOIN_CHANNELS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_join_channels.json")
CHARACTER_SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "character_settings.json")
TTS_SPEED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_speed.json")

def _load_tts_users() -> set[int]:
    try:
        with open(TTS_USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("users", []))
    except FileNotFoundError:
        return set()
    except Exception as e:
        print(f"TTSユーザー読み込み失敗: {e}")
        return set()

def _save_tts_users(users: set[int]) -> None:
    try:
        with open(TTS_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump({"users": list(users)}, f)
    except Exception as e:
        print(f"TTSユーザー保存失敗: {e}")

def _load_tts_channels() -> set[int]:
    try:
        with open(TTS_CHANNELS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("channels", []))
    except FileNotFoundError:
        return set()
    except Exception as e:
        print(f"TTSチャンネル読み込み失敗: {e}")
        return set()

def _save_tts_channels(channels: set[int]) -> None:
    try:
        with open(TTS_CHANNELS_FILE, "w", encoding="utf-8") as f:
            json.dump({"channels": list(channels)}, f)
    except Exception as e:
        print(f"TTSチャンネル保存失敗: {e}")

def _load_character_settings() -> dict[int, str]:
    try:
        with open(CHARACTER_SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {int(k): v for k, v in data.get("users", {}).items()}
    except Exception:
        return {}

def _save_character_settings(settings: dict[int, str]) -> None:
    try:
        with open(CHARACTER_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump({"users": {str(k): v for k, v in settings.items()}}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"キャラクター設定保存失敗: {e}")

def _load_tts_speed() -> dict[int, float]:
    try:
        with open(TTS_SPEED_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {int(k): float(v) for k, v in data.get("users", {}).items()}
    except Exception:
        return {}

def _save_tts_speed(settings: dict[int, float]) -> None:
    try:
        with open(TTS_SPEED_FILE, "w", encoding="utf-8") as f:
            json.dump({"users": {str(k): v for k, v in settings.items()}}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"TTS速度設定保存失敗: {e}")

tts_users = _load_tts_users()
tts_channels = _load_tts_channels()
character_settings = _load_character_settings()
tts_speed_settings = _load_tts_speed()

import re

last_message_author = {}

def sync_cleanup(path):
    import os, time
    try:
        time.sleep(0.5)
        os.remove(path)
    except Exception as e:
        print(f"ファイル削除エラー: {e}")

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return
    guild_id = message.guild.id
    user_id = message.author.id  # ここで必ず定義
    if guild_id in joined_text_channels:
        text_channel_id, voice = joined_text_channels[guild_id]
        if message.channel.id == text_channel_id:
            try:
                # テキストをクリーンアップ
                clean_text = message.content
                clean_text = re.sub(r'https?://\S+', '', clean_text)
                clean_text = re.sub(r'<@!?\d+>', '', clean_text)
                clean_text = re.sub(r'<a?:.+?:\d+>', '', clean_text)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                if clean_text and len(clean_text) > 1:
                    cache_key = f"{message.guild.id}_{message.channel.id}"
                    if cache_key in last_message_author and last_message_author[cache_key] == message.author.id:
                        zunda_text = clean_text
                    else:
                        character = character_settings.get(user_id, "ずんだもん")
                        zunda_text = f"{message.author.display_name}さん。{clean_text}"
                        last_message_author[cache_key] = message.author.id
                    wav_bytes = await generate_zunda_voice(zunda_text, user_id=user_id)
                    if not wav_bytes:
                        return
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                        tmp_file.write(wav_bytes)
                        tts_path = tmp_file.name
                    # VC未接続なら自動で参加
                    if not voice or not voice.is_connected():
                        vc_channel = message.guild.get_member(bot.user.id).voice.channel if message.guild.get_member(bot.user.id) and message.guild.get_member(bot.user.id).voice else None
                        if not vc_channel:
                            # /joinで記憶したVCに再接続
                            vc_channel = message.guild.voice_client.channel if message.guild.voice_client else None
                        if not vc_channel:
                            # どこにもいなければ何もしない
                            return
                        voice = await vc_channel.connect()
                        joined_text_channels[guild_id] = (text_channel_id, voice)
                    if not voice.is_playing():
                        voice.play(
                            discord.FFmpegPCMAudio(tts_path, options='-vn -ar 48000 -ac 2 -b:a 64k -bufsize 16k'),
                            after=lambda e: sync_cleanup(tts_path)
                        )
            except Exception as e:
                print(f"TTS自動読み上げエラー: {e}")
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"TTS Bot起動: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"スラッシュコマンド同期完了: {len(synced)}件")
    except Exception as e:
        print(f"コマンド同期エラー: {e}")

async def generate_zunda_voice(text: str, user_id: int = None) -> bytes | None:
    """VOICEVOXを使用してずんだもんの声を生成（高速化）"""
    try:
        speaker_id = 1
        speed = tts_speed_settings.get(user_id, 1.0) if user_id else 1.0
        synthesis_response = requests.post(
            f"{VOICEVOX_URL}/audio_query",
            params={"text": text, "speaker": speaker_id},
            headers={"Content-Type": "application/json"},
            timeout=3
        )
        if synthesis_response.status_code != 200:
            print(f"VOICEVOX音声合成失敗: {synthesis_response.status_code}")
            return None
        audio_query = synthesis_response.json()
        audio_query["speedScale"] = speed
        audio_response = requests.post(
            f"{VOICEVOX_URL}/synthesis",
            params={"speaker": speaker_id},
            data=json.dumps(audio_query),
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if audio_response.status_code != 200:
            print(f"VOICEVOX音声生成失敗: {audio_response.status_code}")
            return None
        return audio_response.content
    except Exception as e:
        print(f"VOICEVOX音声生成エラー: {e}")
        return None

@bot.tree.command(name="join", description="VCにBotを参加させてこのチャンネルのメッセージを自動読み上げ（VOICEVOX）")
async def join_command(interaction: discord.Interaction):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("❌ VCに参加してから使ってね", ephemeral=True)
        return
    channel = interaction.user.voice.channel
    text_channel = interaction.channel
    if interaction.guild.voice_client and interaction.guild.voice_client.is_connected():
        voice = interaction.guild.voice_client
    else:
        voice = await channel.connect()
    # このテキストチャンネルIDとVCを記憶
    joined_text_channels[interaction.guild.id] = (text_channel.id, voice)
    await interaction.response.send_message(f"✅ {channel.name} に参加＆このチャンネルのメッセージを自動読み上げします！", ephemeral=True)

@bot.tree.command(name="tts_on", description="このチャンネル/自分のTTS自動読み上げを有効にする")
async def tts_on_command(interaction: discord.Interaction):
    user_id = interaction.user.id
    channel_id = interaction.channel.id
    tts_users.add(user_id)
    tts_channels.add(channel_id)
    _save_tts_users(tts_users)
    _save_tts_channels(tts_channels)
    await interaction.response.send_message("✅ このチャンネル/自分のTTS自動読み上げを有効にしました", ephemeral=True)

@bot.tree.command(name="tts_off", description="このチャンネル/自分のTTS自動読み上げを無効にする")
async def tts_off_command(interaction: discord.Interaction):
    user_id = interaction.user.id
    channel_id = interaction.channel.id
    tts_users.discard(user_id)
    tts_channels.discard(channel_id)
    _save_tts_users(tts_users)
    _save_tts_channels(tts_channels)
    await interaction.response.send_message("✅ このチャンネル/自分のTTS自動読み上げを無効にしました", ephemeral=True)

@bot.tree.command(name="tts_character", description="自分のTTSキャラクターを設定")
async def tts_character_command(interaction: discord.Interaction, character: str):
    user_id = interaction.user.id
    character_settings[user_id] = character
    _save_character_settings(character_settings)
    await interaction.response.send_message(f"✅ あなたのTTSキャラクターを『{character}』に設定しました", ephemeral=True)

@bot.tree.command(name="tts_speed", description="自分のTTS読み上げ速度を設定（0.5〜2.0）")
async def tts_speed_command(interaction: discord.Interaction, speed: float):
    if not (0.5 <= speed <= 2.0):
        await interaction.response.send_message("❌ 速度は0.5〜2.0で指定してください", ephemeral=True)
        return
    user_id = interaction.user.id
    tts_speed_settings[user_id] = speed
    _save_tts_speed(tts_speed_settings)
    await interaction.response.send_message(f"✅ あなたのTTS速度を{speed}に設定しました", ephemeral=True)

@bot.tree.command(name="help", description="利用可能なスラッシュコマンド一覧を表示")
async def help_command(interaction: discord.Interaction):
    cmds = [
        f"/{cmd.name} - {cmd.description}" for cmd in bot.tree.get_commands()
    ]
    help_text = "\n".join(cmds)
    await interaction.response.send_message(f"**利用可能なコマンド一覧**\n{help_text}\n\n例: /tts_speed 1.2 で自分の読み上げ速度を変更できます", ephemeral=True)

bot.run(TOKEN) 