import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from bson.objectid import ObjectId
import asyncio
import concurrent.futures

load_dotenv()
TOKEN = os.getenv("TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
bot = commands.Bot(command_prefix="+", intents=intents)

print("DEBUG: TOKEN loaded:", "Yes" if TOKEN else "No")
print("DEBUG: MONGO_URI loaded:", MONGO_URI if MONGO_URI else "None")

# MongoDB setup
client = MongoClient(MONGO_URI)
db = client["transaction_db"]
collection = db["logs"]

# Utility for running blocking code
executor = concurrent.futures.ThreadPoolExecutor()

async def run_blocking(func, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, *args)

def is_admin():
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ You do not have permission to use this command.")
    else:
        raise error

# --- LOG COMMAND ---
@bot.command()
@is_admin()
async def log(ctx, user: discord.Member, item: str, amount: float, payment: str):
    entry = {
        "user_id": str(user.id),
        "item": item,
        "amount": amount,
        "payment": payment,
        "logger_id": str(ctx.author.id)
    }

    await run_blocking(collection.insert_one, entry)
    await ctx.send(f"✅ Logged **{item} {amount} ({payment})** for {user.mention}")

# --- LOGS COMMAND ---
@bot.command(name="logs")
@is_admin()
async def logs_command(ctx, user: discord.Member):
    user_id = str(user.id)
    logs = await run_blocking(lambda: list(collection.find({"user_id": user_id})))

    if not logs:
        await ctx.send(f"📭 No logs found for {user.mention}")
        return

    msg = f"📋 Logs for {user.mention}:\n"
    for i, entry in enumerate(logs, 1):
        logger = f"<@{entry['logger_id']}>"
        msg += f"{i}. {entry['item']} - {entry['amount']} ({entry['payment']}) by {logger}\n"
    await ctx.send(msg)

# --- UNLOG COMMAND ---
@bot.command()
@is_admin()
async def unlog(ctx, user: discord.Member, index: int):
    logs = await run_blocking(lambda: list(collection.find({"user_id": str(user.id)})))

    if not logs or index < 1 or index > len(logs):
        await ctx.send("❌ Invalid log number.")
        return

    log_to_delete = logs[index - 1]
    result = await run_blocking(collection.delete_one, {"_id": log_to_delete["_id"]})

    if result.deleted_count:
        await ctx.send(f"🗑️ Deleted log #{index} for {user.mention}")
    else:
        await ctx.send("❌ Failed to delete the log.")

# --- ROLE TOGGLE ---
@bot.command()
@is_admin()
async def role(ctx, member: discord.Member, role: discord.Role):
    if role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"❌ Removed {role.mention} from {member.mention}")
    else:
        await member.add_roles(role)
        await ctx.send(f"✅ Added {role.mention} to {member.mention}")

# --- TEST MONGO ---
@bot.command()
@is_admin()
async def testmongo(ctx):
    try:
        stats = await run_blocking(db.command, "ping")
        if stats.get("ok") == 1:
            await ctx.send("✅ MongoDB connection is working!")
        else:
            await ctx.send("❌ MongoDB responded but with error.")
    except Exception as e:
        await ctx.send(f"❌ MongoDB error: {e}")

bot.run(TOKEN)
