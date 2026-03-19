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
 
# Card database
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
            
            # Parse version (Legacy/Revised)
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
                CARD_DB[normalized_name] = {"s1": {}, "s2": {}, "s2_tier2": {}, "sides": {}}
            
            CARD_DB[normalized_name]["s1"][version] = str(image_file)
    
    # Load S2 cards
    if S2_PATH.exists():
        for image_file in S2_PATH.glob("*.webp"):
            filename = image_file.stem
            
            # Parse version (Legacy/Revised)
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
                CARD_DB[normalized_name] = {"s1": {}, "s2": {}, "s2_tier2": {}, "sides": {}}
            
            # Check if it's a tier 2 card (ends with _2)
            if normalized_name.endswith("_2"):
                base_name = normalized_name[:-2]
                if base_name not in CARD_DB:
                    CARD_DB[base_name] = {"s1": {}, "s2": {}, "s2_tier2": {}, "sides": {}}
                CARD_DB[base_name]["s2_tier2"][version] = str(image_file)
            # Check if it's a two-sided card (has _A_ or _B_)
            elif "_A_" in normalized_name or normalized_name.endswith("_A"):
                side = "A"
                base_name = normalized_name.replace("_A_", "_").replace("_A", "")
                if base_name not in CARD_DB:
                    CARD_DB[base_name] = {"s1": {}, "s2": {}, "s2_tier2": {}, "sides": {}}
                if "A" not in CARD_DB[base_name]["sides"]:
                    CARD_DB[base_name]["sides"]["A"] = {}
                CARD_DB[base_name]["sides"]["A"][version] = str(image_file)
            elif "_B_" in normalized_name or normalized_name.endswith("_B"):
                side = "B"
                base_name = normalized_name.replace("_B_", "_").replace("_B", "")
                if base_name not in CARD_DB:
                    CARD_DB[base_name] = {"s1": {}, "s2": {}, "s2_tier2": {}, "sides": {}}
                if "B" not in CARD_DB[base_name]["sides"]:
                    CARD_DB[base_name]["sides"]["B"] = {}
                CARD_DB[base_name]["sides"]["B"][version] = str(image_file)
            else:
                # Regular S2 card (genki card with same name as S1)
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
 
def find_card(card_name: str) -> str | None:
    """Find a card in the database by name, word match, or fuzzy match"""
    if not CARD_DB:
        build_card_database()
    
    query_normalized = card_name.strip().lower()
    query_words = get_words_from_text(query_normalized)
    
    # 1. Exact match
    for card_key in CARD_DB.keys():
        if card_key.lower() == query_normalized:
            return card_key
    
    # 2. Word match (at least 50% of words match)
    best_match = None
    best_score = 0
    
    for card_key in CARD_DB.keys():
        card_words = get_words_from_text(card_key)
        if not query_words:
            continue
        word_overlap = len(query_words & card_words) / len(query_words)
        
        if word_overlap > best_score and word_overlap > 0:
            best_score = word_overlap
            best_match = card_key
    
    if best_match and best_score >= 0.5:
        return best_match
    
    # 3. Fuzzy match
    best_match = None
    best_score = 0.6
    
    for card_key in CARD_DB.keys():
        score = SequenceMatcher(None, card_key.lower(), query_normalized).ratio()
        if score > best_score:
            best_score = score
            best_match = card_key
    
    return best_match
 
def get_card_images(card_name: str, modifier: str | None = None) -> list[tuple[str, str]]:
    """
    Get card image path(s) based on card name and modifier.
    Returns list of (image_path, display_label) tuples.
    """
    matched_card = find_card(card_name)
    if not matched_card:
        return []
    
    card_data = CARD_DB[matched_card]
    results = []
    
    # Handle A/B modifiers (two-sided cards)
    if modifier and modifier in ['a', 'b']:
        side = modifier.upper()
        if side in card_data["sides"]:
            side_images = card_data["sides"][side]
            # Prefer Revised > Legacy
            if "Revised" in side_images:
                results.append((side_images["Revised"], f"{matched_card} (Side {side})"))
            elif "Legacy" in side_images:
                results.append((side_images["Legacy"], f"{matched_card} (Side {side})"))
    
    # Handle S1/S2 modifiers
    elif modifier == "s1":
        if card_data["s1"]:
            s1_images = card_data["s1"]
            if "Revised" in s1_images:
                results.append((s1_images["Revised"], f"{matched_card} (Set 1)"))
            elif "Legacy" in s1_images:
                results.append((s1_images["Legacy"], f"{matched_card} (Set 1)"))
    
    elif modifier == "s2":
        # For tier 2 cards, s2 means tier 2
        if card_data["s2_tier2"]:
            s2t2_images = card_data["s2_tier2"]
            if "Revised" in s2t2_images:
                results.append((s2t2_images["Revised"], f"{matched_card} (Set 2 - Tier 2)"))
            elif "Legacy" in s2t2_images:
                results.append((s2t2_images["Legacy"], f"{matched_card} (Set 2 - Tier 2)"))
        # For genki cards, s2 means S2 version
        elif card_data["s2"]:
            s2_images = card_data["s2"]
            if "Revised" in s2_images:
                results.append((s2_images["Revised"], f"{matched_card} (Set 2)"))
            elif "Legacy" in s2_images:
                results.append((s2_images["Legacy"], f"{matched_card} (Set 2)"))
    
    # No modifier - show defaults
    else:
        # Two-sided cards: show both A and B
        if card_data["sides"].get("A") and card_data["sides"].get("B"):
            a_images = card_data["sides"]["A"]
            b_images = card_data["sides"]["B"]
            
            if "Revised" in a_images:
                results.append((a_images["Revised"], f"{matched_card} (Side A)"))
            elif "Legacy" in a_images:
                results.append((a_images["Legacy"], f"{matched_card} (Side A)"))
            
            if "Revised" in b_images:
                results.append((b_images["Revised"], f"{matched_card} (Side B)"))
            elif "Legacy" in b_images:
                results.append((b_images["Legacy"], f"{matched_card} (Side B)"))
        
        # Tier 2 cards: show both S1 and S2 tier 2
        elif card_data["s2_tier2"]:
            # S1 original
            if card_data["s1"]:
                s1_images = card_data["s1"]
                if "Revised" in s1_images:
                    results.append((s1_images["Revised"], f"{matched_card} (Set 1)"))
                elif "Legacy" in s1_images:
                    results.append((s1_images["Legacy"], f"{matched_card} (Set 1)"))
            
            # S2 tier 2
            s2t2_images = card_data["s2_tier2"]
            if "Revised" in s2t2_images:
                results.append((s2t2_images["Revised"], f"{matched_card} (Set 2 - Tier 2)"))
            elif "Legacy" in s2t2_images:
                results.append((s2t2_images["Legacy"], f"{matched_card} (Set 2 - Tier 2)"))
        
        # Genki cards: prefer S2 > S1
        elif card_data["s2"]:
            s2_images = card_data["s2"]
            if "Revised" in s2_images:
                results.append((s2_images["Revised"], matched_card))
            elif "Legacy" in s2_images:
                results.append((s2_images["Legacy"], matched_card))
        
        elif card_data["s1"]:
            s1_images = card_data["s1"]
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
                if len(images) == 1:
                    image_path, label = images[0]
                    file = discord.File(image_path, filename=f"{label}.webp")
                    await message.reply(file=file, mention_author=False)
                else:
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
