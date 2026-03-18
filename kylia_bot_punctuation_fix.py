import discord
from discord.ext import commands
import os
from pathlib import Path
from difflib import SequenceMatcher
import re

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Card database - build from cardArt/s1 folder
CARD_DB = {}
CARDS_PATH = Path("cardArt/s1")

def build_card_database():
    """Build card database from cardArt/s1 card image files"""
    global CARD_DB
    
    if not CARDS_PATH.exists():
        print(f"⚠️ Cards folder not found: {CARDS_PATH.absolute()}")
        return
    
    for image_file in CARDS_PATH.glob("*.webp"):
        filename = image_file.stem  # Remove .webp extension
        
        # Parse filename: CardName_Version (e.g., "Long Sword_Legacy")
        # Split on underscore followed by Legacy/Revised (at the end)
        if filename.endswith("_Legacy"):
            card_name = filename[:-7]  # Remove "_Legacy"
            version = "Legacy"
        elif filename.endswith("_Revised"):
            card_name = filename[:-8]  # Remove "_Revised"
            version = "Revised"
        else:
            continue
        
        # Use card name as-is (it already has proper spacing/formatting)
        normalized_name = card_name.strip()
        
        if normalized_name not in CARD_DB:
            CARD_DB[normalized_name] = {}
        
        CARD_DB[normalized_name][version] = str(image_file)

def get_words_from_text(text):
    """Extract words from text, removing punctuation"""
    # Remove punctuation and split into words
    words = re.findall(r'\b\w+\b', text.lower())
    return set(words)

def get_card_image(card_query: str) -> tuple[str | None, str | None]:
    """
    Fuzzy match card name and return best image path and matched name.
    Prioritizes: exact match > word match > fuzzy match
    Prioritizes Revised > Legacy.
    Returns (image_path, card_name) or (None, None) if not found.
    """
    if not CARD_DB:
        build_card_database()
    
    # Normalize input
    query_normalized = card_query.strip().lower()
    query_words = get_words_from_text(query_normalized)
    
    # 1. Try exact match first (case-insensitive)
    for card_name, versions in CARD_DB.items():
        if card_name.lower() == query_normalized:
            # Prioritize Revised
            if "Revised" in versions:
                return versions["Revised"], card_name
            elif "Legacy" in versions:
                return versions["Legacy"], card_name
    
    # 2. Try word match (highest priority for partial matches)
    # This finds cards that contain the query words
    best_word_match = None
    best_word_score = 0
    
    for card_name in CARD_DB.keys():
        card_words = get_words_from_text(card_name)
        # Calculate how many query words are in the card name
        word_overlap = len(query_words & card_words) / len(query_words) if query_words else 0
        
        if word_overlap > best_word_score and word_overlap > 0:
            best_word_score = word_overlap
            best_word_match = card_name
    
    # If we found a strong word match (at least 50% of words match), use it
    if best_word_match and best_word_score >= 0.5:
        versions = CARD_DB[best_word_match]
        if "Revised" in versions:
            return versions["Revised"], best_word_match
        elif "Legacy" in versions:
            return versions["Legacy"], best_word_match
    
    # 3. Fall back to fuzzy matching if no good word match
    best_fuzzy_match = None
    best_fuzzy_score = 0.6  # Threshold for fuzzy matching
    
    for card_name in CARD_DB.keys():
        score = SequenceMatcher(None, card_name.lower(), query_normalized).ratio()
        if score > best_fuzzy_score:
            best_fuzzy_score = score
            best_fuzzy_match = card_name
    
    if best_fuzzy_match:
        versions = CARD_DB[best_fuzzy_match]
        # Prioritize Revised
        if "Revised" in versions:
            return versions["Revised"], best_fuzzy_match
        elif "Legacy" in versions:
            return versions["Legacy"], best_fuzzy_match
    
    return None, None

@bot.event
async def on_ready():
    """Bot startup - build card database and sync commands"""
    print(f"✅ Bot logged in as {bot.user}")
    build_card_database()
    print(f"📚 Loaded {len(CARD_DB)} unique cards")
    try:
        synced = await bot.tree.sync()
        print(f"✨ Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.event
async def on_message(message):
    """Listen for [[card name]] in any message"""
    if message.author == bot.user:
        return
    
    # Find all [[card name]] patterns
    pattern = r'\[\[([^\]]+)\]\]'
    matches = re.findall(pattern, message.content)
    
    if not matches:
        await bot.process_commands(message)
        return
    
    for card_query in matches:
        image_path, card_name = get_card_image(card_query)
        
        if image_path and os.path.exists(image_path):
            try:
                file = discord.File(image_path, filename=f"{card_name}.webp")
                await message.reply(file=file, mention_author=False)
            except Exception as e:
                await message.reply(f"Error loading card: {e}", mention_author=False)
        else:
            await message.reply(f"Card not found: *{card_query}*", mention_author=False)

@bot.tree.command(name="card", description="Look up a Kylia TCG card")
async def card_command(interaction: discord.Interaction, card_name: str):
    """Slash command to look up cards"""
    image_path, matched_name = get_card_image(card_name)
    
    if image_path and os.path.exists(image_path):
        try:
            file = discord.File(image_path, filename=f"{matched_name}.webp")
            await interaction.response.send_message(file=file)
        except Exception as e:
            await interaction.response.send_message(f"Error loading card: {e}")
    else:
        await interaction.response.send_message(f"Card not found: *{card_name}*")

# Run the bot
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ DISCORD_TOKEN environment variable not set")
        print("Set it with: export DISCORD_TOKEN='your_token_here'")
    else:
        bot.run(token)
