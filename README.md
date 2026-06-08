# TubeFlow - MilitaryDeepOps Automation

This project is the automated content engine for the YouTube channel **MilitaryDeepOps**. 

It handles:
1. Sourcing trending or queued topics in military aviation.
2. Generating high-retention vertical scripts in English using Gemini.
3. Fetching copyright-free background clips (Pexels) and rendering voiceovers (Edge-TTS).
4. Compiling the final YouTube Shorts (9:16) with FFmpeg, burning stylized subtitles.
5. Uploading directly to YouTube and notifying via Telegram.

## Structure
- `/backend`: Core Python pipeline, video editor, APIs, and scheduler.
- `/frontend`: Minimal web UI for YouTube OAuth2 one-time login.
- `config.yaml`: Custom parameters for narration style, schedule, and api keys.
