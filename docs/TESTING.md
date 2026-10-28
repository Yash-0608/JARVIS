# Validation plan

## Automated checks in GitHub Actions

- Backend pytest: Unicode tokenizer, intent preview phrase boundaries, API-key requirement, pairing protections, social-message confirmation/input validation, and bounded YouTube command parsing/query validation.
- Frontend production build using `npm run build`.
- Android debug APK compilation using `gradle :app:assembleDebug`.

These checks do **not** call the owner's live Ollama instance, launch Chrome/Chromium, play real YouTube videos, download/transcribe voice recordings, send real Meta messages, or install the Android app on a physical phone.

## Manual acceptance checks still required

1. Start the local Docker Ollama service and verify the selected installed Qwen model tag, text chat, and disconnect/reconnect behavior.
2. From desktop chat, run `Open YouTube, search for the latest song and play it`. Verify a separate browser window opens and a YouTube video is selected. Test autoplay restrictions, browser-not-installed handling, and browser shutdown.
2. Test speech recognition with quiet English, Hindi, Marathi, and code-mixed recordings. Confirm confidence metadata and test CPU/GPU fallback.
3. Grant/deny microphone permission and verify recording errors don't break the desktop UI.
4. Install the Android debug app on a physical device. Pair, reject, expire, replay and revoke requests; verify unpaired/revoked devices cannot access chat.
5. Test phone Wi-Fi disconnect/reconnect and ensure the app displays a truthful connection state. The current companion is not a full background service.
6. Configure an eligible Meta test account. Confirm that the UI resets approval after editing recipient or message; then test a permitted WhatsApp message and permitted Instagram conversation. Check provider delivery webhooks; HTTP acceptance is not delivery.
7. Confirm that the dialer handoff opens Android's system dialer and never places a call without the user pressing Call.
8. Run the complete flow on the target Windows PC and phone. Record OS, device, model tag and dependency versions.

## Release gate

Do not call this project bug-free or production-ready until the manual checks pass on the intended devices and the network/authentication design is hardened. The development pairing flow uses in-memory state and plain HTTP on a trusted LAN; it is not safe for public internet exposure. Incoming social inbox sync, full telephony integration, arbitrary Windows automation, and always-on full-duplex voice are out of scope for this starter.
