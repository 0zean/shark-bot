# 🦈 Shark Music Bot

Discord music bot built around Discord.py, YT-DLP, and FFMPEG.

## 🎚️ Features
- YouTube links
- YouTube search
- Soundcloud links
- Discord CDN links & File uploads
- Dynamic embeded messages
- Auto disconnect after 10 mins of inactivity or empty voice channel

## ⌨️ Commands
- `/play` (search): Plays a YouTube, Soundcloud, or CDN link, OR searches for a YouTube video by title.
- `/play` (file): Plays music from file upload (supported file types in `utils/configs.json`).
- `/skip`: Skips currently playing song and plays the next in queue OR stops currently playing song if nothing in queue.
- `/leave`: Disconnects the bot from voice channel.
- `/clean`: Purges the `limit` amount of bot-related messages in a text channel (Default limit value is 100).
