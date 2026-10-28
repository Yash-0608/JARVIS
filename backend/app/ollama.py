from typing import Any
import asyncio
import json
import httpx
from .config import settings
from . import browser

class OllamaError(RuntimeError):
    pass

def _base() -> str:
    return settings.ollama_base_url.rstrip("/")

async def status() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{_base()}/api/version")
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("Ollama version response was not an object")
            return {"connected": True, "base_url": _base(), "version": data.get("version")}
    except (httpx.HTTPError, ValueError) as exc:
        return {"connected": False, "base_url": _base(), "error": str(exc)}

async def models() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(f"{_base()}/api/tags")
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or not isinstance(data.get("models"), list):
                raise OllamaError("Ollama returned an invalid model-list response")
            valid_models = [m for m in data["models"] if isinstance(m, dict) and isinstance(m.get("name"), str)]
            return {"connected": True, "models": [{"name": m["name"], "size": m.get("size")} for m in valid_models]}
    except httpx.HTTPError as exc:
        raise OllamaError(f"Cannot reach Ollama at {_base()}: {exc}") from exc
    except ValueError as exc:
        raise OllamaError("Ollama returned invalid JSON for its model list") from exc


_BROWSER_TOOLS = [{
    "type": "function",
    "function": {
        "name": "play_youtube_search",
        "description": (
            "Open the dedicated Chromium-based browser, search YouTube, click the first "
            "matching video, and attempt playback. Use only when the user explicitly asks "
            "you to search/watch/listen/play a YouTube video or song. For 'latest song', "
            "search for the latest song and official music video for the current year. "
            "Never use for unrelated requests."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Plain YouTube search terms only, never a URL; maximum 160 characters.",
                }
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}]


def _tool_query(message: dict[str, Any]) -> str | None:
    """Accept only the one local browser tool, with strict argument parsing."""
    calls = message.get("tool_calls")
    if not isinstance(calls, list):
        return None
    for call in calls[:1]:
        if not isinstance(call, dict):
            continue
        function = call.get("function")
        if not isinstance(function, dict) or function.get("name") != "play_youtube_search":
            continue
        args = function.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                return None
        if isinstance(args, dict) and isinstance(args.get("query"), str):
            try:
                return browser._validate_query(args["query"])
            except ValueError:
                return None
    return None


async def _run_youtube_tool(query: str, selected_model: str) -> dict[str, Any]:
    try:
        result = await asyncio.to_thread(browser.play_youtube_search, query)
    except Exception as exc:
        return {
            "model": selected_model,
            "done": True,
            "action": {"type": "browser", "ok": False},
            "response": f"I understood the YouTube request, but couldn't start playback. {exc}",
        }
    return {
        "model": selected_model,
        "done": True,
        "action": result,
        "response": (
            f"Opened YouTube for: {result['query']}\n"
            f"Selected video: {result['title']}\n"
            f"{result['url']}\n"
            "I clicked the first matching result. Check the browser if playback has not started."
        ),
    }


async def chat(message: str, model: str | None = None) -> dict[str, Any]:
    selected = (model or settings.ollama_model).strip()
    if len(selected) > 120 or not selected:
        raise OllamaError("Invalid model name")
    messages = [
        {
            "role": "system",
            "content": (
                "You are JARVIS, a friendly, clear personal assistant. Understand Hindi, "
                "Marathi, English and Hinglish when possible. Never claim an external action "
                "was completed unless a tool confirms it. Never request secrets. A restricted "
                "YouTube playback tool is available: use it only when the user explicitly asks "
                "to search, watch, listen to or play something on YouTube. It can only search "
                "YouTube and open the first matching result; it cannot perform arbitrary browser "
                "actions. For consequential actions, require the dedicated confirmed tool."
            ),
        },
        {"role": "user", "content": message},
    ]
    payload = {
        "model": selected,
        "stream": False,
        "messages": messages,
        "tools": _BROWSER_TOOLS,
        "options": {"temperature": 0.2},
    }
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{_base()}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or not isinstance(data.get("message"), dict):
                raise OllamaError("Ollama returned an invalid chat response")
            model_message = data["message"]

            # Prefer Qwen's structured tool decision. If the model does not emit a
            # tool call for an unambiguous direct command, use the same allow-listed
            # parser as a deterministic fallback so supported wording still works.
            query = _tool_query(model_message)
            if query is None:
                query = browser.parse_explicit_youtube_request(message)
            if query is not None:
                return await _run_youtube_tool(query, selected)

            return {
                "model": selected,
                "response": model_message.get("content", ""),
                "done": data.get("done", False),
            }
    except httpx.HTTPError as exc:
        # Preserve the explicit, allow-listed browser command even when this
        # Ollama build or model cannot process the tools schema.
        fallback_query = browser.parse_explicit_youtube_request(message)
        if fallback_query is not None:
            return await _run_youtube_tool(fallback_query, selected)
        raise OllamaError(f"Ollama chat failed at {_base()}: {exc}") from exc
    except ValueError as exc:
        raise OllamaError("Ollama returned invalid JSON for chat") from exc
