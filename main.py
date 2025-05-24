import discord
import os
import re
import json
import subprocess
from discord.ext import commands
from discord import app_commands
from keep_alive import keep_alive

DISCORD_TOKEN = os.environ['DISCORD_TOKEN']
OPENROUTER_API_KEY = os.environ['OPENAI_API_KEY']
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
REFERER_URL = "https://replit.com/@9937/cowloon-ai-bot"
GUILD_ID = 1375049845940944907
CHANNEL_ID = 1373347765450444870

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree
auto_thread_enabled = False

@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ グローバルコマンドを同期しました")
    print(f"🤖 Bot logged in as {bot.user}")
    print("🟢 bot is alive")

def generate_thread_title(message_content):
    match_review = re.search(r"復習問題集（(第.+?回)）", message_content)
    if match_review:
        return f"{match_review.group(1)} 復習問題 回答送信用"
    match_lesson = re.search(r"第(\d+)回", message_content)
    if match_lesson:
        return f"第{match_lesson.group(1)}回 回答送信用"
    return "回答送信用スレッド"

async def create_thread_with_guide(message, title):
    try:
        thread = await message.create_thread(name=title)
        await thread.send("📝 このスレッドにあなたの回答を送ってください\nBotが自動で添削とフィードバックを行います\n単語のヒントが欲しい場合は /hint コマンドを使ってください\n質問がある場合は /q コマンドを使ってください。")
    except Exception as e:
        print(f"スレッド作成失敗: {e}")

@bot.command(name="createThreads")
async def create_threads_command(ctx):
    await ctx.send("🩵 スレッドの一括作成を開始します...")
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        await ctx.send("❌ 指定されたチャンネル ID が無効です")
        return

    created_count = 0
    async for message in channel.history(limit=200):
        if message.type == discord.MessageType.default and not message.has_thread():
            title = generate_thread_title(message.content)
            try:
                await create_thread_with_guide(message, title)
                created_count += 1
            except Exception as e:
                print(f"⚠ スレッド作成失敗: {e}")

    await ctx.send(f"✅ 完了：{created_count}件のスレッドを作成しました。")

@tree.command(name="q", description="広東語に関する質問ができます")
@app_commands.describe(question="聞きたい内容を入力してください")
async def slash_question(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    prompt = f"あなたは広東語の先生です。以下の質問に日本語でやさしく答えてください。\n\n【質問】\n{question}"
    data = {
        "model": "anthropic/claude-3-haiku",
        "messages": [{"role": "user", "content": prompt}]
    }
    curl_command = [
        "curl", "-s",
        "-X", "POST",
        OPENROUTER_API_URL,
        "-H", f"Authorization: Bearer {OPENROUTER_API_KEY}",
        "-H", "Content-Type: application/json; charset=utf-8",
        "-H", f"HTTP-Referer: {REFERER_URL}",
        "-H", "X-Title: Claude質問Bot",
        "-d", json.dumps(data, ensure_ascii=False)
    ]
    result = subprocess.run(curl_command, capture_output=True, text=True)
    try:
        output = json.loads(result.stdout)
        reply = output["choices"][0]["message"]["content"]
        await interaction.followup.send(f"{interaction.user.mention}\n📘 回答:\n{reply}")
    except Exception as e:
        await interaction.followup.send(f"❌ Claude API エラー: {e}")

@tree.command(name="hint", description="翻訳課題に関するヒントを表示します（答えは出しません）")
async def slash_hint(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        if isinstance(interaction.channel, discord.Thread):
            thread = interaction.channel
            parent = thread.parent
            starter_message = await parent.fetch_message(thread.id)
            lesson_text = starter_message.content.strip()

            prompt = f"""以下は日本人向けの広東語レッスンです。\n\nこのレッスンを読んで、すでに本文で解説されている文法や語彙はヒントから除外してください。\n読者がすでに説明された内容を繰り返し見せられると混乱や煩わしさを感じるためです。\nそのうえで、翻訳問題・作文問題を解くために必要だが、本文では説明されていない語彙・文型・言い回しを厳選して提示してください。\n出力はすべて日本語で、簡潔かつ視認性の高い箇条書きで記述してください。\n\n【レッスン本文】\n{lesson_text}"""

            data = {
                "model": "anthropic/claude-3-haiku",
                "messages": [{"role": "user", "content": prompt}]
            }
            curl_command = [
                "curl", "-s",
                "-X", "POST",
                OPENROUTER_API_URL,
                "-H", f"Authorization: Bearer {OPENROUTER_API_KEY}",
                "-H", "Content-Type: application/json; charset=utf-8",
                "-H", f"HTTP-Referer: {REFERER_URL}",
                "-H", "X-Title: ClaudeヒントBot",
                "-d", json.dumps(data, ensure_ascii=False)
            ]
            result = subprocess.run(curl_command, capture_output=True, text=True)
            output = json.loads(result.stdout)
            reply = output["choices"][0]["message"]["content"]
            await interaction.followup.send(f"{interaction.user.mention}\n📘 ヒント:\n{reply}")
        else:
            await interaction.followup.send("📘 このコマンドはスレッド内でのみ使用できます。")
    except Exception as e:
        await interaction.followup.send(f"❌ Claude API エラー: {e}")

keep_alive()
bot.run(DISCORD_TOKEN)
