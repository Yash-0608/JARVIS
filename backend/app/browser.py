"""Restricted local browser automation for explicitly requested YouTube playback.

The executor only searches YouTube and opens the first matching video. It does not
accept arbitrary URLs, execute page-provided scripts, or interact with unrelated sites.
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path
from datetime import date
from urllib.parse import quote_plus

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
    if "youtube" not in lower or not re.search(r"\b(play|watch|listen|playing)\b", lower):
        return None

    if re.search(r"\b(latest|newest|new|trending)\s+(?:song|music|track)\b", lower):
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
    if any(ord(char) < 32 for char in query):
        raise ValueError("The YouTube search query contains unsupported control characters.")
    cleaned = " ".join(query.split()).strip()
    if not cleaned or len(cleaned) > 160:
        raise ValueError("The YouTube search query must contain 1–160 characters.")
    if re.match(r"^(?:https?://|www\\.)", cleaned, flags=re.IGNORECASE):
        raise ValueError("Pass search terms, not a URL.")
    return cleaned


async def play_youtube_search(query: str) -> dict[str, object]:
    """Open YouTube search, select the first video, and leave the browser open."""
    global _playwright, _context, _page
    query = _validate_query(query)
    async with _browser_lock:
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Browser support is missing. In the backend folder run "
                "'pip install -r requirements.txt'. If needed, also run "
                "'python -m playwright install chromium'."
            ) from exc

        try:
            if _context is None:
                # Keep the browser profile in the repo's backend folder (which can
                # live on D:), separate from the user's everyday browsing profile.
                profile_dir = Path(__file__).resolve().parents[1] / ".jarvis-browser-profile"
                profile_dir.mkdir(parents=True, exist_ok=True)
                _playwright = await async_playwright().start()
                launch_args = {
                    "user_data_dir": str(profile_dir),
                    "headless": False,
                    "no_viewport": True,
                    "args": ["--autoplay-policy=no-user-gesture-required"],
                }
                try:
                    # Prefer installed Google Chrome (Chromium engine) to save disk.
                    _context = await _playwright.chromium.launch_persistent_context(
                        channel="chrome", **launch_args
                    )
                except Exception:
                    # Fall back to Playwright-managed Chromium if Chrome is unavailable.
                    try:
                        _context = await _playwright.chromium.launch_persistent_context(
                            **launch_args
                        )
                    except Exception as exc:
                        await _playwright.stop()
                        _playwright = None
                        raise RuntimeError(
                            "No usable browser was found. Install Google Chrome, or run "
                            "'python -m playwright install chromium' in the backend environment."
                        ) from exc
                _page = _context.pages[0] if _context.pages else await _context.new_page()

            if _page is None or _page.is_closed():
                _page = await _context.new_page()

            search_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
            await _page.goto(search_url, wait_until="domcontentloaded", timeout=45_000)

            for selector in ("button:has-text('Accept all')", "button:has-text('I agree')"):
                try:
                    await _page.locator(selector).first.click(timeout=900)
                    break
                except Exception:
                    pass

            video_link = _page.locator("ytd-video-renderer a#video-title").first
            await video_link.wait_for(state="visible", timeout=25_000)
            title = (await video_link.get_attribute("title")) or (await video_link.inner_text())
            await video_link.click(timeout=10_000)
            await _page.wait_for_url(
                re.compile(r"https?://(?:www\.)?youtube\.com/watch"),
                timeout=20_000,
            )

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
                "message": "Opened the first matching YouTube video in the browser. Confirm playback in the player.",
            }
        except Exception as exc:
            if isinstance(exc, RuntimeError) and str(exc).startswith("No usable browser"):
                raise
            raise RuntimeError(
                f"Could not open a YouTube video ({type(exc).__name__}): {str(exc)[:250]}"
            ) from exc


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
