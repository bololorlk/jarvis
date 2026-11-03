"""Windows audio input and voices for ARIS / MASTEN.

Speech recognition: offline Vosk PT-BR, native microphone rate converted to
16 kHz using scipy.signal.resample_poly. No browser speech APIs.
Speech synthesis: Edge TTS (online). Fish Audio remains an optional future
adapter, not silently simulated.
"""
from __future__ import annotations
import asyncio
import json
import math
import os
import tempfile
from pathlib import Path

VOICES = {
    "ARIS": {"voice": "pt-BR-AntonioNeural", "rate": "+0%", "pitch": "-12Hz"},
    "MASTEN": {"voice": "pt-BR-FabioNeural", "rate": "+8%", "pitch": "+12Hz"},
}

def listen_once(model_path: str, seconds: int = 8, device=None):
    """Record one bounded utterance and return (recognized_text, diagnostic)."""
    import numpy as np
    import sounddevice as sd
    from scipy.signal import resample_poly
    from vosk import Model, KaldiRecognizer, SetLogLevel

    path = Path(model_path)
    if not (path / "am").exists():
        raise FileNotFoundError(f"Modelo Vosk ausente: {path}")
    SetLogLevel(-1)
    info = sd.query_devices(device, kind="input")
    rate = int(info["default_samplerate"])
    if rate < 8000:
        raise RuntimeError(f"Taxa de entrada inválida: {rate}")
    # End after silence, rather than waiting the full timeout for every utterance.
    import time
    chunks = []
    peak = 0
    speech_started = False
    last_loud = None
    started = time.monotonic()
    block = max(512, int(rate * 0.08))
    with sd.InputStream(samplerate=rate, channels=1, dtype="int16",
                        device=device, blocksize=block) as stream:
        while time.monotonic() - started < seconds:
            frames, overflowed = stream.read(block)
            chunks.append(frames.copy())
            level = int(np.max(np.abs(frames.astype(np.int32))))
            peak = max(peak, level)
            if level > 550:
                speech_started = True
                last_loud = time.monotonic()
            if speech_started and last_loud is not None:
                if time.monotonic() - last_loud > 0.95:
                    break
    if not chunks:
        raise RuntimeError("Nenhum áudio recebido do microfone.")
    frames = np.concatenate(chunks, axis=0)
    samples = frames[:, 0].astype(np.float32)
    divisor = math.gcd(rate, 16000)
    converted = resample_poly(samples, 16000 // divisor, rate // divisor)
    pcm = np.clip(converted, -32768, 32767).astype(np.int16).tobytes()
    recognizer = KaldiRecognizer(Model(str(path)), 16000)
    recognizer.AcceptWaveform(pcm)
    final = json.loads(recognizer.FinalResult()).get("text", "").strip()
    return final, {"device": info["name"], "sample_rate": rate, "peak": peak, "speech_detected": speech_started}

async def synthesize(profile: str, text: str, destination: str):
    import edge_tts
    voice = VOICES[profile.upper()]
    communicate = edge_tts.Communicate(
        text=text, voice=voice["voice"], rate=voice["rate"], pitch=voice["pitch"])
    await communicate.save(destination)

def speak(profile: str, text: str):
    """Return MP3 path; caller handles playback and cleanup."""
    path = Path(tempfile.gettempdir()) / ("aris_masten_" + profile.lower() + ".mp3")
    asyncio.run(synthesize(profile, text, str(path)))
    return path
