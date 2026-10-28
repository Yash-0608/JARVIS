# Validation plan

## Automated checks

- Unit tests for Unicode tokenization, intent parsing, input validation and confirmation policy.
- Backend API tests with mocked Ollama and speech engines.
- Frontend lint/build checks.
- Android unit tests for pairing-code format, expiry and request states.

## Manual acceptance checks

1. Start Ollama and confirm selected Qwen tag is listed.
2. Send a text prompt and confirm response is returned without calling an external service.
3. Test language detection and transcript with quiet Hindi, Marathi, English and code-mixed recordings.
4. Deny microphone permission and confirm the UI remains usable.
5. Pair Android with a one-time code; reject, accept, expire and replay a request.
6. Test phone disconnect/reconnect and invalid pairing codes.
7. Ensure social actions remain unavailable until valid official credentials are configured.
8. Ensure no messages or calls are sent without explicit user action.
9. Run on actual Windows + Android hardware, then document exact OS/device/model versions.

## Honest release gate

Do not call the project bug-free until these tests pass in CI and on the intended devices. Local connector availability, model downloads, GPU/RAM limits and third-party API permissions cannot be verified from GitHub alone.
