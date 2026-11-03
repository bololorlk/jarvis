# ARIS / MASTEN: Windows adaptation of Matheus Jarvis

This directory is **inside the fork of the original Jarvis repository**.
Original `server.py`, `web/`, `hooks/trava.py`, shortcuts and the MIT
license remain unchanged. These adapters are the first integration layer, not
a completed desktop executable.

## What is implemented

- Local Ollama brain (`qwen2.5:3b`) with separate short conversation histories.
- Portuguese ARIS and MASTEN personas.
- Two voice presets: Antonio Neural (deeper ARIS), Fabio Neural (younger MASTEN).
- Windows microphone capture with native sample rate and proper 16 kHz resampling.
- Read-only time/date tools and a small explicit allowlist of desktop actions.
- Action planning separated from execution for a confirmation gate.

## Not implemented yet

- Wiring this module to the original `server.py` and web UI.
- End-to-end speech playback and live wake word.
- Fish Audio integration with existing key.
- OAuth integrations for Gmail, Spotify, WhatsApp, GitHub.
- A compiled Windows executable. Do not claim this is ready to install.

## Dependencies

```powershell
py -3.12 -m pip install -r aris_masten/requirements.txt
ollama pull qwen2.5:3b
```

Download the Brazilian Portuguese Vosk model from the official Vosk website
and pass its directory to `voice.listen_once`.

## Architecture

The original repo uses Claude Code for agent orchestration. The local Ollama
adapter is intentionally independent and does not pretend to provide Claude
Code's MCP/tool access. Integrations must be explicitly implemented, with
authentication and confirmation before writes, sends, deletes, or publishing.
