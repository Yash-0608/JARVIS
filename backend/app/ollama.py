from typing import Any
import httpx
from .config import settings

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

async def chat(message: str, model: str | None = None) -> dict[str, Any]:
    selected = (model or settings.ollama_model).strip()
    if len(selected) > 120 or not selected:
        raise OllamaError("Invalid model name")
    payload = {
        "model": selected,
        "stream": False,
        "messages": [
            {"role": "system", "content": "You are JARVIS, a friendly, clear personal assistant. Understand Hindi, Marathi, English and Hinglish when possible. Never claim an external action was completed unless a tool confirms it. Never request secrets. If asked to perform a consequential action, explain that the action must be confirmed by a dedicated tool."},
            {"role": "user", "content": message},
        ],
        "options": {"temperature": 0.5},
    }
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{_base()}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or not isinstance(data.get("message"), dict):
                raise OllamaError("Ollama returned an invalid chat response")
            return {"model": selected, "response": data["message"].get("content", ""), "done": data.get("done", False)}
    except httpx.HTTPError as exc:
        raise OllamaError(f"Ollama chat failed at {_base()}: {exc}") from exc
    except ValueError as exc:
        raise OllamaError("Ollama returned invalid JSON for chat") from exc
