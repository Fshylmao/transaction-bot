import discord
from discord.ext import commands
import json
import os
import datetime
from aiohttp import web
import asyncio

# If using locally and .env file, uncomment next 2 lines:
# from dotenv import load_dotenv
# load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='+', intents=intents)

FILE = "transactions.json"

# Load transactions from file or start empty list
if os.path.exists(FILE):
    with open(FILE, "r") as f:
        transaction_list = json.load(f)
else:
    transaction_list = []

def save():
    with open(FILE, "w") as f:
        json.dump(transaction_list, f, indent=2)

def get_next_id():
    return (transaction_list[-1]["id"] + 1) if transaction_list else 1

# Admin permission check decorator
def is_admin():
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)

@bot.command()
@is_admin()
async def log(ctx, user_input, *, details):
    try:
        if user_input.startswith("<@") and user_input.endswith(">"):
            user_id = int(user_input.strip("<@!>"))
        else:
            user_id = int(user_input)
        user = await bot.fetch_user(user_id)
    except:
        await ctx.send("❌ Invalid user.")
        return

    parts = details.rsplit(" ", 2)
    if len(parts) != 3:
        await ctx.send("❌ Format: `+log @user skin amount payment_method`")
        return

    skin, amount_str, payment = parts
    try:
        amount = float(amount_str)
    except:
        await ctx.send("❌ Invalid amount.")
        return

    transaction = {
        "id": get_next_id(),
        "user_id": user.id,
        "username": str(user),
        "skin": skin.strip(),
        "amount": amount,
        "payment_method": payment.lower(),
        "logged_by": str(ctx.author),
        "timestamp": datetime.datetime.utcnow().isoformat()
    }

    transaction_list.append(transaction)
    save()

    await ctx.send(f"✅ Logged #{transaction['id']}: **{user}** | **{skin.strip()}** | **${amount}** via **{payment}**")

@bot.command()
@is_admin()
async def unlog(ctx, user_input, log_id: int):
    global transaction_list

    try:
        if user_input.startswith("<@") and user_input.endswith(">"):
            user_id = int(user_input.strip("<@!>"))
        else:
            user_id = int(user_input)
    except:
        await ctx.send("❌ Invalid user.")
        return

    found = next((t for t in transaction_list if t["id"] == log_id and t["user_id"] == user_id), None)

    if not found:
        await ctx.send(f"❌ No transaction found with ID {log_id} for that user.")
        return

    transaction_list = [t for t in transaction_list if not (t["id"] == log_id and t["user_id"] == user_id)]
    save()
    await ctx.send(f"🗑️ Deleted transaction #{log_id} for <@{user_id}>")

@bot.command()
@is_admin()
async def transactions(ctx, user: discord.Member):
    user_logs = [t for t in transaction_list if t["user_id"] == user.id]

    if not user_logs:
        await ctx.send(f"📭 No transactions found for {user}")
        return

    lines = []
    for t in user_logs[-10:]:
        lines.append(f"#{t['id']} | {t['skin']} | ${t['amount']} via {t['payment_method']}")

    msg = f"📒 Last {len(lines)} transactions for {user.mention}:\n" + "\n".join(lines)
    await ctx.send(msg)

# Error handler for permission errors
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ You do not have permission to use this command.")
    else:
        raise error  # Show other errors in logs

# --- Webserver for uptime monitoring ---
async def handle(request):
    return web.Response(text="Bot is alive!")

app = web.Application()
app.add_routes([web.get('/', handle)])

runner = web.AppRunner(app)

async def start_webserver():
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    await start_webserver()
    TOKEN = os.getenv("TOKEN") or "YOUR_BOT_TOKEN_HERE"
    await bot.start(TOKEN)

asyncio.run(main())
