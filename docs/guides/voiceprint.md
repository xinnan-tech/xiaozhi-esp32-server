# 🎤 Voiceprint Recognition

Voiceprint recognition is **implemented** in this build through the built-in
`VoiceprintProvider` (`main/xiaozhi-server/core/utils/voiceprint_provider.py`).
It runs in parallel with ASR: each audio segment is sent both to ASR and to an
external voiceprint HTTP service, and the identified speaker is injected into
the LLM context for personalized responses.

> Note: the server does **not** ship a voiceprint model. You must run any
> voiceprint service that speaks the HTTP protocol below. The community
> [voiceprint-api](https://github.com/xinnan-tech/voiceprint-api) project is
> one compatible implementation (it uses ModelScope's 3D-Speaker models), but
> any service exposing the same endpoints and key scheme works.

## 🎯 What is Voiceprint Recognition?

Voiceprint recognition is a biometric technology that identifies users by their
unique voice characteristics. It allows Xiaozhi to:

- **Identify users** by their voice patterns
- **Provide personalized responses** based on who is speaking
- **Enable access control** through voice authentication
- **Support multi-user environments** with different user profiles

## ⚙️ Configuration

Enable it in `config.yaml` (single-module) or via the control console:

```yaml
voiceprint:
  # Voiceprint service address with your API key
  url: http://192.168.1.100:8005/voiceprint/health?key=abcd
  # Speakers: speaker_id,name,description
  speakers:
    - "test1,John,John is a programmer"
    - "test2,Jane,Jane is a product manager"
  # Optional: identification similarity threshold (default 0.4)
  similarity_threshold: 0.4
```

The service URL is parsed for a `key` query parameter, which is sent as the
service's API key. If `url` or `speakers` is missing, voiceprint recognition
stays disabled and a warning is logged.

## 🛠️ Service Protocol

The built-in provider expects an HTTP service exposing:

- `GET /voiceprint/health?key=<key>` — health probe; expects
  `{"status": "healthy"}` (cached after the first success).
- `POST /voiceprint/identify` — multipart form with the WAV audio and the API
  key; the service replies with the best-matching speaker id and a similarity
  score (scores below `similarity_threshold` are treated as unknown).

Speaker voice vectors are enrolled out-of-band by the service itself; the
server only sends audio and reads back identifications. See the original
[voiceprint-api](https://github.com/xinnan-tech/voiceprint-api) README for a
reference implementation of these endpoints.

## ⚖️ Privacy and Compliance

Voiceprints are biometric data (GDPR special category in the EU, BIPA in
Illinois, etc.). Before enabling:

- Run the voiceprint service **locally**; do not send family audio to third
  parties without a processor agreement.
- Obtain explicit consent from every enrolled speaker and document retention
  and deletion procedures.
- Keep `similarity_threshold` conservative; misidentification feeds the wrong
  persona into the LLM context.

## 📚 Related Documentation

- **[Voice Interaction](../features/voice-interaction.md)** — Basic voice recognition and synthesis
- **[Integrations](../features/integrations.md)** — Third-party service integrations
- **[Configuration](../configuration/basic-setup.md)** — System configuration

👉 **[Next: Available Features →](../features/voice-interaction.md)**
