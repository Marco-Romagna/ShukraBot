# Kylia TCG Discord Bot - Setup Guide

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Your Discord Token
```bash
export DISCORD_TOKEN='your_token_here'
```

Replace `your_token_here` with your bot token from the Discord Developer Portal.

### 3. Run the Bot
```bash
python kylia_bot.py
```

You should see:
```
✅ Bot logged in as YourBotName#0000
📚 Loaded XXX cards
✨ Synced 1 command(s)
```

## Usage

### In Discord

**Method 1: Bracket Query (Recommended)**
```
User: Check out [[Long Sword]]
Bot: [sends card image]
```

**Method 2: Slash Command**
```
/card Long Sword
```

### Features

✅ **Fuzzy Matching** - Handles typos and variations
- `[[longsword]]` finds "Long Sword"
- `[[dreadnaught cann]]` finds "Dreadnought Cannon"

✅ **Auto Prioritization**
- Always serves **Revised** version if available
- Falls back to **Legacy** if Revised doesn't exist
- Special handling for Finesse variants (Return of the Moson Khalim, The Shrine of Tabudai, Essence of Eternity)

✅ **Error Handling**
- Returns "Card not found" for unrecognized cards
- Graceful error messages if file can't load

## Troubleshooting

**Bot not responding?**
- Check token is set: `echo $DISCORD_TOKEN`
- Restart the bot
- Make sure bot has "Send Messages" and "Attach Files" permissions

**Cards not loading?**
- Verify card files are in `/mnt/project/`
- Check bot has file access permissions

**Token error?**
- Double-check token is correct (copy from Developer Portal, not somewhere else)
- Make sure there are no extra spaces

## Deployment Options

### Option A: Keep Running Locally
```bash
nohup python kylia_bot.py &
```

### Option B: Use systemd (Linux/Mac)
Create `/etc/systemd/system/kylia-bot.service`:
```
[Unit]
Description=Kylia TCG Discord Bot
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/path/to/bot
Environment="DISCORD_TOKEN=your_token"
ExecStart=/usr/bin/python3 kylia_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then run:
```bash
sudo systemctl enable kylia-bot
sudo systemctl start kylia-bot
```

### Option C: Cloud Hosting (Heroku, Replit, etc.)
Set environment variable `DISCORD_TOKEN` in your hosting platform settings.
