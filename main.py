import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import json

load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="+", intents=intents)

LOG_FILE = "transaction_logs.json"

# Load logs from file or start empty
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, "r") as f:
        logs = json.load(f)
else:
    logs = {}

def save_logs():
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=4)

def is_admin():
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ You do not have permission to use this command.")
    else:
        raise error

@bot.command()
@is_admin()
async def log(ctx, user: discord.User, *, amount: str):
    user_id = str(user.id)
    if user_id not in logs:
        logs[user_id] = []
    logs[user_id].append({"amount": amount, "logger": str(ctx.author.id)})
    save_logs()
    await ctx.send(f"✅ Logged **{amount}** for {user.mention}")

@bot.command(name="logs")
@is_admin()
async def logs_command(ctx, user: discord.User):
    user_id = str(user.id)
    if user_id not in logs or not logs[user_id]:
        await ctx.send(f"📭 No logs found for {user.mention}")
        return

    msg = f"📋 Logs for {user.mention}:\n"
    for i, entry in enumerate(logs[user_id], 1):
        msg += f"{i}. {entry['amount']} (by <@{entry['logger']}>)\n"
    await ctx.send(msg)

@bot.command()
@is_admin()
async def unlog(ctx, user: discord.User, *, amount: str):
    user_id = str(user.id)
    if user_id in logs:
        original_length = len(logs[user_id])
        logs[user_id] = [
            entry for entry in logs[user_id] if entry["amount"] != amount
        ]
        if len(logs[user_id]) < original_length:
            save_logs()
            await ctx.send(f"🗑️ Removed **{amount}** from {user.mention}'s logs.")
        else:
            await ctx.send("❌ No matching entry found.")
    else:
        await ctx.send("❌ No logs for that user.")

@bot.command()
@is_admin()
async def role(ctx, member: discord.Member, role: discord.Role):
    if role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"Removed {role.mention} from {member.mention}")
    else:
        await member.add_roles(role)
        await ctx.send(f"Added {role.mention} to {member.mention}")

bot.run(TOKEN)
