# bot.py

import os
import json
import discord
from zoneinfo import ZoneInfo, available_timezones
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select, Button
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from typing import Optional

# ─── Setup ─────────────────────────────────────────────────────────────────────

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if TOKEN is None:
    print("Error: DISCORD_BOT_TOKEN is not set!")
    exit(1)

# Optional guild‐ID for dev (instant sync); unset in production

# Persist user → IANA timezone
TZ_FILE = "timezones.json"
try:
    with open(TZ_FILE, "r") as f:
        timezone_map = json.load(f)
        if not isinstance(timezone_map, dict):
            raise ValueError
except (FileNotFoundError, json.JSONDecodeError, ValueError):
    timezone_map = {}

# ─── Persist guild → ping-role ID ─────────────────────────────────────────────
PING_FILE = "ping_roles.json"
try:
    with open(PING_FILE, "r") as f:
        ping_role_map = json.load(f)
        if not isinstance(ping_role_map, dict):
            raise ValueError
except (FileNotFoundError, json.JSONDecodeError, ValueError):
    ping_role_map = {}

def save_ping_roles() -> None:
    with open(PING_FILE, "w") as f:
        json.dump(ping_role_map, f, indent=2)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ─── Autocomplete helper for /mytimezone ──────────────────────────────────────

async def tz_autocomplete(interaction: discord.Interaction, current: str):
    matches = [
        tz for tz in sorted(available_timezones())
        if current.lower() in tz.lower()
    ]
    return [
        app_commands.Choice(name=tz, value=tz)
        for tz in matches[:25]
    ]

# ─── Group‐level check: require ping-role before ANY subcommand ──────────────

def ping_role_required():
    async def predicate(interaction: discord.Interaction) -> bool:
        cmd = interaction.command.name if interaction.command else None
        # always allow admins to set/clear ping-role
        if cmd in ("setpingrole", "clearpingrole"):
            return True
        gid = str(interaction.guild_id)
        if gid not in ping_role_map:
            raise app_commands.AppCommandError(
                "❌ **No ping-role configured.**\n"
                "An administrator must run:\n"
                "`/gamer-mimimi setpingrole @SomeRole`"
            )
        return True
    return app_commands.check(predicate)

# ─── “Tonight” RSVP ──────────────────────────────────────────────────────────

class TonightRSVPView(View):
    def __init__(self, author: discord.abc.User):
        super().__init__(timeout=None)
        self.author  = author
        self.joining = set()
        self.cant    = set()
        self.maybe   = set()

    def make_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🎮 Gamer-Mimimi",
            description=f"Mimimimimi!! {self.author.mention} wants to ~~mimi~~ game **tonight!**",
            color=discord.Color.blurple()
        )
        embed.add_field(
            name="🚀 Ready for warp",
            value=", ".join(u.mention for u in self.joining) or "Nobody",
            inline=False
        )
        embed.add_field(
            name="❌ Can’t make it",
            value=", ".join(u.mention for u in self.cant) or "Nobody",
            inline=False
        )
        embed.add_field(
            name="🤡 Maybe, maybe not",
            value=", ".join(u.mention for u in self.maybe) or "Nobody",
            inline=False
        )
        return embed

    async def update_message(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="🚀 Ready for warp!", style=discord.ButtonStyle.success, custom_id="tonight_join")
    async def join_button(self, interaction: discord.Interaction, button: Button):
        self.joining.add(interaction.user)
        self.cant.discard(interaction.user)
        self.maybe.discard(interaction.user)
        await self.update_message(interaction)

    @discord.ui.button(label="❌ Can’t make it", style=discord.ButtonStyle.danger, custom_id="tonight_cant")
    async def cant_button(self, interaction: discord.Interaction, button: Button):
        self.cant.add(interaction.user)
        self.joining.discard(interaction.user)
        self.maybe.discard(interaction.user)
        await self.update_message(interaction)

    @discord.ui.button(label="🤡 Maybe, maybe not", style=discord.ButtonStyle.secondary, custom_id="tonight_maybe")
    async def maybe_button(self, interaction: discord.Interaction, button: Button):
        self.maybe.add(interaction.user)
        self.joining.discard(interaction.user)
        self.cant.discard(interaction.user)
        await self.update_message(interaction)

# ─── Date → Hour → Minute Picker ─────────────────────────────────────────────

class DaySelect(Select):
    def __init__(self):
        opts = []
        today = datetime.now(timezone.utc).date()
        for i in range(5):
            d = today + timedelta(days=i)
            label = f"{d:%a %b} {d.day}"
            opts.append(discord.SelectOption(label=label, value=d.isoformat()))
        super().__init__(
            placeholder="Select a date…",
            min_values=1, max_values=1,
            options=opts,
            custom_id="day_select"
        )

    async def callback(self, interaction: discord.Interaction):
        view: PickerView = self.view  # type: ignore
        view.chosen_date = self.values[0]
        view.clear_items()
        view.add_item(HourSelect())
        await interaction.response.edit_message(
            content=f"⏰ You’ve locked in **{view.chosen_date}**, what hour do you want to blast off at?",
            view=view
        )

class HourSelect(Select):
    def __init__(self):
        options = []
        # instead of range(24), start at 5 PM then wrap
        hours = list(range(16, 24)) + list(range(0, 16))
        for h in hours:
            hour_12 = (h % 12) or 12
            suffix  = "AM" if h < 12 else "PM"
            label   = f"{hour_12} {suffix}"
            value   = f"{h:02d}"
            options.append(discord.SelectOption(label=label, value=value))

        super().__init__(
            placeholder="Select hour…",
            min_values=1, max_values=1,
            options=options,
            custom_id="hour_select"
        )

    async def callback(self, interaction: discord.Interaction):
        view: PickerView = self.view  # type: ignore
        view.chosen_hour = self.values[0]
        chosen_label = next(opt.label for opt in self.options if opt.value == view.chosen_hour)
        view.chosen_hour_label = chosen_label
        view.clear_items()
        view.add_item(MinuteSelect())
        await interaction.response.edit_message(
            content=(
                f"⏱️ Nice! **{view.chosen_date}** **{chosen_label}** is set—"
                "now, how many minutes into madness?"
            ),
            view=view
        )

class MinuteSelect(Select):
    def __init__(self):
        super().__init__(
            placeholder="Select minutes…",
            min_values=1, max_values=1,
            options=[
                discord.SelectOption(label="00", value="00"),
                discord.SelectOption(label="30", value="30")
            ],
            custom_id="minute_select"
        )

    async def callback(self, interaction: discord.Interaction):
        view: PickerView = self.view  # type: ignore
        # 1) Build naive datetime
        dt_str = f"{view.chosen_date} {view.chosen_hour}:{self.values[0]}"
        naive = datetime.fromisoformat(dt_str)
        # 2) Lookup user's tz
        uid = str(interaction.user.id)
        tz_name = timezone_map.get(uid)
        if not tz_name:
            return await interaction.response.send_message(
                "🚧 Please run `/gamer-mimimi settimezone` first to configure your timezone.",
                ephemeral=True
            )
        user_tz = ZoneInfo(tz_name)
        # 3) Convert to UTC ts
        ts = int(naive.replace(tzinfo=user_tz).astimezone(timezone.utc).timestamp())
        # 4) Ack & remove ephemeral picker
        await interaction.response.defer(ephemeral=True)
        await interaction.edit_original_response(content="✅ Suit up! Session is live. 🛰️", view=None)
        # 5) Send public RSVP
        gid  = str(interaction.guild_id)
        ping = f"<@&{ping_role_map[gid]}>"
        rsvp_view  = RSVPView(interaction.user, ts)
        rsvp_embed = rsvp_view.make_embed()
        chan = interaction.channel
        if isinstance(chan, (discord.TextChannel, discord.Thread, discord.DMChannel)):
            await chan.send(content=ping, embed=rsvp_embed, view=rsvp_view)

class PickerView(View):
    def __init__(self):
        super().__init__(timeout=60)
        self.chosen_date       = ""
        self.chosen_hour       = ""
        self.chosen_hour_label = ""
        self.add_item(DaySelect())

# ─── RSVP Buttons for timestamped event ───────────────────────────────────────

class RSVPView(View):
    def __init__(self, author: discord.abc.User, event_ts: int):
        super().__init__(timeout=None)
        self.author   = author
        self.event_ts = event_ts
        self.joining  = set()
        self.cant     = set()
        self.maybe    = set()

    def make_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🎮 Gamer-Mimimi",
            description=f"{self.author.mention}'s mimimi-ing nonstop about gaming at <t:{self.event_ts}:F>",
            color=discord.Color.blurple()
        )
        embed.add_field(name="🚀 Ready for warp", value=", ".join(u.mention for u in self.joining) or "Nobody", inline=False)
        embed.add_field(name="❌ Can’t make it", value=", ".join(u.mention for u in self.cant) or "Nobody", inline=False)
        embed.add_field(name="🤡 Maybe, maybe not", value=", ".join(u.mention for u in self.maybe) or "Nobody", inline=False)
        return embed

    async def update_message(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="🚀 Ready for warp!", style=discord.ButtonStyle.success, custom_id="rsvp_join")
    async def join_button(self, interaction: discord.Interaction, button: Button):
        self.joining.add(interaction.user)
        self.cant.discard(interaction.user)
        self.maybe.discard(interaction.user)
        await self.update_message(interaction)

    @discord.ui.button(label="❌ Can’t make it", style=discord.ButtonStyle.danger, custom_id="rsvp_cant")
    async def cant_button(self, interaction: discord.Interaction, button: Button):
        self.cant.add(interaction.user)
        self.joining.discard(interaction.user)
        self.maybe.discard(interaction.user)
        await self.update_message(interaction)

    @discord.ui.button(label="🤡 Maybe, maybe not", style=discord.ButtonStyle.secondary, custom_id="rsvp_maybe")
    async def maybe_button(self, interaction: discord.Interaction, button: Button):
        self.maybe.add(interaction.user)
        self.joining.discard(interaction.user)
        self.cant.discard(interaction.user)
        await self.update_message(interaction)

# ─── The `/gamer-mimimi` command group ─────────────────────────────────────────

gamer_group = app_commands.Group(
    name="gamer-mimimi",
    description="Schedule a gaming session"
)

# attach our single gate to the entire group


# 1) `/gamer-mimimi tonight`
@gamer_group.command(name="tonight", description="Announce a session happening tonight")
@ping_role_required()
async def gamer_tonight(interaction: discord.Interaction):
    # ephemeral acknowledgement
    await interaction.response.send_message("✅ Mimimi sent for **tonight!**", ephemeral=True)
    # now publish the real RSVP
    gid  = str(interaction.guild_id)
    ping = f"<@&{ping_role_map[gid]}>"
    view  = TonightRSVPView(interaction.user)
    embed = view.make_embed()
    chan  = interaction.channel
    if isinstance(chan, (discord.TextChannel, discord.Thread, discord.DMChannel)):
        await chan.send(content=ping, embed=embed, view=view)

# 2) `/gamer-mimimi specific`
@gamer_group.command(name="specific", description="Pick a specific date/time")
@ping_role_required()
async def gamer_specific(interaction: discord.Interaction):
    view = PickerView()
    await interaction.response.send_message("📅 **First pick a date:**", view=view, ephemeral=True)

# 3) `/gamer-mimimi mytimezone`
@gamer_group.command(name="mytimezone", description="Show your currently-saved IANA timezone")
@ping_role_required()
async def gamer_showtimezone(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    cur = timezone_map.get(uid)
    if cur:
        await interaction.response.send_message(
            f"🦄 Your dial’s set to **{cur}**!", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "🚨 You haven’t set a timezone yet. Run `/gamer-mimimi settimezone`.", ephemeral=True
        )

# 4) `/gamer-mimimi settimezone`
@gamer_group.command(name="settimezone", description="Set or change your IANA timezone")
@ping_role_required()
@app_commands.describe(tz="Your IANA timezone (autocomplete)")
@app_commands.autocomplete(tz=tz_autocomplete)
async def gamer_settimezone(interaction: discord.Interaction, tz: str):
    if tz not in available_timezones():
        return await interaction.response.send_message("❌ Invalid timezone.", ephemeral=True)
    uid = str(interaction.user.id)
    timezone_map[uid] = tz
    with open(TZ_FILE, "w") as f:
        json.dump(timezone_map, f)
    await interaction.response.send_message(f"✅ Timezone set to **{tz}**.", ephemeral=True)

# 5) `/gamer-mimimi cleartimezone`
@gamer_group.command(name="cleartimezone", description="Delete your saved IANA timezone")
@ping_role_required()
async def gamer_cleartimezone(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    if uid in timezone_map:
        del timezone_map[uid]
        with open(TZ_FILE, "w") as f:
            json.dump(timezone_map, f)
        await interaction.response.send_message("🗑️ Timezone cleared.", ephemeral=True)
    else:
        await interaction.response.send_message("ℹ️ You had no timezone set.", ephemeral=True)

# 6) `/gamer-mimimi setpingrole` (admin only)
@gamer_group.command(
    name="setpingrole",
    description="(Admin) Configure which role gets pinged"
)
@app_commands.describe(role="Role to ping")
@commands.has_guild_permissions(manage_guild=True)
async def gamer_setpingrole(interaction: discord.Interaction, role: discord.Role):
    gid = str(interaction.guild_id)
    ping_role_map[gid] = role.id
    save_ping_roles()
    await interaction.response.send_message(f"✅ I will now ping {role.mention}.", ephemeral=True)

# 7) `/gamer-mimimi clearpingrole` (admin only)
@gamer_group.command(
    name="clearpingrole",
    description="(Admin) Remove the ping-role"
)
@commands.has_guild_permissions(manage_guild=True)
async def gamer_clearpingrole(interaction: discord.Interaction):
    gid = str(interaction.guild_id)
    if ping_role_map.pop(gid, None) is not None:
        save_ping_roles()
        await interaction.response.send_message("✅ Ping-role cleared.", ephemeral=True)
    else:
        await interaction.response.send_message("ℹ️ No ping-role was set.", ephemeral=True)

# ─── 6) HELP ───────────────────────────────────────────────────────────────────
@gamer_group.command(
    name="help",
    description="Show a quick overview of all gamer-mimimi commands 📝"
)
async def gamer_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎮 Gamer-Mimimi Help",
        description="Here's what you can do:",
        color=discord.Color.blurple()
    )
    embed.add_field(
        name="📣 /gamer-mimimi setpingrole",
        value="REQUIRED *(Admin only)* Choose which role the bot pings.",
        inline=False
    )
    embed.add_field(
        name="🚫 /gamer-mimimi clearpingrole",
        value="*(Admin only)* Stop pinging any role.",
        inline=False
    )
    embed.add_field(
        name="🚀 /gamer-mimimi tonight",
        value="Announce a “tonight” gaming session with RSVP buttons.",
        inline=False
    )
    embed.add_field(
        name="⏱️ /gamer-mimimi specific",
        value="Pick a specific date & time via dropdowns.",
        inline=False
    )
    embed.add_field(
        name="🌐 /gamer-mimimi mytimezone",
        value="Show your saved IANA timezone.",
        inline=False
    )
    embed.add_field(
        name="✏️ /gamer-mimimi settimezone",
        value="Set or change your timezone (autocomplete).",
        inline=False
    )
    embed.add_field(
        name="🗑️ /gamer-mimimi cleartimezone",
        value="Delete your saved timezone.",
        inline=False
    )
    embed.set_footer(text="May your games be lag-free! 🕹️")

    await interaction.response.send_message(embed=embed, ephemeral=True)
# ─── Register & Sync ───────────────────────────────────────────────────────────


@bot.event
async def on_ready():
    user = bot.user
    if user is None:
        print("Logged in, but bot.user is None")
        return
    assert isinstance(user, (discord.User, discord.ClientUser))
    print(f"Logged in as {user} (ID: {user.id})")
    # Instant‐inject into every existing guild on startup
    for g in bot.guilds:
        bot.tree.add_command(gamer_group, guild=discord.Object(id=g.id))
        synced = await bot.tree.sync(guild=g)
        print(f"[startup] Synced {len(synced)} commands in {g.name} ({g.id})")

@bot.event
async def on_guild_join(guild: discord.Guild):
    # 1) Add our /gamer-mimimi group into the tree for this new guild…
    bot.tree.add_command(gamer_group, guild=discord.Object(id=guild.id))
    # 2) …then sync so it shows up instantly (no 1 h wait)
    synced = await bot.tree.sync(guild=guild)
    print(f"✅ Registered {len(synced)} slash-commands in guild {guild.name} ({guild.id})")


# ─── Global error handler for app_commands ───────────────────────────────────
from discord import app_commands

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    # If we already sent a response (very unlikely here) skip
    if interaction.response.is_done():
        return
    # Send the error message back to the user, ephemerally
    await interaction.response.send_message(str(error), ephemeral=True)

if __name__ == "__main__":
    bot.run(TOKEN)
