"""yt-dlp wrapper — metadata extraction and streaming downloads via subprocess pipes."""

import json
import subprocess
from typing import Generator


def _build_base_args(cookies: str | None = None) -> list[str]:
    args = ["yt-dlp", "--no-check-certificates"]
    if cookies:
        # Write cookies to a temp pipe (avoid disk)
        args += ["--cookies", "/dev/stdin"]
    return args


def extract_info(url: str, cookies: str | None = None) -> dict:
    """Extract metadata + available formats from a URL using yt-dlp --dump-json."""
    args = _build_base_args(cookies) + [
        "--dump-json",
        "--no-download",
        "--flat-playlist",
        url,
    ]

    proc = subprocess.run(
        args,
        capture_output=True,
        text=True,
        input=cookies if cookies else None,
        timeout=30,
    )

    if proc.returncode != 0:
        raise RuntimeError(f"yt-dlp error: {proc.stderr.strip()[:200]}")

    data = json.loads(proc.stdout)

    # Build format list
    formats = []
    seen = set()

    for f in data.get("formats", []):
        vcodec = f.get("vcodec", "none")
        acodec = f.get("acodec", "none")
        height = f.get("height")
        format_id = f.get("format_id", "")

        if vcodec != "none" and height:
            quality = f"{height}p"
            ftype = "video"
        elif acodec != "none" and vcodec == "none":
            abr = f.get("abr", 0)
            quality = f"{int(abr)}kbps" if abr else f.get("format_note", "audio")
            ftype = "audio"
        else:
            continue

        key = f"{quality}_{f.get('ext')}"
        if key in seen:
            continue
        seen.add(key)

        formats.append({
            "quality": quality,
            "format_id": format_id,
            "ext": f.get("ext", "mp4"),
            "filesize": f.get("filesize") or f.get("filesize_approx"),
            "type": ftype,
        })

    # Add MP3 320kbps and FLAC options
    formats.append({
        "quality": "MP3 320kbps",
        "format_id": "mp3-320",
        "ext": "mp3",
        "filesize": None,
        "type": "audio",
    })
    formats.append({
        "quality": "FLAC Lossless",
        "format_id": "flac-best",
        "ext": "flac",
        "filesize": None,
        "type": "audio",
    })

    # Sort: video by height desc, audio by bitrate desc
    formats.sort(key=lambda x: (
        0 if x["type"] == "video" else 1,
        -int(''.join(filter(str.isdigit, x["quality"])) or 0),
    ))

    return {
        "title": data.get("title", "Unknown"),
        "author": data.get("uploader", data.get("channel", "Unknown")),
        "thumbnail": data.get("thumbnail", ""),
        "duration": data.get("duration", 0),
        "formats": formats,
        "platform": data.get("extractor_key", "unknown").lower(),
    }


def stream_download(url: str, format_id: str, cookies: str | None = None) -> Generator[bytes, None, None]:
    """Stream a download to stdout via yt-dlp subprocess — zero disk writes."""
    args = [
        "yt-dlp",
        "--no-check-certificates",
        "-f", format_id,
        "-o", "-",  # output to stdout
        url,
    ]

    proc = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE if cookies else None,
    )

    if cookies and proc.stdin:
        proc.stdin.write(cookies.encode())
        proc.stdin.close()

    try:
        while True:
            chunk = proc.stdout.read(64 * 1024)  # 64KB chunks
            if not chunk:
                break
            yield chunk
    finally:
        proc.stdout.close()
        proc.wait()
