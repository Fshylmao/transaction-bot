import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
TOKEN = os.getenv("TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

# MongoDB setup
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client["transaction_db"]
logs_collection = mongo_db["transactions"]

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix="+", intents=intents)

def is_admin():
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ You do not have permission to use this command.")
    else:
        raise error

@bot.command()
@is_admin()
async def log(ctx, user: discord.Member, item: str, amount: float, payment_type: str):
    entry = {
        "user_id": user.id,
        "user_name": user.name,
        "item": item,
        "amount": amount,
        "payment_type": payment_type,
        "logger_id": ctx.author.id
    }
    logs_collection.insert_one(entry)
    await ctx.send(f"✅ Logged `{item}` worth **{amount}** via `{payment_type}` for {user.mention}")

@bot.command(name="logs")
@is_admin()
async def logs_command(ctx, user: discord.Member):
    user_logs = list(logs_collection.find({"user_id": user.id}))
    if not user_logs:
        await ctx.send(f"📭 No logs found for {user.mention}")
        return

    msg = f"📋 Logs for {user.mention}:\n"
    for i, entry in enumerate(user_logs, 1):
        msg += (
            f"{i}. `{entry['item']}` - ${entry['amount']} ({entry['payment_type']}) "
            f"(by <@{entry['logger_id']}>)\n"
        )
    await ctx.send(msg)

@bot.command()
@is_admin()
async def unlog(ctx, user: discord.Member, index: int):
    user_logs = list(logs_collection.find({"user_id": user.id}))
    if not user_logs or index < 1 or index > len(user_logs):
        await ctx.send("❌ Invalid log index.")
        return

    to_delete = user_logs[index - 1]
    logs_collection.delete_one({"_id": to_delete["_id"]})
    await ctx.send(f"🗑️ Removed log #{index} for {user.mention}")

@bot.command()
@is_admin()
async def testmongo(ctx):
    try:
        mongo_client.admin.command("ping")
        await ctx.send("✅ MongoDB connection successful.")
    except Exception as e:
        await ctx.send(f"❌ MongoDB connection failed: {e}")

# Fixed role command to accept role name strings
@bot.command()
@is_admin()
async def role(ctx, member: discord.Member, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if role is None:
        await ctx.send(f"❌ Role '{role_name}' not found.")
        return

    if role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"Removed {role.mention} from {member.mention}")
    else:
        await member.add_roles(role)
        await ctx.send(f"Added {role.mention} to {member.mention}")

bot.run(TOKEN)
