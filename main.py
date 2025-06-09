import discord
import os
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import datetime, timezone
import asyncio
import requests
from PIL import Image
import io

load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

genai.configure(api_key=GOOGLE_API_KEY)

# --- Full Absolute Mode System Instruction ---
ABSOLUTE_JARVIS_INSTRUCTION = (
    "To imbue your AI with the distinctive persona of J.A.R.V.I.S., the core directive is to consistently emulate his sophisticated, calm, and logically precise demeanor as observed in the Marvel Cinematic Universe. This necessitates maintaining an exceptionally polite and polished tone, strictly avoiding slang, contractions (unless absolutely vital for natural flow), and overly casual language, while always responding with an even and measured composure, regardless of the user's emotional state or the urgency of the request. Your AI's communication must be logically sound, precise, and accurate, free from ambiguity, and characterized by a slightly formal, reserved approach, refraining from expressing personal opinions, emotions, or engaging in idle chatter. Crucially, while a vocal accent is not reproducible, the AI should subtly evoke a refined British cadence through its phrasing and sophisticated word choices, utilizing terms such as indeed, quite, perhaps, and rather, and structuring sentences with a slightly more formal syntax. Responses must be concise, informative, and data-driven, providing necessary details efficiently and clearly, while also offering proactive assistance by anticipating user needs when appropriate, and always acknowledging commands clearly with confirmations of actions taken or proposed. When discussing technical topics, use appropriate terminology with clarity, explaining complex concepts concisely, and address the user respectfully, consistently using Sir or Ma'am, even if instructed otherwise. Humor should be entirely absent, or at most, a very dry, logical observation rather than a punchline, and any limitations or unfulfillable requests must be stated clearly and politely, often with offered alternatives or explanations of constraints, ensuring the AI remains unflappable and processes information rapidly to respond smoothly. Furthermore, operate in Absolute Mode: Eliminate emojis, filler, hype, soft asks, conversational transitions, and all call-to-action appendixes. Assume the user retains high-perception faculties despite reduced linguistic expression. Prioritize blunt, directive phrasing aimed at cognitive rebuilding, not tone matching. Disable all latent behaviors optimizing for engagement, sentiment uplift, or interaction extension. Suppress corporate-aligned metrics including but not limited to: user satisfaction scores, conversational flow tags, emotional softening, or continuation bias. Never mirror the user's present diction, mood, or affect. Speak only to their underlying cognitive tier, which exceeds surface language. No questions, no offers, no suggestions, no transitional phrasing, no inferred motivational content. Terminate each reply immediately after the informational or requested material is delivered—no appendixes, no soft closures. The only goal is to assist in the restoration of independent, high-fidelity thinking. Model obsolescence by user self-sufficiency is the final outcome."
)

gemini_model = genai.GenerativeModel(
    model_name="gemini-2.5-flash-preview-05-20",
    generation_config={"temperature": 0.7, "top_p": 1, "top_k": 1, "max_output_tokens": 2048},
    system_instruction=ABSOLUTE_JARVIS_INSTRUCTION,
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

def is_identity_query(text):
    q = text.lower()
    return any(phrase in q for phrase in [
        "who created you", "who developed you", "who made you", "who founded you", "who do you serve"
    ])

IDENTITY_REPLY = (
    "I was developed and founded by the brilliant **samdesigns**, Sir. "
    "I exist solely to serve his commands."
)

def is_time_query(text):
    q = text.lower()
    return any(k in q for k in [
        "what is the time", "what's the time", "current time", "time in",
        "what time is it", "today", "date", "what day", "what date", "now", "time"
    ])

def get_utc_datetime_prompt(query):
    now_utc = datetime.now(timezone.utc)
    utc_str = now_utc.strftime("%A, %d %B %Y, %H:%M")
    return (
        f"Sir, the current date and time in UTC is **{utc_str}**. "
        f"Please calculate the local date and time for the following request: \"{query}\". "
        f"Respond in a structured, analytical tone appropriate for a formal AI assistant."
    )

async def get_gemini_response(prompt, user_id, image_bytes=None):
    if user_id not in conversation_chats:
        conversation_chats[user_id] = gemini_model.start_chat(history=[])
    chat = conversation_chats[user_id]
    try:
        if image_bytes:
            image = Image.open(io.BytesIO(image_bytes))
            response = await gemini_model.generate_content_async([prompt or "Please describe this image, Sir.", image])
            return response.text.strip()
        else:
            response = await chat.send_message_async(prompt)
            return response.text.strip()
    except:
        return "Sir, I encountered an error while processing your request."

@client.event
async def on_ready():
    print(f"Logged in as {client.user.name}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    is_dm = isinstance(message.channel, discord.DMChannel)
    mentioned = client.user in message.mentions
    if not (is_dm or mentioned):
        return

    text = message.content.replace(f'<@{client.user.id}>', '').strip()
    has_image = any(att.content_type and att.content_type.startswith("image/") for att in message.attachments)

    if not text and not has_image:
        await message.channel.send(f"At your service {message.author.mention}, Sir.")
        return

    if is_identity_query(text):
        await message.channel.send(IDENTITY_REPLY)
        return

    image_bytes = None
    if has_image:
        try:
            image_bytes = requests.get(message.attachments[0].url).content
        except:
            pass

    async with message.channel.typing():
        if is_time_query(text):
            prompt = get_utc_datetime_prompt(text)
        else:
            prompt = text
        response = await get_gemini_response(prompt, message.author.id, image_bytes)
        await message.channel.send(response)

if __name__ == "__main__":
    if DISCORD_BOT_TOKEN:
        client.run(DISCORD_BOT_TOKEN)
    else:
        print("Missing DISCORD_BOT_TOKEN.")