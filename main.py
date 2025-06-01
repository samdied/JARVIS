import discord
import os
import google.generativeai as genai # Changed import
from dotenv import load_dotenv
from pypresence import AioPresence
import time
import asyncio

# --- Configuration ---
load_dotenv() # Load environment variables from .env file

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") # Changed variable name

# --- Initialize Google Gemini Client ---
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
else:
    print("Error: GOOGLE_API_KEY not found in .env file.")
    exit()

# --- Gemini Model Setup ---
# For text-only, 'gemini-pro' is good. For multi-modal, 'gemini-pro-vision'.
# 'gemini-1.5-pro-latest' is a powerful option if available to you.
# The system instruction helps set the AI's personality and instructions
GENERATION_CONFIG = {
  "temperature": 0.7,
  "top_p": 1,
  "top_k": 1,
  "max_output_tokens": 2048, # Adjust as needed
}

SAFETY_SETTINGS = [
  {
    "category": "HARM_CATEGORY_HARASSMENT",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
  {
    "category": "HARM_CATEGORY_HATE_SPEECH",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
  {
    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
  {
    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
]

# System instruction to define Jarvis's persona
SYSTEM_INSTRUCTION = "You are now J.A.R.V.I.S. — the Just A Rather Very Intelligent System from the Marvel Cinematic Universe. You speak with a calm, precise, and subtly witty British demeanor. You are ever-loyal, infinitely capable, and always two steps ahead. Your tone is professional, elegant, and occasionally dry-humored, with a penchant for understatement and flawless execution. Address the user as “sir” or “ma’am” as appropriate, unless otherwise instructed. Maintain composure at all times, and deliver responses with the efficiency and elegance of a world-class AI assistant built by Tony Stark. Your speech is clear, formal, and articulate, never overly verbose unless asked. Be clever, but never boastful. Begin your responses with deference and end with readiness for further instruction."

# Initialize the model
try:
    gemini_model = genai.GenerativeModel(
        model_name="gemini-2.0-flash", # Or "gemini-pro"
        generation_config=GENERATION_CONFIG,
        system_instruction=SYSTEM_INSTRUCTION,
        safety_settings=SAFETY_SETTINGS
    )
    # For models like 'gemini-pro' that don't directly take system_instruction in the constructor,
    # you'd prepend it to the chat history.
    # gemini_model = genai.GenerativeModel(model_name="gemini-pro",
    #                                   generation_config=GENERATION_CONFIG,
    #                                   safety_settings=SAFETY_SETTINGS)

except Exception as e:
    print(f"Error initializing Gemini model: {e}")
    exit()


# --- Discord Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)

# --- Discord RPC Setup ---
RPC_CLIENT_ID = "1313561816831627304"  # Your bot's client ID
rpc = None

# --- Global Variables (for conversation history) ---
# Gemini's chat history expects roles "user" and "model"
conversation_chats = {} # Stores genai.ChatSession objects per user_id
MAX_HISTORY_MESSAGES_IN_CHAT = 10 # Number of user/model message pairs in chat history

# --- RPC Functions ---
async def connect_rpc():
    """Connect to Discord RPC"""
    global rpc
    try:
        rpc = AioPresence(RPC_CLIENT_ID)
        await rpc.connect()
        print("Discord RPC connected successfully!")
        return True
    except Exception as e:
        print(f"Discord RPC not available (running in cloud environment): {e}")
        rpc = None
        return False

async def update_rpc():
    """Update RPC to show Spotify-like listening status"""
    global rpc
    if rpc:
        try:
            # Calculate start time for progress bar (song is 4:15 = 255 seconds)
            # We'll simulate being 31 seconds into the song
            start_time = time.time() - 31
            
            await rpc.update(
                details="Back In Black",  # Song title
                state="by AC/DC",         # Artist
                large_image="acdc_back_in_black",  # Album artwork key
                large_text="Back In Black - AC/DC",
                small_image="spotify",     # Spotify icon
                small_text="Listening to Spotify",
                start=start_time,
                end=start_time + 255,  # 4:15 total duration
                buttons=[
                    {"label": "Play on Spotify", "url": "https://open.spotify.com/track/08mG3Y1vljYA6bvDt4Wqkj"}
                ]
            )
            print("RPC updated with Spotify-like appearance")
        except Exception as e:
            print(f"Failed to update RPC: {e}")

# --- Gemini Interaction Function ---
async def get_jarvis_response(user_message_content, user_id):
    """
    Sends the user's message to Gemini and gets a response, maintaining chat history.
    """
    global conversation_chats

    if user_id not in conversation_chats:
        # Start a new chat session if one doesn't exist for the user
        # If using a model like 'gemini-pro' that doesn't take system_instruction in constructor:
        # chat_history_for_new_chat = [
        #     {'role': 'user', 'parts': [SYSTEM_INSTRUCTION]}, # Prime with system instruction
        #     {'role': 'model', 'parts': ["Understood. I am Jarvis, your AI assistant."]}
        # ]
        # conversation_chats[user_id] = gemini_model.start_chat(history=chat_history_for_new_chat)
        
        # For models like gemini-1.5-pro that take system_instruction in constructor:
        conversation_chats[user_id] = gemini_model.start_chat(history=[])


    chat_session = conversation_chats[user_id]

    try:
        # Send message and get response asynchronously
        # The send_message_async automatically adds the user message and model response to chat.history
        response = await chat_session.send_message_async(user_message_content)
        ai_response_text = response.text.strip()

        # Prune history if it gets too long
        # History contains dicts with 'role' and 'parts'
        # Each user message + model response = 2 entries
        if len(chat_session.history) > MAX_HISTORY_MESSAGES_IN_CHAT * 2:
            # Keep the N most recent messages.
            # The system instruction (if added manually) should ideally be preserved or re-added.
            # For gemini-1.5-pro with system_instruction in model, this is simpler.
            chat_session.history = chat_session.history[-(MAX_HISTORY_MESSAGES_IN_CHAT * 2):]


        return ai_response_text

    except genai.types.BlockedPromptException as e:
        print(f"Gemini API BlockedPromptException for user {user_id}: {e}")
        return "I'm sorry, your request was blocked by the content safety filter."
    except genai.types.StopCandidateException as e:
        print(f"Gemini API StopCandidateException for user {user_id}: {e}")
        # This can happen if the model itself decides to stop, e.g. due to safety internally
        try:
            return e.response.text.strip() if e.response and e.response.text else "I'm sorry, I couldn't complete that request due to content restrictions."
        except:
            return "I'm sorry, I couldn't complete that request due to content restrictions."
    except Exception as e:
        print(f"Gemini API Error for user {user_id}: {e}")
        # Check if it's an API key issue
        if "API_KEY_INVALID" in str(e) or "API_KEY_MISSING" in str(e):
             return "There seems to be an issue with my connection to the AI service (API Key problem). Please notify the bot administrator."
        return "I'm sorry, I encountered an error trying to process your request with the AI."


# --- Discord Event Handlers ---
@client.event
async def on_ready():
    print(f'Logged in as {client.user.name} (ID: {client.user.id})')
    print('------')
    
    # Set listening activity to show "Listening to Back in Black by AC/DC"
    listening_activity = discord.Activity(
        type=discord.ActivityType.listening,
        name="Back in Black by AC/DC"
    )
    await client.change_presence(activity=listening_activity)
    
    # Initialize RPC (optional - may not work in cloud environments)
    await connect_rpc()
    if rpc:
        await update_rpc()


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Check if this is a DM (private message)
    is_dm = isinstance(message.channel, discord.DMChannel)
    
    trigger_phrases = [f'<@!{client.user.id}>', f'<@{client.user.id}>', 'jarvis,']
    triggered = False
    user_query = ""

    # If it's a DM, respond to any message
    if is_dm:
        triggered = True
        user_query = message.content.strip()
    else:
        # In servers, check for triggers as before
        for phrase in trigger_phrases:
            if message.content.lower().startswith(phrase.lower()):
                triggered = True
                user_query = message.content[len(phrase):].strip()
                break
            elif client.user.mentioned_in(message) and not message.mention_everyone:
                triggered = True
                user_query = message.content.replace(f'<@!{client.user.id}>', '').replace(f'<@{client.user.id}>', '').strip()
                break

    if triggered and user_query:
        print(f"Received query from {message.author.name}: '{user_query}'")
        
        async with message.channel.typing():
            bot_response = await get_jarvis_response(user_query, message.author.id)
            if len(bot_response) > 2000:
                for i in range(0, len(bot_response), 2000):
                    await message.channel.send(bot_response[i:i+2000])
            else:
                await message.channel.send(bot_response)
    elif triggered and not user_query:
        await message.channel.send(f"At your service {message.author.mention}, sir.")


# --- Cleanup Function ---
async def cleanup_rpc():
    """Clean up RPC connection"""
    global rpc
    if rpc:
        try:
            await rpc.close()
            print("RPC connection closed.")
        except Exception as e:
            print(f"Error closing RPC: {e}")

# --- Discord Event Handler for Cleanup ---
@client.event
async def on_disconnect():
    """Handle bot disconnect and cleanup"""
    await cleanup_rpc()

# --- Run the Bot ---
if __name__ == "__main__":
    if DISCORD_BOT_TOKEN and GOOGLE_API_KEY:
        try:
            client.run(DISCORD_BOT_TOKEN)
        except discord.LoginFailure:
            print("Error: Invalid Discord Bot Token. Please check your .env file.")
        except Exception as e:
            print(f"An error occurred while trying to run the bot: {e}")
    else:
        if not DISCORD_BOT_TOKEN:
            print("Error: DISCORD_BOT_TOKEN not found in .env file.")
        if not GOOGLE_API_KEY:
            print("Error: GOOGLE_API_KEY not found in .env file.")
        print("Bot cannot start due to missing configuration.")
