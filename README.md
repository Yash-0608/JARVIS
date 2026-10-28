# JARVIS

A local-first personal AI assistant for Windows and Android. The starter includes a Qwen/Ollama gateway, multilingual speech transcription, Unicode-aware tokenization, a conservative intent previewer, a clean white React UI, and an Android companion pairing/chat starter.

> **Status: working foundation, not production-complete.** Social messaging needs Meta developer credentials and supported account types. Incoming social inbox sync/webhooks, full Android call handling, call logs, remote device controls, other social platforms, and always-on full-duplex voice are not implemented. A zero-bug guarantee is not possible without CI results and testing on your own Windows PC and Android phone.

## Repository layout

- `backend/`: FastAPI local API, Ollama gateway, Faster-Whisper ASR, intent preview, secure-ish development pairing handshake.
- `frontend/`: React + Vite UI for chat, voice input/reply, phone pairing and connector status.
- `android/`: Kotlin/Jetpack Compose companion with pairing, push-to-talk speech service, phone chat, text-to-speech, and a safe dialer handoff.
- `docs/`: architecture, integration boundaries and acceptance-test plan.
- `.github/workflows/ci.yml`: backend/frontend/Android build checks.

## Requirements

- Windows 10/11
- Python 3.11+
- Node.js 20+
- Ollama reachable from the Python backend. For Docker, publish Ollama's API to the host and keep it on a trusted local network.
- Android Studio + JDK 17 + Android SDK 35 to build the companion.

## 1. Start the Windows backend

In PowerShell:

```powershell
cd D:\Projects\JARVIS\backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Set these values in `backend/.env`:

- `OLLAMA_BASE_URL=http://127.0.0.1:11434` (if Ollama's published host port is 11434)
- `OLLAMA_MODEL=` followed by the **exact** installed tag shown by `ollama list`
- `JARVIS_API_KEY=` a long unique random string

Start the API:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Check `http://127.0.0.1:8000/api/health`. Interactive API docs are at `http://127.0.0.1:8000/docs`. The UI sends `X-JARVIS-API-Key` on protected desktop API calls.

## 2. Start the Windows UI

In another PowerShell window:

```powershell
cd D:\Projects\JARVIS\frontend
npm install
Copy-Item .env.example .env
notepad .env
npm run dev
```

Set `VITE_API_BASE_URL=http://127.0.0.1:8000` and set `VITE_JARVIS_API_KEY` to the same value as `JARVIS_API_KEY` in the backend. Open the Vite URL printed in the terminal (usually `http://127.0.0.1:5173`).

Never commit either `.env` file. The example strings are placeholders; replace them with your own value.

## 3. Connect the Android companion

1. Open the `android/` folder in Android Studio. Allow Gradle sync and install the app on your phone.
2. For the first LAN-development pairing only, stop the backend and restart it with `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
3. Put Windows and Android on the same **trusted private Wi-Fi**. Run `ipconfig` on Windows and find its LAN IPv4 address.
4. In Windows Firewall, allow inbound port 8000 only on the Private profile; do not create a router port-forward.
5. In the phone app, enter `http://WINDOWS-LAN-IP:8000`, the display name, and the one-time code shown on the desktop's **Phone & devices** page.
6. Accept the phone request in the desktop UI. The phone receives a per-device token and can chat through the paired-device API.

The phone pairing bootstrap uses a single-use expiring code and client secret; phone chat requires the per-device token. This is **development-only HTTP on a trusted LAN**, not an encrypted production pairing system. Do not expose the backend to the public internet or an untrusted network. The desktop's API key is a local-development control, not a substitute for TLS or authentication hardening.

## Capability status

| Capability | Status |
|---|---|
| Qwen via Ollama | Gateway implemented; must be checked against your running model tag |
| Speech recognition + dominant-language metadata | Implemented with Faster-Whisper; first run downloads weights |
| Spoken assistant replies on Windows | Uses browser speech synthesis; available voices depend on Windows/browser |
| Tokenization + action intent preview | Implemented; heuristic classifier, not an autonomous planner |
| Android pairing | Request/accept handshake and companion starter implemented; hardware validation still required |
| Voice conversation on Android | Push-to-talk through the installed Android speech-recognition service and TTS; provider may use online services |
| Phone calling | Dialer handoff only; no call answering, incoming call detection, call-history reading, or background call management |
| WhatsApp / Instagram outbound | Confirmed text-send routes through official Meta APIs; requires credentials and an eligible account |
| Arbitrary Windows task execution | Not enabled; only safe allow-listed executor design is intended |

See [Architecture](docs/ARCHITECTURE.md), [Integration requirements](docs/INTEGRATIONS.md), [Android setup](android/README.md), and [Testing plan](docs/TESTING.md).

The Connections page includes explicitly confirmed WhatsApp/Instagram outbound text forms. Configure the corresponding Meta credentials in backend/.env; real delivery depends on the provider accepting the request. Incoming inbox sync and webhooks are a later stage.

## Safety baseline

- Do not send personal chat data to third-party services without choosing to do so.
- Do not pass arbitrary shell commands from the model to the operating system.
- Confirm sensitive actions (messages, calls, deleting/moving files, purchases) and verify completion.
- Keep social tokens in `.env` on the backend, never in React code.
- Real social-platform access is permissioned and constrained. The application will not bypass account security, scrape private accounts, or automate actions that the provider does not support.
