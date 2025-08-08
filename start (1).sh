#!/bin/bash
echo "📦 Setting up RazorBot..."
cd "$(dirname "$0")"
mkdir -p ~/razorbot_backups

# Set up Python venv
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Prompt for Discord token
read -p "Enter your Discord Bot Token: " TOKEN
export TOKEN="$TOKEN"

# Prompt for OpenAI API key
read -p "Enter your OpenAI API Key: " OPENAI_KEY
export OPENAI_API_KEY="$OPENAI_KEY"

# Insert tokens into bot.py
sed -i "s|TOKEN = \"\"|TOKEN = \"$TOKEN\"|" bot.py
sed -i "s|openai.api_key = \"\"|openai.api_key = \"$OPENAI_KEY\"|" bot.py

# Run bot
python bot.py
