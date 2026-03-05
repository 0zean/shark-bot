# 🦈 Shark Music Bot

A well‑architected Discord music bot built with [discord.py](https://discordpy.readthedocs.io/), `yt-dlp`, and `FFmpeg`. Engineered with a modular Cog‑based design and a decoupled service layer, delivering high‑quality audio streaming through fully integrated Slash Commands.

> [!NOTE]
> Updated to use Discord's new [DAVE protocol](https://discord.com/blog/bringing-dave-to-all-discord-platforms)

## 🎚️ Features
- **Multi-Source Playback:** Stream audio from YouTube (via URL or search queries) and SoundCloud.
- **Direct Audio Uploads:** Play music directly from file uploads and Discord CDN links (configurable formats up to 10MB).
- **Slash-Command Interface:** Uses Discord's integrated Slash Commands for intuitive interactions and a cleaner server experience.
- **Rich Embeds:** Dynamic "Now Playing" and queued track updates, featuring video thumbnails and personalized accent colors based on the invoking user's color.
- **Smart Resource Management:**
  - Automatically disconnects from voice channels after configurable periods of inactivity, with a dynamic grace period based on queued track lengths.
  - Automatically leaves when left alone in a voice channel to conserve resources.

## ⌨️ Commands
- `/play [search] [file]`: Queue and play a track. Provide a search query/URL for YouTube/SoundCloud, or directly attach a supported audio file.
- `/skip`: Skips the currently playing song and advances to the next track in the queue. Stops playback if no more tracks are in the queue.
- `/leave`: Disconnects the bot from the current voice channel and clears the active queue.
- `/clean [limit]`: Purges bot-authored messages from the current text channel (default limit: 100 messages).
- `/name`: Changes your nickname in the server to a randomly generated one for fun.

## 📦 Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/0zean/shark-bot.git
   cd shark-bot
   ```
2. Install dependencies (Python 3.11+, `ffmpeg` must be in your PATH):
   ```bash
   uv sync
   ```
3. Create a Discord application, enable the **Bot** and **Slash Commands** intents, and copy the token.
4. Create a `.env` file:
   ```env
   DISCORD_TOKEN=your_bot_token_here
   ```
5. Run the bot:
   ```bash
   uv run python shark.py
   ```

## 🤝 Contributing
Contributions are welcome! Feel free to open issues or submit pull requests. Please follow the existing code style.

## 📄 License
This project is licensed under the GNU GPLv3 License – see the `LICENSE` file for details.
