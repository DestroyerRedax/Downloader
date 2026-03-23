"""FFmpeg audio conversion via pipes — zero disk writes."""

import subprocess
from typing import Generator


def convert_audio_stream(
    url: str,
    source_format: str,
    codec: str = "mp3",
    bitrate: str | None = "320k",
    cookies: str | None = None,
) -> Generator[bytes, None, None]:
    """
    Download audio via yt-dlp, pipe it to FFmpeg for conversion, stream the output.
    Entire pipeline runs in memory — no temp files.
    """
    # Step 1: yt-dlp downloads best audio to stdout
    ytdlp_args = [
        "yt-dlp",
        "--no-check-certificates",
        "-f", "bestaudio",
        "-o", "-",
        url,
    ]

    ytdlp_proc = subprocess.Popen(
        ytdlp_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE if cookies else None,
    )

    if cookies and ytdlp_proc.stdin:
        ytdlp_proc.stdin.write(cookies.encode())
        ytdlp_proc.stdin.close()

    # Step 2: FFmpeg converts from stdin to stdout
    ffmpeg_args = [
        "ffmpeg",
        "-i", "pipe:0",    # read from stdin
        "-vn",             # no video
        "-f", codec,       # output format
    ]

    if codec == "mp3" and bitrate:
        ffmpeg_args += ["-b:a", f"{bitrate}k" if not bitrate.endswith("k") else bitrate]
    elif codec == "flac":
        ffmpeg_args += ["-compression_level", "5"]

    ffmpeg_args += ["pipe:1"]  # output to stdout

    ffmpeg_proc = subprocess.Popen(
        ffmpeg_args,
        stdin=ytdlp_proc.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Let yt-dlp's stdout flow directly into ffmpeg's stdin
    ytdlp_proc.stdout.close()

    try:
        while True:
            chunk = ffmpeg_proc.stdout.read(64 * 1024)
            if not chunk:
                break
            yield chunk
    finally:
        ffmpeg_proc.stdout.close()
        ffmpeg_proc.wait()
        ytdlp_proc.wait()
