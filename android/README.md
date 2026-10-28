# JARVIS Android Companion (starter)

Minimal white Android companion with a pairing-code request/accept flow, push-to-talk via the Android speech-recognition service, local Qwen chat via the paired-device endpoint, text-to-speech responses, and a safe `ACTION_DIAL` handoff.

## Build

1. Open the `android/` folder in Android Studio (JDK 17 recommended; Android SDK 35 required).
2. Let Gradle sync.
3. Install/run `app` on a physical Android device.

## Pairing

1. Start the Windows backend with `--host 0.0.0.0 --port 8000` **only on a trusted private Wi-Fi network**.
2. Find the Windows PC IPv4 address in `ipconfig` and allow port 8000 only on the Windows **Private** firewall profile.
3. In the phone app, replace the sample API address with `http://WINDOWS-LAN-IP:8000`, generate a code in the Windows JARVIS UI, enter it on Android, then accept the request on Windows.
4. When paired, the phone receives a per-device token and can send chat requests through `/api/phone/chat`.

The desktop API uses the `X-JARVIS-API-Key` value from `backend/.env`; the local frontend must use the same value in `frontend/.env`. Pairing bootstrap instead uses a single-use expiring code and a random client secret. This is a development-only HTTP LAN flow, not a substitute for TLS on an untrusted network. Never port-forward it to the internet.

## Voice and calls

The microphone button launches the device's installed Android speech-recognition service. Depending on the installed provider/device settings, recognition may be processed online; it is not guaranteed to be local. Responses use Android TextToSpeech. The Calls panel only opens the system dialer and does not place calls automatically. Call logs, incoming-call detection, call answering, and background notification access are **not implemented** in this starter and require separate Android permissions/roles and real-device testing.
