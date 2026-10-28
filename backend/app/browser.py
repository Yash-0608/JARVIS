"""Restricted local Chromium automation for explicitly requested YouTube playback.

The executor never accepts arbitrary URLs or arbitrary browser scripts. It only
searches YouTube and opens the first matching video in a dedicated Chromium profile.
"""
from __future__ import annotations

import asyncio
import re
from datetime import date
from pathlib import Path
from urllib.parse import quote_plus

_YOUTUBE_HOST = "www.youtube.com"
_browser_lock = asyncio.Lock()
_playwright = None
_context = None
_page = None


def parse_explicit_youtube_request(message: str) -> str | None:
    """Return a search phrase only for clear YouTube playback requests."""
    if not isinstance(message, str):
        return None
    text = " ".join(message.strip().split())
    lower = text.casefold()
    if "youtube" not in lower:
        return None
    if not re.search(r"\b(play|watch|listen|start playing)\b", lower):
        return None

    if re.search(r"\b(latest|newest|new|trending)\s+(song|music|track)\b", lower):
        return f"latest song official music video {date.today().year}"

    pattern = re.compile(
        r"\b(?:search(?:\s+for)?|play|listen(?:\s+to)?|watch)\s+(.+?)"
        r"(?=\s+(?:on|in)\s+youtube\b|\s+and\s+play(?:\s+(?:it|that))?\b|"
        r"\s+and\s+watch\b|[.!?]|$)",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return None
    query = match.group(1).strip(" \"'.,!?")
    if query.casefold().startswith("for "):
        query = query[4:].strip()
    if len(query) < 2 or len(query) > 160:
        return None
    return query


def _validate_query(query: object) -> str:
    if not isinstance(query, str):
        raise ValueError("The YouTube search query must be text.")
    cleaned = " ".join(query.split()).strip()
    if not cleaned:
        raise ValueError("Enter what you want to search for on YouTube.")
    if len(cleaned) > 160:
        raise ValueError("The YouTube search query must be 160 characters or fewer.")
    if any(ord(char) < 32 for char in cleaned):
        raise ValueError("The YouTube search query contains unsupported control characters.")
    return cleaned


async def play_youtube_search(query: str) -> dict[str, object]:
    """Open YouTube search, select the first video, and leave Chromium open."""
    global _playwright, _context, _page
    query = _validate_query(query)
    async with _browser_lock:
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Browser support is not installed. In backend, run "
                "'pip install -r requirements.txt' and 'python -m playwright install chromium'."
            ) from exc

        try:
            if _context is None:
                profile_dir = Path.home() / ".jarvis" / "chromium-profile"
                profile_dir.mkdir(parents=True, exist_ok=True)
                _playwright = await async_playwright().start()
                try:
                    _context = await _playwright.chromium.launch_persistent_context(
                        user_data_dir=str(profile_dir),
                        headless=False,
                        no_viewport=True,
                        args=["--autoplay-policy=no-user-gesture-required"],
                    )
                except Exception:
                    await _playwright.stop()
                    _playwright = None
                    raise
                _page = _context.pages[0] if _context.pages else await _context.new_page()

            if _page is None or _page.is_closed():
                _page = await _context.new_page()

            search_url = f"https://{_YOUTUBE_HOST}/results?search_query={quote_plus(query)}"
            await _page.goto(search_url, wait_until="domcontentloaded", timeout=45_000)

            # Dismiss a consent prompt when one is shown; do not enter account details.
            for selector in (
                "button:has-text('Accept all')",
                "button:has-text('I agree')",
            ):
                try:
                    await _page.locator(selector).first.click(timeout=900)
                    break
                except Exception:
                    pass

            video_link = _page.locator("ytd-video-renderer a#video-title").first
            await video_link.wait_for(state="visible", timeout=25_000)
            title = (await video_link.get_attribute("title")) or (await video_link.inner_text())
            await video_link.click(timeout=10_000)
            await _page.wait_for_url(re.compile(r"https?://(?:www\.)?youtube\.com/watch"), timeout=20_000)

            # Clicking the result should normally start playback. If YouTube shows
            # its explicit play overlay, click it once; otherwise leave playback alone.
            play_button = _page.locator("button.ytp-large-play-button")
            try:
                await play_button.wait_for(state="visible", timeout=2_000)
                await play_button.click(timeout=3_000)
            except Exception:
                pass

            return {
                "ok": True,
                "query": query,
                "title": title.strip() if title else "YouTube video",
                "url": _page.url,
                "message": "Opened the first matching YouTube video in a dedicated Chromium window. Confirm playback in the player.",
            }
        except Exception as exc:
            error = str(exc)
            if "Executable doesn't exist" in error or "playwright install" in error.casefold():
                raise RuntimeError(
                    "Chromium is not installed for Playwright. In backend, run "
                    "'python -m playwright install chromium', then restart JARVIS."
                ) from exc
            raise RuntimeError(f"Could not open a YouTube video: {type(exc).__name__}: {error[:300]}") from exc


async def close_browser() -> None:
    """Close the dedicated browser on a clean backend shutdown."""
    global _playwright, _context, _page
    async with _browser_lock:
        if _context is not None:
            try:
                await _context.close()
            finally:
                _context = None
                _page = None
        if _playwright is not None:
            try:
                await _playwright.stop()
            finally:
                _playwright = None
