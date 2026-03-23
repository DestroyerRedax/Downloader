# MediaGrab Backend

FastAPI backend for MediaGrab — zero-disk streaming media downloader.

## Features
- **yt-dlp** for metadata extraction & streaming downloads
- **FFmpeg** for audio conversion (MP3 320kbps / FLAC)
- **Facebook photo scraper** with cookie support
- **Rate limiting** (10 analyze/min, 5 download/min)
- **Zero disk writes** — all media is piped from subprocess to HTTP response

## Quick Start (Local)

```bash
pip install -r requirements.txt
ALLOWED_ORIGINS=http://localhost:8080 uvicorn main:app --reload --port 8000
```

## Deploy to Railway

1. Push this folder to a GitHub repository
2. Create a new Railway project → "Deploy from GitHub Repo"
3. Set environment variable: `ALLOWED_ORIGINS=https://downloadermedia.lovable.app`
4. Railway will auto-detect the Dockerfile and deploy

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | `*` |
| `PORT` | Server port | `8000` |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/analyze` | Extract metadata & formats from URL |
| GET | `/api/download` | Stream download a specific format |
| GET | `/health` | Health check |

## Frontend Connection

Set `VITE_API_URL` in your Lovable project to your Railway URL:
```
https://your-app.up.railway.app
```
