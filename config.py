import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
BOT_NAME = "rootv1"

# Bot intents
INTENTS = {
    "message_content": True,
    "members": True,
    "moderation": True,
}
