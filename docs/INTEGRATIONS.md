# Integration matrix

| Integration | Current scaffold | Requirements before real use |
|---|---|---|
| Ollama/Qwen | Chat/model/status endpoints | Model tag, reachable Ollama URL, network configuration |
| Microphone ASR | Audio transcription endpoint | Microphone permission, downloaded speech model, test in target environment |
| Windows automation | Intent preview and safe examples | Per-action allow-list, Windows-specific implementation, confirmation/verification |
| Android phone | Pairing protocol and companion starter | Build/install app, same trusted LAN initially, OS permissions, pairing test |
| Calls | No direct telephony implementation | Android role/permissions, call-state design, regional/OS limits and real-device validation |
| WhatsApp | Connector boundary only | Supported Meta/WhatsApp API access, approved account and credentials; personal chat access is not assumed |
| Instagram | Connector boundary only | Supported Meta APIs and permissions; many personal DM operations are not available through public APIs |
| Other social platforms | Planned adapters | Each platform's official API, OAuth/permissions and rate limits |

Never paste access tokens into issues or chat. Put credentials in local environment variables or a secrets manager. API availability changes; verify each provider's current official documentation before implementing live actions.
