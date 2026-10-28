# JARVIS architecture

## Flow

1. Input: text or microphone audio.
2. ASR: speech-to-text with dominant language metadata.
3. Normalization/tokenization: preserve Unicode/Devanagari and produce tokens for diagnostics.
4. Intent routing: transform a request into a typed intent; unknown/high-risk intents require clarification.
5. Planner: LLM proposes structured tool calls; the server validates each tool against schemas and policy.
6. Execution: only allow-listed connectors with minimum permissions.
7. Verification: check connector response/state where available.
8. Response: return status and optionally text-to-speech.

## Services

- React/Vite UI: `frontend/`.
- FastAPI local gateway: `backend/app/main.py`.
- Ollama: local model inference through configured HTTP endpoint.
- Android companion: `android/`, pairing/request/accept flow before introducing privileged permissions.

## Trust boundaries

The model is not trusted to invent successful outcomes or bypass confirmation. Tool calls are validated server-side. Public internet access, social platform accounts, Android system permissions, and telephony are separate trust boundaries. Use authenticated encrypted transport before using the pairing flow over anything other than a trusted development LAN.
