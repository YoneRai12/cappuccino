import os
import asyncio
import discord
from discord.ext import commands

# Botの設定
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user}")
    print("🎤 TTS機能テスト用Botが起動しました")

@bot.command(name="test")
async def test_command(ctx):
    """テストコマンド"""
    await ctx.send("🎤 TTS機能テスト用Botが正常に動作しています！")

@bot.command(name="join")
async def join_command(ctx):
    """VCに参加するテストコマンド"""
    if not ctx.author.voice:
        await ctx.send("❌ VCに参加してから使用してください")
        return
    
    try:
        voice_channel = ctx.author.voice.channel
        voice = await voice_channel.connect()
        await ctx.send(f"🎤 {voice_channel.name} に接続しました！")
    except Exception as e:
        await ctx.send(f"❌ 接続に失敗しました: {e}")

@bot.command(name="leave")
async def leave_command(ctx):
    """VCから退出するテストコマンド"""
    if ctx.guild.voice_client:
        await ctx.guild.voice_client.disconnect()
        await ctx.send("🎤 VCから退出しました")
    else:
        await ctx.send("❌ VCに接続していません")

async def main():
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("❌ DISCORD_BOT_TOKEN環境変数が設定されていません")
        print("以下のコマンドで設定してください：")
        print('$env:DISCORD_BOT_TOKEN="your_bot_token_here"')
        raise SystemExit(1)

    print("Discord Botを起動中...")
    await bot.start(token)

if __name__ == "__main__":
    # Windowsでasyncioのイベントループポリシーを設定
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main()) 