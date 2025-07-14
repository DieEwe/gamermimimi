# bot.py

import os
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select, Button
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

# ─── Setup ─────────────────────────────────────────────────────────────────────

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ─── “Tonight” RSVP (no picker) ────────────────────────────────────────────────

class TonightRSVPView(View):
    def __init__(self, author: discord.abc.User):
        super().__init__(timeout=None)
        self.author  = author
        self.joining = set()
        self.cant    = set()
        self.maybe   = set()

    def make_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🎮 Gamer-Mimimi SOS",
            description=f"{self.author.mention} wants to game **tonight!**",
            color=discord.Color.blurple()
        )
        embed.add_field(
            name=f"🐱 I'm in ({len(self.joining)})",
            value=", ".join(u.mention for u in self.joining) or "Nobody",
            inline=False
        )
        embed.add_field(
            name=f"❌ Can’t make it ({len(self.cant)})",
            value=", ".join(u.mention for u in self.cant) or "Nobody",
            inline=False
        )
        embed.add_field(
            name=f"🤡 Maybe, maybe not ({len(self.maybe)})",
            value=", ".join(u.mention for u in self.maybe) or "Nobody",
            inline=False
        )
        return embed

    async def update_message(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="🐱 I'm in", style=discord.ButtonStyle.success, custom_id="tonight_join")
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


# ─── Step 1: Date → Hour → Minute Picker ────────────────────────────────────────

class DaySelect(Select):
    def __init__(self):
        options = []
        today = datetime.now(timezone.utc).date()
        for i in range(5):
            d = today + timedelta(days=i)
            label = f"{d:%a %b} {d.day}"
            options.append(discord.SelectOption(label=label, value=d.isoformat()))
        super().__init__(
            placeholder="Select a date…",
            min_values=1, max_values=1,
            options=options,
            custom_id="day_select"
        )

    async def callback(self, interaction: discord.Interaction):
        view: PickerView = self.view  # type: ignore
        if not view:
            return await interaction.response.send_message("❌ Picker error.", ephemeral=True)

        view.chosen_date = self.values[0]
        view.clear_items()
        view.add_item(HourSelect())
        await interaction.response.edit_message(
            content=f"📅 Picked **{view.chosen_date}**. Now select an hour:",
            view=view
        )

class HourSelect(Select):
    def __init__(self):
        opts = [
            discord.SelectOption(label=f"{h:02d}", value=f"{h:02d}")
            for h in range(24)
        ]
        super().__init__(
            placeholder="Select hour…",
            min_values=1, max_values=1,
            options=opts,
            custom_id="hour_select"
        )

    async def callback(self, interaction: discord.Interaction):
        view: PickerView = self.view  # type: ignore
        if not view:
            return await interaction.response.send_message("❌ Picker error.", ephemeral=True)

        view.chosen_hour = self.values[0]
        view.clear_items()
        view.add_item(MinuteSelect())
        await interaction.response.edit_message(
            content=f"📅 Picked **{view.chosen_date} {view.chosen_hour}**. Now select minutes:",
            view=view
        )

class MinuteSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="00", value="00"),
            discord.SelectOption(label="30", value="30")
        ]
        super().__init__(
            placeholder="Select minutes…",
            min_values=1, max_values=1,
            options=options,
            custom_id="minute_select"
        )

    async def callback(self, interaction: discord.Interaction):
        view: PickerView = self.view  # type: ignore
        if not view:
            return await interaction.response.send_message("❌ Picker error.", ephemeral=True)

        dt_str = f"{view.chosen_date} {view.chosen_hour}:{self.values[0]}"
        dt = datetime.fromisoformat(dt_str)
        ts = int(dt.replace(tzinfo=timezone.utc).timestamp())

        rsvp = RSVPView(interaction.user, ts)
        await interaction.response.send_message(embed=rsvp.make_embed(), view=rsvp)
        try:
            if interaction.message:
                await interaction.message.delete()
        except discord.errors.NotFound:
            pass

class PickerView(View):
    def __init__(self):
        super().__init__(timeout=60)
        self.chosen_date = ""
        self.chosen_hour = ""
        self.add_item(DaySelect())


# ─── Step 2: Timestamped RSVP (Specific Date/Time) ─────────────────────────────

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
            title="🎮 Gamer-Mimimi SOS",
            description=f"{self.author.mention} wants to game at <t:{self.event_ts}:F>",
            color=discord.Color.blurple()
        )
        embed.add_field(
            name=f"🐱 Joining ({len(self.joining)})",
            value=", ".join(u.mention for u in self.joining) or "Nobody",
            inline=False
        )
        embed.add_field(
            name=f"❌ Can’t make it ({len(self.cant)})",
            value=", ".join(u.mention for u in self.cant) or "Nobody",
            inline=False
        )
        embed.add_field(
            name=f"🤡 Maybe, maybe not ({len(self.maybe)})",
            value=", ".join(u.mention for u in self.maybe) or "Nobody",
            inline=False
        )
        return embed

    async def update_message(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="🐱 I'm in", style=discord.ButtonStyle.success, custom_id="rsvp_join")
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


# ─── The `/gamer-mimimi` command group (global) ────────────────────────────────

gamer_group = app_commands.Group(
    name="gamer-mimimi",
    description="Schedule a gaming session"
)

@gamer_group.command(
    name="tonight",
    description="Announce a session happening tonight"
)
async def gamer_tonight(interaction: discord.Interaction):
    view = TonightRSVPView(interaction.user)
    await interaction.response.send_message(embed=view.make_embed(), view=view)

@gamer_group.command(
    name="specific",
    description="Pick a specific date and time for your session"
)
async def gamer_specific(interaction: discord.Interaction):
    view = PickerView()
    await interaction.response.send_message(
        "📅 **So you have extra wishes, eh? What do the demons tell you when you want to game?** First pick a date:",
        view=view,
        ephemeral=True
    )

# Register the group **globally**
bot.tree.add_command(gamer_group)


# ─── Bot Events & Sync ───────────────────────────────────────────────────────

@bot.event
async def on_ready():
    # narrow bot.user into a non‐None local
    user = bot.user
    if user is None:
        print("Logged in, but bot.user is None")
        return

    # now Pylance knows `user` is a discord.User, so `.id` is valid
    print(f"Logged in as {user} (ID: {user.id})")

    # global sync
    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} global command(s)")

# ─── Run ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_BOT_TOKEN is not set!")
    else:
        bot.run(TOKEN)
