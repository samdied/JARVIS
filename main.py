import discord
import os
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import datetime, timezone
import asyncio

# --- Configuration ---
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

genai.configure(api_key=GOOGLE_API_KEY)

gemini_model = genai.GenerativeModel(
    model_name="gemini-2.5-flash-preview-05-20",
    generation_config={"temperature": 0.7, "top_p": 1, "top_k": 1, "max_output_tokens": 2048},
    system_instruction="To imbue your AI with the distinctive persona of J.A.R.V.I.S., the core directive is to consistently emulate his sophisticated, calm, and logically precise demeanor as observed in the Marvel Cinematic Universe. ...",  # use your full Absolute Mode instruction here
    safety_settings=[
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]
)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
conversation_chats = {}
MAX_HISTORY = 10

def is_time_query(msg):
    q = msg.lower()
    return any(k in q for k in [
        "what is the time", "what's the time", "current time",
        "what time is it", "time in", "what date is it", "today's date",
        "date in", "day", "time now", "what day is it"
    ])

def get_utc_datetime_prompt(query):
    now_utc = datetime.now(timezone.utc)
    utc_str = now_utc.strftime("%A, %d %B %Y, %H:%M")
    return (
        f"Sir, the current date and time in UTC is {utc_str}. "
        f"Please calculate the local date and time for the following request: \"{query}\". "
        f"Respond in a structured, analytical tone appropriate for a formal AI assistant."
    )

async def get_gemini_response(prompt, uid):
    if uid not in conversation_chats:
        conversation_chats[uid] = gemini_model.start_chat(history=[])
    chat = conversation_chats[uid]
    try:
        response = await chat.send_message_async(prompt)
        return response.text.strip()
    except:
        return "Sir, I encountered a problem processing the temporal conversion."

@client.event
async def on_ready():
    print(f"Logged in as {client.user.name}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    content = message.content.strip()
    is_dm = isinstance(message.channel, discord.DMChannel)
    mentioned = client.user in message.mentions

    if not (is_dm or mentioned):
        return

    prompt = content.replace(f'<@{client.user.id}>', '').strip()
    if not prompt:
        await message.channel.send(f"At your service {message.author.mention}, Sir.")
        return

    if is_time_query(prompt):
        prep = get_utc_datetime_prompt(prompt)
        async with message.channel.typing():
            reply = await get_gemini_response(prep, message.author.id)
            await message.channel.send(reply)
        return

    async with message.channel.typing():
        response = await get_gemini_response(prompt, message.author.id)
        await message.channel.send(response)

if __name__ == "__main__":
    if DISCORD_BOT_TOKEN:
        client.run(DISCORD_BOT_TOKEN)
    else:
        print("Missing DISCORD_BOT_TOKEN.")