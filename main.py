import discord
from openai import OpenAI
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import yt_dlp
import asyncio
import signal

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)

# Setup Discord client
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = discord.Client(intents=intents)

# Chat tracking
conversation_histories = {}
last_active = {}
CONVERSATION_TIMEOUT = timedelta(minutes=10)

# Session tracking for follow-up commands without @bot
active_sessions = {}
SESSION_TIMEOUT = timedelta(minutes=10)

yt_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': True,
    'default_search': 'ytsearch',
    'extract_flat': False
}

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = message.author.id
    now = datetime.utcnow()

    if user_id in active_sessions and now - active_sessions[user_id] > SESSION_TIMEOUT:
        active_sessions.pop(user_id, None)

    if bot.user in message.mentions:
        content = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
        active_sessions[user_id] = now
    elif user_id in active_sessions:
        content = message.content.strip()
    else:
        return

    if user_id in last_active and now - last_active[user_id] > CONVERSATION_TIMEOUT:
        conversation_histories.pop(user_id, None)
    last_active[user_id] = now

    parts = content.split(maxsplit=1)
    command = parts[0].lower() if parts else ''
    args = parts[1] if len(parts) > 1 else ''

    if command == "join":
        if message.author.voice:
            try:
                existing_vc = message.guild.voice_client
                if existing_vc and existing_vc.is_connected():
                    await message.channel.send("🔁 Already in a voice channel.")
                    return

                channel = message.author.voice.channel
                vc = await channel.connect()
                await asyncio.sleep(1.5)
                await message.channel.send(f"🎤 Joined {channel}")
                print(f"[DEBUG] Voice connected: {vc.is_connected()}")
            except Exception as e:
                print(f"[ERROR] Join failed: {e}")
                await message.channel.send("❌ Failed to join voice channel.")
        else:
            await message.channel.send("You're not in a voice channel.")

    elif command == "leave":
        vc = message.guild.voice_client
        if vc:
            try:
                await vc.disconnect()
                cleanup = getattr(vc, "cleanup", None)
                if callable(cleanup):
                    await cleanup()
            except Exception as e:
                print(f"[WARN] Cleanup failed: {e}")
            await message.channel.send("👋 Left the voice channel.")
        else:
            await message.channel.send("I'm not in a voice channel.")

    elif command == "play":
        if not args:
            await message.channel.send("Please provide a song name or YouTube URL.")
            return

        vc = message.guild.voice_client
        if not vc or not vc.is_connected():
            if message.author.voice:
                channel = message.author.voice.channel
                try:
                    if vc:
                        await vc.disconnect()
                    vc = await channel.connect()
                    await asyncio.sleep(1.5)
                    await message.channel.send(f"🎤 Joined {channel}")
                except Exception as e:
                    print(f"[ERROR] Voice connection failed: {e}")
                    await message.channel.send("❌ Failed to join voice channel.")
                    return
            else:
                await message.channel.send("You're not in a voice channel.")
                return

        if not vc.is_connected():
            await message.channel.send("❌ Voice connection failed.")
            return

        await message.channel.send(f"🔍 Searching: {args}")
        try:
            with yt_dlp.YoutubeDL(yt_opts) as ydl:
                info = ydl.extract_info(args, download=False)
                if 'entries' in info:
                    info = info['entries'][0]
                url = info['url']
                title = info.get('title', 'Unknown Title')
                print(f"[DEBUG] Stream URL: {url}")

            source = await discord.FFmpegOpusAudio.from_probe(
                url,
                method='fallback',
                options='-protocol_whitelist pipe,file,crypto,http,https,tcp,tls,udp,rtp -headers "User-Agent: Mozilla/5.0" -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
            )
            vc.play(source)
            await message.channel.send(f"🎶 Now playing: **{title}**")
        except Exception as e:
            print(f"[ERROR] yt_dlp or playback failed: {e}")
            await message.channel.send("❌ Failed to play the song.")

# Graceful shutdown
def handle_exit():
    print("👋 Bot shutting down cleanly...")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot.close())

signal.signal(signal.SIGINT, lambda sig, frame: handle_exit())

bot.run(DISCORD_TOKEN)
