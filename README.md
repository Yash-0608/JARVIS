# JARVIS

A local-first personal AI assistant for Windows and Android, built around an Ollama/Qwen gateway, multilingual speech, an action orchestrator, and permission-based app/device connectors.

> Status: first scaffold. This is not yet a fully autonomous, production-ready assistant. Platform integrations require separate configuration and real-device testing.

## Architecture

- `backend/`: FastAPI service; Ollama gateway; intent router; speech API; pairing/session primitives; connector status.
- `frontend/`: React + Vite clean, white UI for chat, voice workflow, integrations and phone pairing.
- `android/`: Android companion app starter for pairing requests and permission-aware device bridge (setup instructions included).
- `docs/`: architecture, security, integration status and testing plan.

## Requirements

- Python 3.11+
- Node.js 20+
- Ollama reachable from the backend. If Ollama is in Docker, expose its API only to the local host/network you trust.
- Android Studio for building the companion app; Android debugging only for development when needed.

## Quick start (Windows PowerShell)

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open the Vite URL displayed in the terminal. Backend API docs are at `http://127.0.0.1:8000/docs`.

Set `OLLAMA_BASE_URL` to a URL reachable from the **backend process** (commonly `http://127.0.0.1:11434` for a host process). The model name is configurable using `OLLAMA_MODEL` (e.g. your installed Qwen tag). Test with `GET /api/ollama/status` and `GET /api/ollama/models`.

## Speech

The first scaffold uses Faster-Whisper for transcription and dominant-language identification. First run may download model weights. Mixed Hindi/Marathi/English speech quality varies by acoustic conditions and model; evaluate locally before relying on it for commands. Recognition produces a transcript; the router must still interpret it and ask for confirmation when needed.

## Phone pairing

The companion design uses a one-time pairing code and explicit request/accept flow. The server must be reachable from both devices on a trusted LAN, and the mobile app must show what permissions are requested. Do not expose the local API or pairing endpoint publicly. Do not use a pairing code as a replacement for transport encryption in an untrusted network.

## Integrations status

- Ollama chat/models/status: implemented scaffold.
- Speech transcription + detected language: implemented scaffold; requires model download and local performance testing.
- Tokenization + initial intent routing: implemented scaffold; intent matching is not a general-purpose planner.
- Windows actions: safe allow-listed examples only; extend deliberately.
- Android pairing: protocol and companion starter; real-device build/test still required.
- WhatsApp/Instagram and other social platforms: connector interfaces/configuration scaffolds only. Actual access depends on platform-supported APIs, account type, review, permissions and credentials. This repo does not bypass app security or scrape private accounts.
- Cellular call handling: not implemented as direct carrier-call control. Android requires a separately designed role/permission flow and testing. Start with call-state/notification integration; outgoing calls must be explicitly confirmed.

## Safety baseline

- Keep API tokens in `.env`, never commit them.
- Restrict the API to localhost while developing.
- Do not allow an LLM to execute arbitrary shell commands.
- Require confirmation before sending messages, making calls, deleting files, or changing system settings.
- Verify results and log action outcomes without storing message contents unnecessarily.

See `docs/ARCHITECTURE.md`, `docs/INTEGRATIONS.md`, and `docs/TESTING.md`.