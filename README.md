# 🎓 SSC CGL/CHSL AI Quiz Bot (Docker)

Docker-based AI-powered quiz bot for SSC exam preparation.

## 🚀 Features

- ✅ Docker containerized
- ✅ AI-Generated Questions (Gemini)
- ✅ SSC CGL/CHSL Exam Level
- ✅ English & GK subjects
- ✅ Bilingual GK (Hindi + English)
- ✅ Infinite Questions
- ✅ Score Tracking
- ✅ Self-Healing (Retry + Fallback)
- ✅ Health Check Endpoints

## 🐳 Docker Deployment

### Local Testing
```bash
docker build -t ssc-quiz-bot .
docker run -e TELEGRAM_BOT_TOKEN=your_token -e GEMINI_API_KEY=your_key -p 10000:10000 ssc-quiz-bot
```

### Render Deployment
1. Push to GitHub
2. Connect repo to Render
3. Select "Docker" environment
4. Add Environment Variables:
   - `TELEGRAM_BOT_TOKEN`
   - `GEMINI_API_KEY`
5. Deploy!

## 📁 Files

- `Dockerfile` - Docker configuration
- `bot.py` - Main bot logic
- `health_server.py` - Health check server
- `run.py` - Entry point
- `requirements.txt` - Python dependencies
- `render.yaml` - Render config

## ⚡ Keep Alive

Setup cron job at [cron-job.org](https://cron-job.org):
- URL: `https://your-app.onrender.com/health`
- Interval: Every 5 minutes

## 🎮 Bot Commands

- `/start` - Start the quiz
- `/health` - Check bot status

Made with ❤️ for SSC aspirants
