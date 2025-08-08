import discord, asyncio, sqlite3, os, zipfile, time, threading, schedule
import openai
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta

TOKEN = ""

openai.api_key = ""  # Will be injected by start.sh

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

db_file = "Cafe ☕️.db"
backup_dir = os.path.expanduser("~/Cafe ☕️bot_backups")

if not os.path.exists(db_file):
    if os.path.exists(backup_dir):
        backups = sorted([f for f in os.listdir(backup_dir) if f.endswith(".zip")])
        if backups:
            with zipfile.ZipFile(os.path.join(backup_dir, backups[-1]), 'r') as zip_ref:
                zip_ref.extractall(".")

conn = sqlite3.connect(db_file)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS money (user_id INTEGER PRIMARY KEY, balance INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS invites (inviter_id INTEGER, invited_id INTEGER UNIQUE)")
c.execute("CREATE TABLE IF NOT EXISTS afk (user_id INTEGER PRIMARY KEY, reason TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS prefixes (guild_id INTEGER PRIMARY KEY, prefix TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS commands (prefix TEXT, cmd TEXT, msg TEXT, type TEXT)")
conn.commit()

@bot.event
async def on_guild_join(guild):
    c.execute("INSERT OR IGNORE INTO prefixes (guild_id, prefix) VALUES (?, '!')", (guild.id,))
    conn.commit()

def get_prefix(bot, message):
    try:
        c.execute("SELECT prefix FROM prefixes WHERE guild_id = ?", (message.guild.id,))
        result = c.fetchone()
        return result[0] if result else "!"
    except:
        return "!"

bot.command_prefix = get_prefix

@tree.command(name="imagine", description="Generate an AI image from a prompt.")
async def imagine(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    try:
        response = openai.Image.create(
            prompt=prompt,
            n=1,
            size="512x512"
        )
        image_url = response["data"][0]["url"]
        embed = discord.Embed(title="🧠 AI Image Generator", description=f"Prompt: `{prompt}`", color=0x00ffff)
        embed.set_image(url=image_url)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Error generating image: {e}")

@tree.command(name="setprefix")
@app_commands.checks.has_permissions(administrator=True)
async def setprefix(interaction: discord.Interaction, prefix: str):
    c.execute("INSERT OR REPLACE INTO prefixes (guild_id, prefix) VALUES (?, ?)", (interaction.guild.id, prefix))
    conn.commit()
    embed = discord.Embed(description=f"✅ Prefix set to `{prefix}`.", color=0x00ffff)
    await interaction.response.send_message(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        await tree.sync()
    except Exception as e:
        print("❌ Sync failed:", e)
    await cache_invites()

def backup_task():
    while True:
        try:
            if os.path.exists(db_file):
                filename = f"Cafe ☕️bot_backup_{datetime.now().strftime('%Y-%m-%d--%H-%M-%S')}.zip"
                with zipfile.ZipFile(os.path.join(backup_dir, filename), 'w') as z:
                    z.write(db_file)
                print(" Backup saved.")
        except Exception as e:
            print("❌ Backup failed:", e)
        time.sleep(600)

threading.Thread(target=backup_task, daemon=True).start()

guild_invites = {}
async def cache_invites():
    for guild in bot.guilds:
        try:
            invites = await guild.invites()
            guild_invites[guild.id] = invites
        except: pass

@bot.event
async def on_member_join(member):
    await asyncio.sleep(2)
    try:
        new_invites = await member.guild.invites()
        old_invites = guild_invites.get(member.guild.id, [])
        inviter = None
        for invite in new_invites:
            for old in old_invites:
                if invite.code == old.code and invite.uses > old.uses:
                    inviter = invite.inviter
                    break
        if inviter:
            c.execute("INSERT OR IGNORE INTO invites (inviter_id, invited_id) VALUES (?, ?)", (inviter.id, member.id))
            c.execute("INSERT OR IGNORE INTO money (user_id, balance) VALUES (?, 0)", (inviter.id,))
            c.execute("UPDATE money SET balance = balance + 10 WHERE user_id = ?", (inviter.id,))
            conn.commit()
        guild_invites[member.guild.id] = new_invites
    except: pass

@tree.command(name="afk")
async def afk(interaction: discord.Interaction, reason: str = "AFK"):
    c.execute("INSERT OR REPLACE INTO afk (user_id, reason) VALUES (?, ?)", (interaction.user.id, reason))
    conn.commit()
    embed = discord.Embed(description=f" {interaction.user.mention} is now AFK: {reason}", color=0x00ffff)
    await interaction.response.send_message(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    c.execute("SELECT reason FROM afk WHERE user_id = ?", (message.author.id,))
    if c.fetchone():
        c.execute("DELETE FROM afk WHERE user_id = ?", (message.author.id,))
        conn.commit()

    for user in message.mentions:
        c.execute("SELECT reason FROM afk WHERE user_id = ?", (user.id,))
        result = c.fetchone()
        if result:
            await message.channel.send(f" {user.mention} is AFK: {result[0]}")

    c.execute("SELECT * FROM commands")
    for prefix, cmd, msg, typ in c.fetchall():
        if message.content.strip() == prefix + cmd:
            if typ == "send here":
                await message.channel.send(msg)
            elif typ == "dm":
                await message.author.send(msg)

    await bot.process_commands(message)

bot.run(TOKEN)
