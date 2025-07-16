# Gamer-Mimimi Discord Bot

Gamer-Mimimi is a Discord bot for scheduling and organizing gaming sessions with your friends. It provides easy RSVP buttons, timezone support, and role-based pings to make group gaming hassle-free.

## Features

- **/gamer-mimimi tonight**: Announce a gaming session for tonight with RSVP buttons (Ready, Can't, Maybe).
- **/gamer-mimimi specific**: Schedule a session for a specific date and time using dropdown pickers.
- **/gamer-mimimi mytimezone**: View your currently saved IANA timezone.
- **/gamer-mimimi settimezone**: Set or change your timezone (with autocomplete).
- **/gamer-mimimi cleartimezone**: Remove your saved timezone.
- **/gamer-mimimi setpingrole**: *(Admin only)* Set which role gets pinged for sessions.
- **/gamer-mimimi clearpingrole**: *(Admin only)* Remove the ping role.
- **/gamer-mimimi help**: Show a quick overview of all commands.

## Setup

1. **Clone the repository:**
   ```sh
   git clone https://github.com/DieEwe/gamermimimi.git
   cd gamermimimi
   ```

2. **Create a virtual environment (optional but recommended):**
   ```sh
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   # or
   source .venv/bin/activate  # On macOS/Linux
   ```

3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   - Copy `.env.example` to `.env` (or create `.env` manually).
   - Set your Discord bot token and (optionally) a guild ID for development:
     ```env
     DISCORD_BOT_TOKEN=your-bot-token-here
     GUILD_ID=your-guild-id-here  # Optional, for dev only
     ```

5. **Run the bot:**
   ```sh
   python bot.py
   ```

## Permissions
- The bot requires the following Discord permissions:
  - Send Messages
  - Embed Links
  - Manage Roles
  - Use Slash Commands

## Usage
- Use `/gamer-mimimi help` in your server to see all available commands and their descriptions.
- Only admins (with Manage Server permission) can set or clear the ping role.
- Each user can set their own timezone for accurate scheduling.

## Contributing
Pull requests and suggestions are welcome! Please open an issue or PR on GitHub.

## License
MIT License
