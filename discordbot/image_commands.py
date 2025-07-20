import discord
from discord import app_commands
import asyncio
import os
import json
import logging
from image_generator import generate_image, generate_image_with_negative

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

# 画像生成コマンド（一般向け）
async def imagegen(interaction: discord.Interaction, prompt: str):
    if not IMAGEGEN_ENABLED:
        await interaction.response.send_message("現在画像生成は管理者により停止中です。", ephemeral=True)
        return
    if interaction.user.id in IMAGEGEN_DENY_USERS:
        await interaction.response.send_message("あなたは現在画像生成を利用できません。", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        # ここにLLMプロンプト変換・画像生成処理を呼び出す（bot.pyから移植）
        # path = ... 画像ファイルパス
        # 例: path = await asyncio.to_thread(generate_image, prompt, options)
        # ファイルサイズチェック・送信処理も同様
        pass
    except Exception as e:
        logging.error(f"画像生成コマンドエラー: {e}")
        await interaction.followup.send(f"❌ 画像生成または送信中にエラーが発生しました: {e}", ephemeral=True)

# 画像生成コマンド（上級者向け）
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
        options = {"width": 512, "height": 768}
        path = await asyncio.to_thread(generate_image_with_negative, prompt, negative_prompt, options)
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
        logging.error(f"画像生成Heavyコマンドエラー: {e}")
        await interaction.followup.send(f"❌ Heavy画像生成または送信中にエラーが発生しました: {e}", ephemeral=True) 