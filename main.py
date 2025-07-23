import discord
from discord.ext import commands
from discord.ext.commands import has_permissions, CheckFailure
from pymongo import MongoClient
import os
from dotenv import load_dotenv

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

def is_admin():
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} ({bot.user.id})')

@bot.command()
@is_admin()
async def log(ctx, user: discord.Member, amount: float, *, reason: str = "No reason provided"):
    entry = {
        "user_id": user.id,
        "user_name": str(user),
        "amount": amount,
        "reason": reason
    }
    collection.insert_one(entry)
    await ctx.send(f"✅ Logged {amount} for {user.mention} | Reason: {reason}")

@bot.command(name="logs")
@is_admin()
async def logs(ctx, user: discord.Member):
    logs = collection.find({"user_id": user.id})
    result = ""
    for i, log in enumerate(logs, 1):
        result += f"{i}. Amount: {log['amount']} | Reason: {log['reason']}\n"
    if result == "":
        result = "No transactions found."
    await ctx.send(f"📒 Logs for {user.mention}:\n{result}")

@bot.command()
@is_admin()
async def unlog(ctx, user: discord.Member, amount: float):
    result = collection.find_one_and_delete({"user_id": user.id, "amount": amount})
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
        await ctx.send("⚠️ Error occurred.")

bot.run(TOKEN)
