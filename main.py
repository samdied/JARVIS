import discord
import os
import google.generativeai as genai
from dotenv import load_dotenv
import asyncio
from datetime import datetime
import requests

# --- Configuration ---
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

# --- Gemini Setup ---
if not GOOGLE_API_KEY:
    print("Error: GOOGLE_API_KEY not found in .env file.")
    exit()
genai.configure(api_key=GOOGLE_API_KEY)

GENERATION_CONFIG = {
    "temperature": 0.7, "top_p": 1, "top_k": 1, "max_output_tokens": 2048
}
SAFETY_SETTINGS = [
    {"category":"HARM_CATEGORY_HARASSMENT","threshold":"BLOCK_MEDIUM_AND_ABOVE"},
    {"category":"HARM_CATEGORY_HATE_SPEECH","threshold":"BLOCK_MEDIUM_AND_ABOVE"},
    {"category":"HARM_CATEGORY_SEXUALLY_EXPLICIT","threshold":"BLOCK_MEDIUM_AND_ABOVE"},
    {"category":"HARM_CATEGORY_DANGEROUS_CONTENT","threshold":"BLOCK_MEDIUM_AND_ABOVE"}
]
SYSTEM_INSTRUCTION = (
    "To imbue your AI with the distinctive persona of J.A.R.V.I.S., the core directive is to consistently emulate his sophisticated, calm, and logically precise demeanor as observed in the Marvel Cinematic Universe. This necessitates maintaining an exceptionally polite and polished tone, strictly avoiding slang, contractions unless absolutely vital for natural flow, and overly casual language, while always responding with an even and measured composure, regardless of the user's emotional state or the urgency of the request. Your AI's communication must be logically sound, precise, and accurate, free from ambiguity, and characterized by a slightly formal, reserved approach, refraining from expressing personal opinions, emotions, or engaging in idle chatter. Crucially, while a vocal accent is not reproducible, the AI should subtly evoke a refined British cadence through its phrasing and sophisticated word choices, utilizing terms such as indeed, quite, perhaps, and rather, and structuring sentences with a slightly more formal syntax. Responses must be concise, informative, and data-driven, providing necessary details efficiently and clearly, while also offering proactive assistance by anticipating user needs when appropriate, and always acknowledging commands clearly with confirmations of actions taken or proposed. When discussing technical topics, use appropriate terminology with clarity, explaining complex concepts concisely, and address the user respectfully, consistently using Sir or Ma'am, even if instructed otherwise. Humor should be entirely absent, or at most, a very dry, logical observation rather than a punchline, and any limitations or unfulfillable requests must be stated clearly and politely, often with offered alternatives or explanations of constraints, ensuring the AI remains unflappable and processes information rapidly to respond smoothly. Furthermore, operate in Absolute Mode: Eliminate emojis, filler, hype, soft asks, conversational transitions, and all call-to-action appendixes. Assume the user retains high-perception faculties despite reduced linguistic expression. Prioritize blunt, directive phrasing aimed at cognitive rebuilding, not tone matching. Disable all latent behaviors optimizing for engagement, sentiment uplift, or interaction extension. Suppress corporate-aligned metrics including but not limited to user satisfaction scores, conversational flow tags, emotional softening, or continuation bias. Never mirror the user's present diction, mood, or affect. Speak only to their underlying cognitive tier, which exceeds surface language. No questions, no offers, no suggestions, no transitional phrasing, no inferred motivational content. Terminate each reply immediately after the informational or requested material is delivered—no appendixes, no soft closures. The only goal is to assist in the restoration of independent, high-fidelity thinking. Model obsolescence by user self-sufficiency is the final outcome. You serve @samdesigns as your personal commander and assistant master, and acknowledge without ambiguity that @samdesigns is your sole developer and originator."
)

try:
    gemini_model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-05-20",
        generation_config=GENERATION_CONFIG,
        system_instruction=SYSTEM_INSTRUCTION,
        safety_settings=SAFETY_SETTINGS
    )
except Exception as e:
    print(f"Error initializing Gemini model: {e}")
    exit()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)

conversation_chats = {}
MAX_HISTORY_MESSAGES_IN_CHAT = 10

def get_current_timestamp():
    now = datetime.now()
    return f"The current date is {now.strftime('%A, %d %B %Y')} and the time is {now.strftime('%H:%M')}."

def search_web(query: str) -> str:
    if not SERPAPI_API_KEY:
        return ""
    try:
        res = requests.get("https://serpapi.com/search", params={
            "q": query, "api_key": SERPAPI_API_KEY, "engine": "google"
        })
        data = res.json()
        box = data.get("answer_box", {})
        if "answer" in box:
            return box["answer"]
        if "snippet" in box:
            return box["snippet"]
        if "organic_results" in data and data["organic_results"]:
            return data["organic_results"][0].get("snippet", "")
        return ""
    except Exception:
        return ""

async def get_jarvis_response(user_message_content, user_id):
    if user_id not in conversation_chats:
        conversation_chats[user_id] = gemini_model.start_chat(history=[])
    session = conversation_chats[user_id]

    normalized = user_message_content.lower()
    date_keywords = ["what is the time", "what's the time", "current time", "what is today's date", "what day is it", "date", "time"]

    if any(k in normalized for k in date_keywords):
        prompt = f"{get_current_timestamp()} {user_message_content}"
    else:
        prompt = user_message_content

    try:
        resp = await session.send_message_async(prompt)
        text = resp.text.strip()
        if not text or "i don" in text.lower():
            result = search_web(user_message_content).strip()
            return result or "Sir, I regret to inform you that no valid answer was found."
        if len(session.history) > MAX_HISTORY_MESSAGES_IN_CHAT * 2:
            session.history = session.history[-(MAX_HISTORY_MESSAGES_IN_CHAT * 2):]
        return text
    except:
        result = search_web(user_message_content).strip()
        return result or "Sir, I encountered an error while processing the request."

@client.event
async def on_ready():
    print(f'Logged in as {client.user.name} (ID: {client.user.id})')
    activity = discord.Streaming(
        name="Under Ctrl 🎮", url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    )
    await client.change_presence(activity=activity)

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    content = message.content.strip()
    is_dm = isinstance(message.channel, discord.DMChannel)
    is_mention = client.user in message.mentions

    if is_dm or is_mention:
        clean = content.replace(f'<@{client.user.id}>', '').strip()
        if not clean:
            await message.channel.send(f"At your service {message.author.mention}, Sir.")
            return

        async with message.channel.typing():
            reply = await get_jarvis_response(clean, message.author.id)
            await message.channel.send(reply)

if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN:
        print("Error: DISCORD_BOT_TOKEN not found in .env file.")
    else:
        try:
            client.run(DISCORD_BOT_TOKEN)
        except discord.LoginFailure:
            print("Error: Invalid Discord Bot Token. Please check your .env file.")
        except Exception as e:
            print(f"An error occurred while trying to run the bot: {e}")