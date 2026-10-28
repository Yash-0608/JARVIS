# Integration matrix

| Integration | Current implementation | Requirements before real use |
|---|---|---|
| Ollama/Qwen | Chat, model listing and status gateway | Model tag, reachable Ollama URL, local network configuration |
| Microphone ASR | Faster-Whisper transcription + dominant language | Microphone permission, downloaded speech model, testing with target accents/languages |
| Windows automation | Intent preview only | Per-action allow-list, Windows executor, confirmation, verification and rollback strategy |
| Android phone | One-time pairing code, request/accept, per-device token for phone chat | Build/install app, same trusted LAN initially, OS permissions, actual device testing |
| WhatsApp outbound | Confirmed text-send route through Meta WhatsApp Cloud API | Business Platform setup, phone-number ID, access token, eligible recipient/opt-in and Meta permissions |
| Instagram outbound | Confirmed text-send route through Meta Graph API | Professional account, business/account ID, access token and messaging permission; recipient must be an allowed Instagram-scoped ID |
| Incoming WhatsApp/Instagram | Not implemented; webhook and inbox synchronization still required | HTTPS-reachable webhook, signature validation, subscription/configuration and privacy retention design |
| Calls | Android companion opens the system dialer; direct call control is not implemented | Separate Android telephony/default-dialer design, OS roles/permissions, robust in-call UI and hardware testing |
| Other social platforms | Adapter pattern planned; no live connector yet | Each provider's official API, OAuth/permissions, review and rate limits |

## Meta environment variables

Configure these server-side only in backend/.env, copied from .env.example:

- META_GRAPH_BASE_URL — default https://graph.facebook.com.
- META_GRAPH_VERSION — API version string; use a version currently supported by your Meta app.
- WHATSAPP_CLOUD_API_TOKEN and WHATSAPP_PHONE_NUMBER_ID.
- INSTAGRAM_GRAPH_API_TOKEN and INSTAGRAM_BUSINESS_ACCOUNT_ID.

The UI enables send forms only when the required environment values are present, and each outbound send requires a checkbox confirming the exact recipient and message. The backend also requires confirmed=true; it will not infer confirmation from an LLM response. A provider's HTTP success means accepted/submitted, not necessarily delivered; check provider status/webhooks.

WhatsApp Cloud API is designed for the WhatsApp Business Platform, not as an unrestricted bridge to a personal WhatsApp account. The configured Instagram adapter targets the Instagram API with Instagram Login (`graph.instagram.com`) and expects the professional account ID plus a token with the supported Instagram messaging permission. The distinct Facebook Login flow uses a Page token and Page-scoped endpoint; don't mix its token/IDs with this Instagram Login configuration. Recipient IDs must come from a supported conversation. This scaffold is not a universal personal-account DM gateway, and it does not support arbitrary cold DMs. Never use browser-password scraping to bypass provider APIs.

## Security

All desktop-facing API endpoints require X-JARVIS-API-Key, set in backend .env and mirrored as VITE_JARVIS_API_KEY in the local frontend .env. This is a local development control, not a production secrets boundary. Phone pairing uses short-lived single-use codes, a random pairing secret and a per-device token. The current pairing registry is in memory and resets on restart. Do not expose the HTTP backend to the public internet. Production deployment needs authenticated TLS, a persistent device registry, revocation, rate limiting, audit controls and secret rotation.
