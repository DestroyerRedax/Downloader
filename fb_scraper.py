"""Facebook photo scraper for profile/cover photos using cookies."""

import re
import requests
from bs4 import BeautifulSoup


def scrape_facebook_photos(url: str, cookies_txt: str | None = None) -> dict:
    """
    Scrape high-res Facebook photos from a photo URL.
    Requires cookies for authentication.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    session = requests.Session()
    session.headers.update(headers)

    # Parse cookies if provided
    if cookies_txt:
        for line in cookies_txt.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 7:
                session.cookies.set(parts[5], parts[6], domain=parts[0])

    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Try to find high-res image
        img_urls = []

        # Method 1: og:image meta tag
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            img_urls.append(og_image["content"])

        # Method 2: data-store attributes
        for tag in soup.find_all(attrs={"data-store": True}):
            store = tag.get("data-store", "")
            urls = re.findall(r'https?://[^"\\]+\.(?:jpg|jpeg|png|webp)[^"\\]*', store)
            img_urls.extend(urls)

        if not img_urls:
            raise RuntimeError("Could not find image URL. Try providing cookies.")

        best_url = img_urls[0]
        title = soup.find("title")
        title_text = title.get_text() if title else "Facebook Photo"

        return {
            "title": title_text,
            "author": "Facebook",
            "thumbnail": best_url,
            "duration": 0,
            "platform": "facebook",
            "formats": [
                {
                    "quality": "Original",
                    "format_id": "fb-photo-orig",
                    "ext": "jpg",
                    "filesize": None,
                    "type": "video",  # treated as downloadable
                }
            ],
        }
    except Exception as e:
        raise RuntimeError(f"Facebook scraping failed: {str(e)}")
