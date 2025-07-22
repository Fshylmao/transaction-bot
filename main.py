import discord
from discord.ext import commands
import json
import os
import datetime
from aiohttp import web
import asyncio

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

@bot.command()
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
async def unlog(ctx, log_id: int):
    global transaction_list
    found = next((t for t in transaction_list if t["id"] == log_id), None)

    if not found:
        await ctx.send(f"❌ No transaction found with ID {log_id}")
        return

    transaction_list = [t for t in transaction_list if t["id"] != log_id]
    save()
    await ctx.send(f"🗑️ Deleted transaction #{log_id}")

@bot.command()
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

# --- Webserver for uptime monitoring ---

async def handle(request):
    return web.Response(text="Bot is alive!")

app = web.Application()
app.add_routes([web.get('/', handle)])

runner = web.AppRunner(app)

async def start_webserver():
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

async def main():
    await start_webserver()
    await bot.start(os.environ.get("TOKEN") or "YOUR_BOT_TOKEN_HERE")

asyncio.run(main())
