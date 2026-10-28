"""Restricted local browser automation for explicitly requested YouTube playback.

Playwright runs on a dedicated worker thread. This avoids Windows asyncio event-loop
limitations that can raise NotImplementedError when an async browser launches from
a Windows ASGI server. The executor only navigates to YouTube search results and
opens the first matching video; it accepts no arbitrary URLs or browser scripts.
"""
from __future__ import annotations

import asyncio
import queue
import re
import threading
from datetime import date
from pathlib import Path
from urllib.parse import quote_plus

_jobs: queue.Queue = queue.Queue()
_worker_guard = threading.Lock()
_worker_thread: threading.Thread | None = None


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
    # Strip a common natural-language article without trying to rewrite the search.
    query = re.sub(r"^(?:the|a|an)\s+", "", query, flags=re.IGNORECASE)
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
    if re.match(r"^(?:https?://|www\.)", cleaned, flags=re.IGNORECASE):
        raise ValueError("Pass search terms, not a URL.")
    return cleaned


def _open_video(context, query: str) -> dict[str, object]:
    """Run Playwright operations from the one thread that owns its sync API."""
    page = context.pages[0] if context.pages else context.new_page()
    search_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    page.goto(search_url, wait_until="domcontentloaded", timeout=45_000)

    # Handle a basic consent prompt when it is displayed, without entering credentials.
    for selector in ("button:has-text('Accept all')", "button:has-text('I agree')"):
        try:
            page.locator(selector).first.click(timeout=900)
            break
        except Exception:
            pass

    video_link = page.locator("ytd-video-renderer a#video-title").first
    try:
        video_link.wait_for(state="visible", timeout=25_000)
    except Exception:
        # YouTube may change its result markup; this fallback is still scoped to
        # video links on YouTube search results, not arbitrary page controls.
        video_link = page.locator("a#video-title[href*='/watch']").first
        video_link.wait_for(state="visible", timeout=10_000)

    title = (video_link.get_attribute("title") or video_link.inner_text() or "YouTube video").strip()
    video_link.click(timeout=10_000)
    page.wait_for_url(
        re.compile(r"https?://(?:www\.)?youtube\.com/watch"),
        timeout=20_000,
    )

    # Clicking a video often begins playback immediately. If a visible play overlay
    # remains, click it once; browser autoplay rules may still require user interaction.
    try:
        play_button = page.locator("button.ytp-large-play-button")
        play_button.wait_for(state="visible", timeout=2_000)
        play_button.click(timeout=3_000)
    except Exception:
        pass

    return {
        "ok": True,
        "query": query,
        "title": title,
        "url": page.url,
        "message": "Opened the first matching YouTube video. Confirm playback in the browser player.",
    }


def _browser_worker() -> None:
    """Own the Playwright sync runtime on this dedicated thread."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        context = None
        try:
            while True:
                item = _jobs.get()
                if item is None:
                    _jobs.task_done()
                    break
                query, done, result_box = item
                try:
                    if context is None:
                        profile_dir = Path(__file__).resolve().parents[1] / ".jarvis-browser-profile"
                        profile_dir.mkdir(parents=True, exist_ok=True)
                        launch_args = {
                            "user_data_dir": str(profile_dir),
                            "headless": False,
                            "no_viewport": True,
                            "args": ["--autoplay-policy=no-user-gesture-required"],
                        }
                        try:
                            # Prefer installed Chrome to avoid a second browser download.
                            context = playwright.chromium.launch_persistent_context(
                                channel="chrome", **launch_args
                            )
                        except Exception:
                            try:
                                context = playwright.chromium.launch_persistent_context(**launch_args)
                            except Exception as launch_error:
                                raise RuntimeError(
                                    "No usable browser could be launched. Install Google Chrome, "
                                    "or run 'python -m playwright install chromium' in the "
                                    "activated backend environment."
                                ) from launch_error
                    result_box["value"] = _open_video(context, query)
                except Exception as exc:
                    result_box["error"] = (
                        f"Could not open a YouTube video ({type(exc).__name__}): {str(exc)[:250]}"
                    )
                finally:
                    done.set()
                    _jobs.task_done()
        finally:
            if context is not None:
                try:
                    context.close()
                except Exception:
                    pass


def play_youtube_search(query: str) -> dict[str, object]:
    """Queue YouTube playback on the dedicated browser thread and wait for the result."""
    global _worker_thread
    query = _validate_query(query)
    done = threading.Event()
    result_box: dict[str, object] = {}

    # Serialize startup/enqueue against shutdown so an action cannot be queued
    # after the worker's shutdown marker.
    with _worker_guard:
        if _worker_thread is None or not _worker_thread.is_alive():
            _worker_thread = threading.Thread(
                target=_browser_worker,
                name="JARVIS-Chromium-Worker",
                daemon=True,
            )
            _worker_thread.start()
        _jobs.put((query, done, result_box))

    if not done.wait(timeout=90):
        raise RuntimeError("The browser did not finish within 90 seconds. Check the Chromium window.")
    if "error" in result_box:
        raise RuntimeError(str(result_box["error"]))
    result = result_box.get("value")
    if not isinstance(result, dict):
        raise RuntimeError("The browser returned no result.")
    return result


def close_browser() -> None:
    """Close the dedicated browser worker cleanly when the backend stops."""
    global _worker_thread
    with _worker_guard:
        worker = _worker_thread
        if worker is None:
            return
        _worker_thread = None
        _jobs.put(None)
    worker.join(timeout=12)
