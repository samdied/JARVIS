import discord
import os
import google.generativeai as genai # Changed import
from dotenv import load_dotenv
from pypresence import Presence
import time
import asyncio

# --- Configuration ---
load_dotenv() # Load environment variables from .env file

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") # Changed variable name

# --- Discord RPC Configuration ---
RPC_CONFIG = {
    "client_id": "1313561816831627304",
    "enabled": True,
    "image": "ACDC.png",  # Single image for all statuses
    "update_interval": 15  # seconds
}

rpc = None
start_time = time.time()

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

# --- Global Variables (for conversation history) ---
# Gemini's chat history expects roles "user" and "model"
conversation_chats = {} # Stores genai.ChatSession objects per user_id
MAX_HISTORY_MESSAGES_IN_CHAT = 10 # Number of user/model message pairs in chat history

# --- RPC Variables ---
total_queries_handled = 0
last_query_user = None

# --- RPC Functions ---
def init_rpc():
    """Initialize Discord Rich Presence"""
    global rpc
    if not RPC_CONFIG["enabled"]:
        return False
        
    try:
        rpc = Presence(RPC_CONFIG["client_id"])
        rpc.connect()
        update_rpc_status("Initializing", "Starting up systems...")
        print("Discord RPC connected successfully")
        return True
    except Exception as e:
        print(f"Failed to connect to Discord RPC: {e}")
        return False

def update_rpc_status(state, details):
    """Update Discord Rich Presence status"""
    global rpc, start_time
    
    if not rpc or not RPC_CONFIG["enabled"]:
        return
        
    try:
        rpc.update(
            state=state,
            details=details,
            start=start_time,
            large_image=RPC_CONFIG["image"],
            large_text="J.A.R.V.I.S. - Just A Rather Very Intelligent System",
            buttons=[
                {"label": "Add to Server", "url": f"https://discord.com/api/oauth2/authorize?client_id={RPC_CONFIG['client_id']}&permissions=2048&scope=bot"},
                {"label": "Support", "url": "https://discord.gg/replit"}
            ]
        )
    except Exception as e:
        print(f"Failed to update RPC: {e}")

async def rpc_update_loop():
    """Background task to update RPC periodically"""
    while True:
        try:
            if last_query_user:
                update_rpc_status(
                    f"Assisting {last_query_user}",
                    f"Handled {total_queries_handled} queries total"
                )
            else:
                update_rpc_status(
                    "Awaiting Instructions",
                    f"Ready to assist • {total_queries_handled} queries handled"
                )
        except Exception as e:
            print(f"RPC update loop error: {e}")
        
        await asyncio.sleep(RPC_CONFIG["update_interval"])

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
    
    # Initialize Discord RPC
    if init_rpc():
        # Start RPC update loop
        client.loop.create_task(rpc_update_loop())
    
    # Set initial Discord presence
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Back in Black"))


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
        global total_queries_handled, last_query_user
        
        print(f"Received query from {message.author.name}: '{user_query}'")
        
        # Update RPC tracking variables
        total_queries_handled += 1
        last_query_user = message.author.name
        
        # Update RPC status to show processing
        update_rpc_status(
            f"Processing for {message.author.name}",
            f"Analyzing query • {total_queries_handled} total queries"
        )
        
        async with message.channel.typing():
            bot_response = await get_jarvis_response(user_query, message.author.id)
            if len(bot_response) > 2000:
                for i in range(0, len(bot_response), 2000):
                    await message.channel.send(bot_response[i:i+2000])
            else:
                await message.channel.send(bot_response)
        
        # Update RPC status after completing response
        update_rpc_status(
            f"Completed query for {message.author.name}",
            f"Response delivered • {total_queries_handled} queries handled"
        )
    elif triggered and not user_query:
        await message.channel.send(f"At your service {message.author.mention}, sir.")


# --- Run the Bot ---
if __name__ == "__main__":
    if DISCORD_BOT_TOKEN and GOOGLE_API_KEY:
        try:
            client.run(DISCORD_BOT_TOKEN)
        except discord.LoginFailure:
            print("Error: Invalid Discord Bot Token. Please check your .env file.")
        except Exception as e:
            print(f"An error occurred while trying to run the bot: {e}")
        finally:
            # Clean up RPC connection
            if rpc:
                try:
                    rpc.close()
                    print("Discord RPC connection closed")
                except:
                    pass
    else:
        if not DISCORD_BOT_TOKEN:
            print("Error: DISCORD_BOT_TOKEN not found in .env file.")
        if not GOOGLE_API_KEY:
            print("Error: GOOGLE_API_KEY not found in .env file.")
        print("Bot cannot start due to missing configuration.")
