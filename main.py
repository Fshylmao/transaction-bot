import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import json

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="+", intents=intents)

DATA_FILE = "transactions.json"

# Load or create transactions data
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

@bot.event
async def on_ready():
    print(f"Bot is ready. Logged in as {bot.user}")

@bot.command()
@commands.has_permissions(administrator=True)
async def log(ctx, member: discord.Member, *, amount: str):
    data = load_data()
    user_id = str(member.id)
    if user_id not in data:
        data[user_id] = []
    data[user_id].append(amount)
    save_data(data)
    await ctx.send(f"✅ Logged `{amount}` for {member.mention}")

@bot.command(name="logs")
@commands.has_permissions(administrator=True)
async def logs(ctx, member: discord.Member):
    data = load_data()
    user_id = str(member.id)
    if user_id in data and data[user_id]:
        logs = "\n".join(f"{idx+1}. {log}" for idx, log in enumerate(data[user_id]))
        await ctx.send(f"📜 Logs for {member.mention}:\n{logs}")
    else:
        await ctx.send(f"📜 No logs found for {member.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def unlog(ctx, member: discord.Member, index: int):
    data = load_data()
    user_id = str(member.id)
    if user_id in data and 0 < index <= len(data[user_id]):
        removed = data[user_id].pop(index - 1)
        save_data(data)
        await ctx.send(f"❌ Removed log entry `{removed}` for {member.mention}")
    else:
        await ctx.send("⚠️ Invalid log entry or user has no logs.")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def role(ctx, member: discord.Member, role: discord.Role):
    if role in member.roles:
        try:
            await member.remove_roles(role)
            await ctx.send(f"❌ Removed **{role.name}** from {member.mention}")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to remove that role.")
    else:
        try:
            await member.add_roles(role)
            await ctx.send(f"✅ Gave **{role.name}** to {member.mention}")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to give that role.")

bot.run(TOKEN)
