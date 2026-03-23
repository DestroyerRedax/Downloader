import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel
from ytdlp_handler import extract_info, stream_download
from ffmpeg_utils import convert_audio_stream
from fb_scraper import scrape_facebook_photos

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="MediaGrab API", version="1.0.0")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"error": "Rate limit exceeded. Try again later."})


class AnalyzeRequest(BaseModel):
    url: str
    cookies: str | None = None


@app.post("/api/analyze")
@limiter.limit("10/minute")
async def analyze(request: Request, body: AnalyzeRequest):
    """Extract metadata and available formats from a URL."""
    try:
        # Check if it's a Facebook photo URL
        if "facebook.com" in body.url and ("/photo" in body.url or "/photos" in body.url):
            return scrape_facebook_photos(body.url, body.cookies)

        result = extract_info(body.url, body.cookies)
        return result
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@app.get("/api/download")
@limiter.limit("5/minute")
async def download(request: Request, url: str, format_id: str, cookies: str | None = None):
    """Stream download a specific format — zero disk writes."""
    try:
        # Check if audio conversion is requested
        if format_id.startswith("mp3-") or format_id.startswith("flac-"):
            codec = "mp3" if format_id.startswith("mp3-") else "flac"
            bitrate = format_id.split("-")[1] if codec == "mp3" else None
            source_format = format_id.split("-")[-1] if "-" in format_id.rsplit("-", 1)[-1] else "bestaudio"

            gen = convert_audio_stream(url, source_format, codec, bitrate, cookies)
            ext = "mp3" if codec == "mp3" else "flac"
            return StreamingResponse(
                gen,
                media_type=f"audio/{'mpeg' if codec == 'mp3' else 'flac'}",
                headers={
                    "Content-Disposition": f'attachment; filename="mediagrab_audio.{ext}"',
                    "Cache-Control": "no-cache",
                },
            )

        gen = stream_download(url, format_id, cookies)
        return StreamingResponse(
            gen,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="mediagrab_download"',
                "Cache-Control": "no-cache",
            },
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/health")
async def health():
    return {"status": "ok"}
