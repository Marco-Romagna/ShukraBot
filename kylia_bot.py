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
 
# Card database - build from both S1 and S2 folders
CARD_DB = {}
S1_PATH = Path("cardArt/s1")
S2_PATH = Path("cardArt/s2")
 
def build_card_database():
    """Build card database from S1 and S2 card image files"""
    global CARD_DB
    
    # Load S1 cards
    if S1_PATH.exists():
        for image_file in S1_PATH.glob("*.webp"):
            filename = image_file.stem
            
            if filename.endswith("_Legacy"):
                card_name = filename[:-7]
                version = "Legacy"
            elif filename.endswith("_Revised"):
                card_name = filename[:-8]
                version = "Revised"
            else:
                continue
            
            normalized_name = card_name.strip()
            
            if normalized_name not in CARD_DB:
                CARD_DB[normalized_name] = {"s1": {}, "s2": {}}
            
            CARD_DB[normalized_name]["s1"][version] = str(image_file)
    
    # Load S2 cards
    if S2_PATH.exists():
        for image_file in S2_PATH.glob("*.webp"):
            filename = image_file.stem
            
            if filename.endswith("_Legacy"):
                card_name = filename[:-7]
                version = "Legacy"
            elif filename.endswith("_Revised"):
                card_name = filename[:-8]
                version = "Revised"
            else:
                continue
            
            normalized_name = card_name.strip()
            
            if normalized_name not in CARD_DB:
                CARD_DB[normalized_name] = {"s1": {}, "s2": {}}
            
            CARD_DB[normalized_name]["s2"][version] = str(image_file)
 
def get_words_from_text(text):
    """Extract words from text, removing punctuation"""
    words = re.findall(r'\b\w+\b', text.lower())
    return set(words)
 
def parse_card_query(query: str) -> tuple[str, str | None]:
    """
    Parse card query format: [[card name]] or [[card name | modifier]]
    Returns (card_name, modifier) where modifier is s1, s2, a, b, or None
    """
    if "|" in query:
        parts = query.split("|")
        card_name = parts[0].strip()
        modifier = parts[1].strip().lower()
        return card_name, modifier
    
    return query.strip(), None
 
def get_card_images(card_name: str, modifier: str | None = None) -> list[tuple[str, str]]:
    """
    Get card image path(s) and display names based on card name and modifier.
    Returns list of (image_path, display_label) tuples.
    Modifier: s1, s2, a, b, or None (None = show all available)
    """
    if not CARD_DB:
        build_card_database()
    
    query_normalized = card_name.strip().lower()
    query_words = get_words_from_text(query_normalized)
    
    # 1. Try exact match first
    matched_card = None
    for card_key in CARD_DB.keys():
        if card_key.lower() == query_normalized:
            matched_card = card_key
            break
    
    # 2. Try word match if no exact match
    if not matched_card:
        best_match = None
        best_score = 0
        
        for card_key in CARD_DB.keys():
            card_words = get_words_from_text(card_key)
            word_overlap = len(query_words & card_words) / len(query_words) if query_words else 0
            
            if word_overlap > best_score and word_overlap > 0:
                best_score = word_overlap
                best_match = card_key
        
        if best_match and best_score >= 0.5:
            matched_card = best_match
    
    # 3. Fall back to fuzzy matching
    if not matched_card:
        best_match = None
        best_score = 0.6
        
        for card_key in CARD_DB.keys():
            score = SequenceMatcher(None, card_key.lower(), query_normalized).ratio()
            if score > best_score:
                best_score = score
                best_match = card_key
        
        matched_card = best_match
    
    if not matched_card:
        return []
    
    # Now get the actual images based on modifier
    sets = CARD_DB[matched_card]
    results = []
    
    # Handle A/B modifiers (two-sided cards)
    if modifier and modifier in ['a', 'b']:
        side_letter = modifier.upper()
        # Look for Side A or Side B in card name
        for version in ["Revised", "Legacy"]:
            s2_images = sets.get("s2", {})
            s1_images = sets.get("s1", {})
            
            # Try S2 first, then S1
            if version in s2_images:
                image_path = s2_images[version]
                if f"_{side_letter}_" in image_path or f"_{side_letter}." in image_path:
                    results.append((image_path, f"{matched_card} (Side {side_letter})"))
            
            if version in s1_images and not results:
                image_path = s1_images[version]
                if f"_{side_letter}_" in image_path or f"_{side_letter}." in image_path:
                    results.append((image_path, f"{matched_card} (Side {side_letter})"))
    
    # Handle S1/S2 modifiers
    elif modifier and modifier in ['s1', 's2']:
        set_key = modifier
        set_images = sets.get(set_key, {})
        
        # Prefer Revised > Legacy
        if "Revised" in set_images:
            results.append((set_images["Revised"], f"{matched_card} ({modifier.upper()})"))
        elif "Legacy" in set_images:
            results.append((set_images["Legacy"], f"{matched_card} ({modifier.upper()})"))
    
    # No modifier - show both S1 and S2 if available (for tier 2 cards)
    else:
        has_s1 = bool(sets.get("s1"))
        has_s2 = bool(sets.get("s2"))
        
        # If both exist, show side by side (tier 2 card)
        if has_s1 and has_s2:
            # Get S1 version (Revised preferred)
            s1_images = sets["s1"]
            if "Revised" in s1_images:
                results.append((s1_images["Revised"], f"{matched_card} (Set 1)"))
            elif "Legacy" in s1_images:
                results.append((s1_images["Legacy"], f"{matched_card} (Set 1)"))
            
            # Get S2 version (Revised preferred)
            s2_images = sets["s2"]
            if "Revised" in s2_images:
                results.append((s2_images["Revised"], f"{matched_card} (Set 2)"))
            elif "Legacy" in s2_images:
                results.append((s2_images["Legacy"], f"{matched_card} (Set 2)"))
        
        # If only one set exists, show that
        elif has_s2:
            s2_images = sets["s2"]
            if "Revised" in s2_images:
                results.append((s2_images["Revised"], matched_card))
            elif "Legacy" in s2_images:
                results.append((s2_images["Legacy"], matched_card))
        
        elif has_s1:
            s1_images = sets["s1"]
            if "Revised" in s1_images:
                results.append((s1_images["Revised"], matched_card))
            elif "Legacy" in s1_images:
                results.append((s1_images["Legacy"], matched_card))
    
    return results
 
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
    
    for query in matches:
        card_name, modifier = parse_card_query(query)
        images = get_card_images(card_name, modifier)
        
        if images:
            try:
                # Create embed with all images
                if len(images) == 1:
                    # Single image - just send it
                    image_path, label = images[0]
                    file = discord.File(image_path, filename=f"{label}.webp")
                    await message.reply(file=file, mention_author=False)
                else:
                    # Multiple images - send as separate files in one message
                    files = [discord.File(path, filename=f"{label}.webp") for path, label in images]
                    await message.reply(files=files, mention_author=False)
            except Exception as e:
                await message.reply(f"Error loading card: {e}", mention_author=False)
        else:
            await message.reply(f"Card not found: *{card_name}*", mention_author=False)
 
@bot.tree.command(name="card", description="Look up a Kylia TCG card")
async def card_command(interaction: discord.Interaction, card_name: str, modifier: str | None = None):
    """Slash command to look up cards"""
    images = get_card_images(card_name, modifier)
    
    if images:
        try:
            if len(images) == 1:
                image_path, label = images[0]
                file = discord.File(image_path, filename=f"{label}.webp")
                await interaction.response.send_message(file=file)
            else:
                files = [discord.File(path, filename=f"{label}.webp") for path, label in images]
                await interaction.response.send_message(files=files)
        except Exception as e:
            await interaction.response.send_message(f"Error loading card: {e}")
    else:
        await interaction.response.send_message(f"Card not found: *{card_name}*")
 
@bot.tree.command(name="help", description="Show card bot help")
async def help_command(interaction: discord.Interaction):
    """Help command"""
    embed = discord.Embed(
        title="🎮 Kylia TCG Card Bot Help",
        description="",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="Query cards",
        value="```\n[[Card Name]] - Shows the card image\n```",
        inline=False
    )
    
    embed.add_field(
        name="Specify art version",
        value="```\n[[Card Name | s1]] - Show Set 1 art only\n[[Card Name | s2]] - Show Set 2 art only\n```",
        inline=False
    )
    
    embed.add_field(
        name="Two-sided & Tier 2 cards",
        value="By default, shows both sides/versions side-by-side\n```\n[[Card Name | a]] - Show Side A only\n[[Card Name | b]] - Show Side B only\n```",
        inline=False
    )
    
    embed.add_field(
        name="Fuzzy matching",
        value="Typos are fine! `[[longsword]]` finds \"Long Sword\"",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)
 
# Run the bot
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ DISCORD_TOKEN environment variable not set")
    else:
        bot.run(token)
 
