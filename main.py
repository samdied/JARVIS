import discord
import os
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import datetime, timezone
import asyncio
import requests
from PIL import Image
import io

# --- Load environment ---
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Gemini Setup ---
genai.configure(api_key=GOOGLE_API_KEY)
gemini_model = genai.GenerativeModel(
    model_name="gemini-2.5-flash-preview-05-20",
    generation_config={"temperature": 0.7, "top_p": 1, "top_k": 1, "max_output_tokens": 2048},
    system_instruction="To imbue your AI with the distinctive persona of J.A.R.V.I.S. ...",  # full instruction here
    safety_settings=[
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]
)

# --- Discord Setup ---
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

conversation_chats = {}
MAX_HISTORY = 10

# --- Time Handler ---
def is_time_query(msg):
    q = msg.lower()
    return any(k in q for k in [
        "what is the time", "what's the time", "current time", "time in",
        "what time is it", "today", "date", "what day", "what date", "now"
    ])

def get_utc_datetime_prompt(query):
    now_utc = datetime.now(timezone.utc)
    utc_str = now_utc.strftime("%A, %d %B %Y, %H:%M")
    return (
        f"Sir, the current date and time in UTC is {utc_str}. "
        f"Please calculate the local date and time for the following request: \"{query}\". "
        f"Respond in a structured, analytical tone appropriate for a formal AI assistant."
    )

# --- Gemini Interaction ---
async def get_gemini_response(prompt, user_id, image_bytes=None):
    if user_id not in conversation_chats:
        conversation_chats[user_id] = gemini_model.start_chat(history=[])
    chat = conversation_chats[user_id]

    try:
        if image_bytes:
            image = Image.open(io.BytesIO(image_bytes))
            result = await gemini_model.generate_content_async([prompt or "Please describe this image, Sir.", image])
            return result.text.strip()
        else:
            result = await chat.send_message_async(prompt)
            return result.text.strip()
    except Exception:
        return "Sir, I encountered an error processing the visual or text input."

# --- Discord Events ---
@client.event
async def on_ready():
    print(f"Logged in as {client.user.name}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    is_dm = isinstance(message.channel, discord.DMChannel)
    mentioned = client.user in message.mentions
    text = message.content.replace(f'<@{client.user.id}>', '').strip()

    has_image = any(att.content_type and att.content_type.startswith("image/") for att in message.attachments)
    image_bytes = None

    if has_image:
        try:
            image_bytes = requests.get(message.attachments[0].url).content
        except:
            pass

    if not (is_dm or mentioned):
        return  # Only respond in DMs or when pinged

    # Empty message
    if not text and not has_image:
        await message.channel.send(f"At your service {message.author.mention}, Sir.")
        return

    async with message.channel.typing():
        if is_time_query(text):
            prompt = get_utc_datetime_prompt(text)
            reply = await get_gemini_response(prompt, message.author.id)
        else:
            reply = await get_gemini_response(text, message.author.id, image_bytes=image_bytes)

        await message.channel.send(reply)

# --- Run Bot ---
if __name__ == "__main__":
    if DISCORD_BOT_TOKEN:
        client.run(DISCORD_BOT_TOKEN)
    else:
        print("Missing DISCORD_BOT_TOKEN.")