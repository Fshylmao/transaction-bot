import discord
from discord.ext import commands
from discord.ext.commands import has_permissions, CheckFailure
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv("TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

client = commands.Bot(command_prefix="+", intents=discord.Intents.all())
mongo = MongoClient(MONGO_URI)
db = mongo["logDB"]
collection = db["logs"]

def is_admin():
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)

@client.event
async def on_ready():
    print(f"Bot connected as {client.user}")

@client.command()
@is_admin()
async def log(ctx, member: discord.Member, *, details):
    log_entry = {
        "user_id": member.id,
        "user_name": str(member),
        "details": details,
        "moderator": str(ctx.author),
        "mod_id": ctx.author.id
    }
    collection.insert_one(log_entry)
    await ctx.send(f"✅ Logged `{member}` for: **{details}**")

@client.command(name="logs")
@is_admin()
async def logs(ctx, member: discord.Member):
    user_logs = collection.find({"user_id": member.id})
    logs = [f"• {log['details']} (by {log['moderator']})" for log in user_logs]
    if not logs:
        await ctx.send(f"❌ No logs found for {member.mention}")
        return
    msg = f"📄 Logs for {member.mention}:\n" + "\n".join(logs)
    await ctx.send(msg)

@client.command()
@is_admin()
async def unlog(ctx, member: discord.Member, *, details):
    result = collection.delete_one({
        "user_id": member.id,
        "details": details
    })
    if result.deleted_count > 0:
        await ctx.send(f"✅ Removed log from `{member}`: **{details}**")
    else:
        await ctx.send(f"❌ No matching log found for `{member}` with those details.")

@client.command()
@is_admin()
async def role(ctx, member: discord.Member, role: discord.Role):
    if role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"❌ Removed role `{role.name}` from {member.mention}")
    else:
        await member.add_roles(role)
        await ctx.send(f"✅ Gave role `{role.name}` to {member.mention}")

client.run(TOKEN)
