import discord
from discord.ext import commands
from discord.ext.commands import CheckFailure
from pymongo import MongoClient
import os
from dotenv import load_dotenv
import traceback
import asyncio
from concurrent.futures import ThreadPoolExecutor

load_dotenv()
TOKEN = os.getenv("TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="+", intents=intents)

# Setup MongoDB client
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["transaction_db"]
collection = db["transactions"]

executor = ThreadPoolExecutor()

def is_admin():
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)

# Mongo blocking operations run in executor
def insert_log(entry):
    collection.insert_one(entry)

def find_logs(user_id):
    return list(collection.find({"user_id": user_id}))

def delete_log(user_id, amount):
    return collection.find_one_and_delete({"user_id": user_id, "amount": amount})

async def run_blocking(func, *args):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, func, *args)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, CheckFailure):
        await ctx.send("❌ You don’t have permission to use this command.")
    else:
        # Send error and print traceback for debugging
        await ctx.send(f"⚠️ Error occurred:\n```{error}```")
        traceback.print_exception(type(error), error, error.__traceback__)

@bot.command()
@is_admin()
async def log(ctx, user: discord.Member, *, rest: str):
    parts = rest.split()
    amount = None
    amount_index = None

    for i, part in enumerate(parts):
        try:
            amount = float(part)
            amount_index = i
            break
        except ValueError:
            continue

    if amount is None:
        await ctx.send("❌ Please provide a valid numeric amount.")
        return

    item_name = " ".join(parts[:amount_index]).strip()
    payment_type = " ".join(parts[amount_index + 1 :]).strip() or "No payment type provided"

    entry = {
        "user_id": user.id,
        "user_name": str(user),
        "amount": amount,
        "item": item_name,
        "payment_type": payment_type,
        "logger_id": ctx.author.id,
    }

    await run_blocking(insert_log, entry)
    await ctx.send(f"✅ Logged {amount} for {user.mention} | Item: {item_name} | Payment type: {payment_type}")

@bot.command(name="logs")
@is_admin()
async def logs_command(ctx, user: discord.Member):
    logs = await run_blocking(find_logs, user.id)

    if not logs:
        await ctx.send(f"📭 No logs found for {user.mention}")
        return

    msg = f"📋 Logs for {user.mention}:\n"
    for i, entry in enumerate(logs, 1):
        item = entry.get("item", "No item")
        amount = entry.get("amount", "N/A")
        payment_type = entry.get("payment_type", "N/A")
        logger = entry.get("logger_id", None)
        logger_mention = f"<@{logger}>" if logger else "Unknown"
        msg += f"{i}. Amount: {amount} | Item: {item} | Payment: {payment_type} | Logged by: {logger_mention}\n"

    await ctx.send(msg)

@bot.command()
@is_admin()
async def unlog(ctx, user: discord.Member, amount: float):
    result = await run_blocking(delete_log, user.id, amount)
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

@bot.command()
@is_admin()
async def testmongo(ctx):
    try:
        # Try a simple command to test connection
        await run_blocking(db.list_collection_names)
        await ctx.send("✅ MongoDB connection successful!")
    except Exception as e:
        await ctx.send(f"❌ MongoDB connection failed:\n```{e}```")
        traceback.print_exception(type(e), e, e.__traceback__)

bot.run(TOKEN)
