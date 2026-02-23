import os
import discord
from discord.ext import commands

# ===== TOKEN (RAILWAY VARIABLE MUST BE: TOKEN) =====
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("TOKEN environment variable is not set!")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

# In-memory config (simple & fast)
autorole_config = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# ================= AUTOROLE COMMAND =================
@bot.command(name="autorole")
@commands.has_permissions(administrator=True)
async def autorole(ctx, channel: discord.TextChannel, *roles: discord.Role):
    if not roles:
        await ctx.send("❌ You must provide at least one role.")
        return

    roles = roles[:5]  # Max 5 roles
    guild = ctx.guild

    # Lock the channel for everyone (no chatting)
    overwrite = channel.overwrites_for(guild.default_role)
    overwrite.send_messages = False
    await channel.set_permissions(guild.default_role, overwrite=overwrite)

    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

    description = "\n".join(
        [f"{emojis[i]} → {roles[i].mention}" for i in range(len(roles))]
    )

    embed = discord.Embed(
        title="🔒 Verification Required",
        description=f"React below to get roles and unlock chat:\n\n{description}",
        color=discord.Color.blurple()
    )

    msg = await channel.send(embed=embed)

    for i in range(len(roles)):
        await msg.add_reaction(emojis[i])

    # Save config
    autorole_config[guild.id] = {
        "channel_id": channel.id,
        "message_id": msg.id,
        "role_ids": [role.id for role in roles]
    }

    await ctx.send(f"✅ Autorole panel created in {channel.mention}")

# ================= REACTION ROLE SYSTEM =================
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.guild_id is None or payload.user_id == bot.user.id:
        return

    config = autorole_config.get(payload.guild_id)
    if not config:
        return

    if payload.message_id != config["message_id"]:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    member = guild.get_member(payload.user_id)
    if not member:
        return

    channel = guild.get_channel(config["channel_id"])
    role_ids = config["role_ids"]

    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    emoji_str = str(payload.emoji)

    if emoji_str not in emojis:
        return

    index = emojis.index(emoji_str)

    if index >= len(role_ids):
        return

    role = guild.get_role(role_ids[index])
    if not role:
        return

    if role not in member.roles:
        try:
            await member.add_roles(role, reason="Reaction autorole verification")

            # Unlock chat for this specific user
            overwrite = channel.overwrites_for(member)
            overwrite.send_messages = True
            await channel.set_permissions(member, overwrite=overwrite)

        except discord.Forbidden:
            print("Missing permissions (Manage Roles / Manage Channels)")

bot.run(TOKEN)
