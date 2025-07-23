import discord
from discord.ext import commands
from discord.ext.commands import CheckFailure
from pymongo import MongoClient
import os
from dotenv import load_dotenv
import asyncio
import traceback
from concurrent.futures import ThreadPoolExecutor

load_dotenv()
TOKEN = os.getenv("TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='+', intents=intents)

# MongoDB setup
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["transaction_db"]
collection = db["transactions"]

# ThreadPoolExecutor for offloading blocking calls
executor = ThreadPoolExecutor()

def is_admin():
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} ({bot.user.id})')

# Blocking pymongo calls wrapped here:
def insert_log(entry):
    collection.insert_one(entry)

def find_logs(user_id):
    return list(collection.find({"user_id": user_id}))

def delete_log(user_id, amount):
    return collection.find_one_and_delete({"user_id": user_id, "amount": amount})

@bot.command()
@is_admin()
async def log(ctx, user: discord.Member, amount: float, *, reason: str = "No reason provided"):
    entry = {
        "user_id": user.id,
        "user_name": str(user),
        "amount": amount,
        "reason": reason
    }
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(executor, insert_log, entry)
    await ctx.send(f"✅ Logged {amount} for {user.mention} | Reason: {reason}")

@bot.command(name="logs")
@is_admin()
async def logs(ctx, user: discord.Member):
    loop = asyncio.get_running_loop()
    logs = await loop.run_in_executor(executor, find_logs, user.id)
    
    if not logs:
        await ctx.send("No transactions found.")
        return

    result = ""
    for i, log in enumerate(logs, 1):
        result += f"{i}. Amount: {log['amount']} | Reason: {log['reason']}\n"
    await ctx.send(f"📒 Logs for {user.mention}:\n{result}")

@bot.command()
@is_admin()
async def unlog(ctx, user: discord.Member, amount: float):
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(executor, delete_log, user.id, amount)
    if result:
        await ctx.send(f"🗑️ Removed log of {amount} for {user.mention}")
    else:
        await ctx.send("❌ Log not found.")

@bot.command()
@is_admin()
async def role(ctx, member: discord.Member, role: discord.Role):
    if role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"🔻 Removed role {role.name} from {member.mention}")
    else:
        await member.add_roles(role)
        await ctx.send(f"🔺 Added role {role.name} to {member.mention}")

@log.error
@logs.error
@unlog.error
@role.error
async def admin_command_error(ctx, error):
    if isinstance(error, CheckFailure):
        await ctx.send("❌ You don’t have permission to use this command.")
    else:
        # Send error message to Discord (remove if you want to keep errors private)
        await ctx.send(f"⚠️ Error occurred:\n```{error}```")
        # Print full traceback in logs (Railway console)
        traceback.print_exception(type(error), error, error.__traceback__)

bot.run(TOKEN)
