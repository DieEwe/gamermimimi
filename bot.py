# bot.py


import os
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
from dotenv import load_dotenv
load_dotenv()
# Load token from environment
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

class RSVPView(View):
    def __init__(self, author, date_str: str):
        super().__init__(timeout=None)
        self.author = author
        self.date_str = date_str
        # Track who clicked what
        self.joining = set()
        self.cant = set()
        self.maybe = set()

    async def update_embed(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎮 Gamer-Mimimi SOS",
            description=f"{self.author.mention} möchte gerne am **{self.date_str}** zocken!",
            color=discord.Color.blurple()
        )
        embed.add_field(
            name=f"✅ Kommt mit! ({len(self.joining)})",
            value=", ".join(u.mention for u in self.joining) or "Niemand",
            inline=False
        )
        embed.add_field(
            name=f"❌ Kann nicht! ({len(self.cant)})",
            value=", ".join(u.mention for u in self.cant) or "Niemand",
            inline=False
        )
        embed.add_field(
            name=f"🤷 Vielleicht... ({len(self.maybe)})",
            value=", ".join(u.mention for u in self.maybe) or "Niemand",
            inline=False
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="✅ Kommt!", style=discord.ButtonStyle.success, custom_id="rsvp_join")
    async def join_button(self, interaction: discord.Interaction, button: Button):
        user = interaction.user
        self.joining.add(user)
        self.cant.discard(user)
        self.maybe.discard(user)
        await self.update_embed(interaction)

    @discord.ui.button(label="❌ Kann nicht!", style=discord.ButtonStyle.danger, custom_id="rsvp_cant")
    async def cant_button(self, interaction: discord.Interaction, button: Button):
        user = interaction.user
        self.cant.add(user)
        self.joining.discard(user)
        self.maybe.discard(user)
        await self.update_embed(interaction)

    @discord.ui.button(label="🤷 Vielleicht", style=discord.ButtonStyle.secondary, custom_id="rsvp_maybe")
    async def maybe_button(self, interaction: discord.Interaction, button: Button):
        user = interaction.user
        self.maybe.add(user)
        self.joining.discard(user)
        self.cant.discard(user)
        await self.update_embed(interaction)

@bot.event
async def on_ready():
    if bot.user:
        print(f"Logged in as {bot.user} (ID: {getattr(bot.user, 'id', 'Unbekannt')})")
    else:
        print("Logged in, but bot.user is None")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(e)

@bot.tree.command(name="gamer-mimimi", description="Send a gaming SOS with date/time")
@app_commands.describe(date="Date and time (e.g. '2025-07-12 20:00')")
async def gamer_mimimi(interaction: discord.Interaction, date: str):
    view = RSVPView(interaction.user, date)
    embed = discord.Embed(
        title="🎮 Gamer-Mimimi SOS",
        description=f"{interaction.user.mention} wants to game at **{date}**",
        color=discord.Color.blurple()
    )
    await interaction.response.send_message(embed=embed, view=view)

if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("Fehler: DISCORD_BOT_TOKEN ist nicht gesetzt!")
