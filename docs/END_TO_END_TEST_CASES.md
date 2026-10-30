# JARVIS end-to-end acceptance test cases

**Goal:** prove that JARVIS performs an action, not merely that a button responds. Record Pass / Fail / Blocked / Not tested, actual result, device details, and logs for each test. Keep mocked CI results separate from real-device results.

## A. Prompt and model response

| ID | Test | Steps | Expected result |
|---|---|---|---|
| CHAT-01 | Basic prompt | Ask “What is Python?” | One prompt is sent and a non-empty answer from the selected model is displayed. |
| CHAT-02 | Empty prompt | Submit whitespace only | No request or empty chat bubble is created. |
| CHAT-03 | Keyboard send | Press Enter, then Shift+Enter | Enter sends; Shift+Enter inserts a newline. |
| CHAT-04 | Long prompt | Submit a prompt near 12,000 characters | Valid input is handled; invalid input gets a clear validation message. |
| CHAT-05 | Backend offline | Stop FastAPI and send a prompt | Clear connection error; UI remains usable and does not claim success. |
| CHAT-06 | Ollama offline | Stop Ollama while API remains online | Clear model-service error; no fabricated answer. |
| CHAT-07 | Rapid submission | Double-click Send / press Enter repeatedly | No duplicate submission or duplicate assistant response. |
| MODEL-01 | Model discovery | Start Ollama and refresh status | Only locally installed model tags are listed. |
| MODEL-02 | Qwen baseline | Run a fixed prompt set on the configured Qwen tag | Record answer quality, latency, tokens/sec, RAM/VRAM and failures. |
| MODEL-03 | Model switching | Select another installed model and repeat the same prompts | Selected tag is sent to Ollama; no silent fallback. |
| MODEL-04 | Invalid model | Select/request an uninstalled tag | Clear model error is returned. |
| MODEL-05 | Model capability | Test reasoning, coding, Hindi, Marathi and Hinglish prompts | Record factual accuracy and language quality rather than relying on model names. |

## B. Voice recognition and voice replies

| ID | Test | Steps | Expected result |
|---|---|---|---|
| VOICE-01 | Microphone permission | Start recording and grant permission | Recording indicator becomes active and audio is captured. |
| VOICE-02 | Permission denied | Deny microphone access | Clear error; app does not crash. |
| VOICE-03 | English | Speak a short English prompt | Transcript, language and confidence appear; prompt is submitted once. |
| VOICE-04 | Hindi | Speak a Hindi prompt | Transcript is compared with the spoken words; language metadata is plausible. |
| VOICE-05 | Marathi | Speak a Marathi prompt | Transcript is compared with the spoken words; language metadata is plausible. |
| VOICE-06 | Hinglish | Mix Hindi/Marathi and English | Code-switching quality is recorded; do not assume perfect recognition. |
| VOICE-07 | Silence/noise | Record silence and background noise | Empty/poor transcript is reported; no unintended action runs. |
| VOICE-08 | Stop recording | Start and stop microphone capture | Microphone tracks are released and the indicator resets. |
| VOICE-09 | Spoken answer | Enable voice output and receive an answer | Browser speech synthesis speaks the response where supported. |
| VOICE-10 | Mute | Disable voice output during/after speech | Current utterance is cancelled and new replies remain silent. |
| VOICE-11 | Unsupported browser | Test without MediaRecorder/microphone support | Helpful fallback; text chat remains available. |
| VOICE-12 | Continuous voice expectation | Speak without pressing the microphone button | Confirm current desktop limitation: push-to-talk, not always-listening full-duplex voice. |

## C. Actions and execution verification

| ID | Test | Steps | Expected result |
|---|---|---|---|
| ACT-01 | YouTube playback | Ask JARVIS to search for a named song on YouTube and play it | Dedicated browser opens search, selects a result and returns the real browser result; verify playback visually. |
| ACT-02 | Browser unavailable | Disable supported browser and request playback | Clear failure; no false success claim. |
| ACT-03 | Consent/autoplay | Test YouTube consent and autoplay restrictions | Manual interaction requirement is communicated. |
| ACT-04 | Unsupported action | Ask for an unimplemented Windows action | JARVIS says it is unsupported and does not claim completion. |
| ACT-05 | Social confirmation | Prepare a test message without confirming | No outbound message is sent. |
| ACT-06 | Edited social message | Confirm, then change recipient or text | Confirmation must be repeated. |
| ACT-07 | Provider rejection | Use invalid/ineligible test credentials or recipient | Provider error shown; HTTP acceptance is not treated as delivery. |
| ACT-08 | Android dialer | Use the Calls panel | System dialer opens; no call is placed automatically. |

## D. Windows ↔ Android connectivity

| ID | Test | Steps | Expected result |
|---|---|---|---|
| LINK-01 | Generate code | Generate pairing code on desktop | Short-lived code and expiry are shown. |
| LINK-02 | Request pairing | Enter code on Android | Pending request appears on desktop. |
| LINK-03 | Accept | Accept pending phone request | Phone receives a device token and can chat. |
| LINK-04 | Reject | Reject pending request | Phone does not receive usable access. |
| LINK-05 | Expired code | Wait for expiry and submit code | Request is rejected. |
| LINK-06 | Replay | Reuse a consumed code | Second request is rejected. |
| LINK-07 | Revoke | Revoke a linked phone | Phone disappears from linked devices and its next chat request is denied. |
| LINK-08 | Wrong network | Put devices on separate networks | Connection fails clearly; no false connected state. |
| LINK-09 | Wi-Fi interruption | Disconnect/reconnect phone Wi-Fi | UI reflects state and recovery is tested. |
| LINK-10 | Backend restart | Restart backend after pairing | Current in-memory pairing limitation is understood; re-pair if state is lost. |
| LINK-11 | Firewall | Block private-network port 8000 | Pairing failure is diagnosable. |
| LINK-12 | CORS revoke | Revoke device from Vite UI on localhost:5173 | Browser DELETE preflight succeeds and the device is revoked. |

## E. UI, navigation and accessibility

| ID | Test | Steps | Expected result |
|---|---|---|---|
| UI-01 | Desktop layout | Open at 1366×768 and 1920×1080 | Sidebar, topbar, cards, chat and footer do not overlap. |
| UI-02 | Tablet | Open at 768–1024 px | Content reflows and controls remain reachable. |
| UI-03 | Small mobile | Open at 320, 375 and 430 px | No horizontal overflow; icon navigation has accessible names/tooltips. |
| UI-04 | Navigation | Visit Assistant, Phone & devices, Connections | Correct page opens and active state is clear. |
| UI-05 | Wordmark | Inspect sidebar logo | “JARVIS” uses a distinct display font with readable fallback. |
| UI-06 | Keyboard | Use Tab, Shift+Tab, Enter and Space | All interactive controls are reachable with visible focus. |
| UI-07 | Screen reader | Inspect icon-only navigation and buttons | Meaningful accessible names and active-page state are exposed. |
| UI-08 | Reduced motion | Enable OS reduced-motion preference | Decorative motion is reduced. |
| UI-09 | Long response | Display very long messages | Text wraps without clipped controls or horizontal overflow. |
| UI-10 | Error state | Trigger API and microphone errors | Error is readable and does not cover critical controls. |

## F. Security and reliability

| ID | Test | Steps | Expected result |
|---|---|---|---|
| SEC-01 | Missing API key | Call protected endpoint without key | Request rejected. |
| SEC-02 | Invalid API key | Call protected endpoint with wrong key | Request rejected. |
| SEC-03 | Unpaired phone | Call phone chat without valid device token | Request rejected. |
| SEC-04 | Revoked phone | Reuse token after revocation | Request rejected. |
| SEC-05 | Oversized audio | Upload audio larger than 20 MB | Request rejected with size error. |
| SEC-06 | Invalid audio type | Upload text file as audio | Request rejected. |
| SEC-07 | Client secrets | Inspect built frontend assets and browser network | Provider tokens/backend secrets are not embedded in client assets. |
| SEC-08 | Network exposure | Inspect bind address, firewall and router | Development HTTP API is not exposed publicly or port-forwarded. |
| SEC-09 | Pairing rate limit | Send repeated invalid pairing attempts | Rate limit activates as configured. |
| SEC-10 | Shutdown | Stop backend after browser use | Browser worker closes without blocking ASGI shutdown. |

## Automated checks

Run these in the project directories:

- Backend: `python -m pytest -q` from `backend/`.
- Frontend: `npm run build` from `frontend/`.
- Android: `gradle :app:assembleDebug` from `android/`.

The new backend interaction tests mock Ollama and speech transcription. They verify API contracts, not live model inference or real microphone accuracy. CI does not prove actual browser playback, social message delivery, or physical phone connectivity.

## Release gate

Do not call JARVIS fully verified until every applicable test has a recorded result on the target Windows laptop and Android phone. A successful HTTP response is not proof that an external action completed; verify the resulting state wherever possible. The current pairing implementation is development-only HTTP on a trusted LAN and must not be exposed to the public internet.
