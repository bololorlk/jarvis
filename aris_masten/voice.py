"""Windows audio input and voices for ARIS / MASTEN.

Speech recognition: offline Vosk PT-BR, native microphone rate converted to
16 kHz using NumPy interpolation. No browser speech APIs.
Speech synthesis: Edge TTS (online). Fish Audio remains an optional future
adapter, not silently simulated.
"""
from __future__ import annotations
import asyncio
import json
import os
import tempfile
from pathlib import Path

_MODEL_CACHE = {}

VOICES = {
    "ARIS": {"voice": "pt-BR-AntonioNeural", "rate": "+0%", "pitch": "-12Hz"},
    "MASTEN": {"voice": "pt-BR-FabioNeural", "rate": "+8%", "pitch": "+12Hz"},
}

def resolve_vosk_model(model_path: str) -> Path:
    """Find bundled Vosk data or install the official model in persistent user storage."""
    import shutil
    import urllib.request
    import zipfile

    base = Path(model_path)
    local = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "ARIS_MASTEN" / "vosk-model"
    candidates = [base, base / "vosk-model-small-pt-0.3", local,
                  local / "vosk-model-small-pt-0.3"]
    for candidate in candidates:
        if (candidate / "am").is_dir() and (candidate / "conf").is_dir():
            return candidate
    for root in (base,):
        if root.is_dir():
            for child in root.iterdir():
                if child.is_dir() and (child / "am").is_dir() and (child / "conf").is_dir():
                    return child

    local.parent.mkdir(parents=True, exist_ok=True)
    archive = local.parent / "vosk-pt-download.zip"
    url = "https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip"
    try:
        urllib.request.urlretrieve(url, archive)
        with zipfile.ZipFile(archive) as z:
            # Prevent archive path traversal.
            destination = local.parent.resolve()
            for item in z.infolist():
                target = (destination / item.filename).resolve()
                if not target.is_relative_to(destination):
                    raise RuntimeError("Arquivo do modelo Vosk inválido.")
            z.extractall(destination)
        extracted = local.parent / "vosk-model-small-pt-0.3"
        if (extracted / "am").is_dir() and (extracted / "conf").is_dir():
            if local.exists():
                shutil.rmtree(local)
            extracted.rename(local)
            return local
    except Exception as exc:
        raise RuntimeError(
            "Modelo de voz Vosk não encontrado no executável e download automático falhou. "
            "Verifique sua conexão com a internet. Detalhes: " + str(exc)) from exc
    finally:
        archive.unlink(missing_ok=True)
    raise RuntimeError("Modelo Vosk baixado, mas os arquivos de reconhecimento estão incompletos.")


def listen_once(model_path: str, seconds: int = 8, device=None):
    """Record one bounded utterance and return (recognized_text, diagnostic)."""
    import numpy as np
    import sounddevice as sd
    from vosk import Model, KaldiRecognizer, SetLogLevel

    path = resolve_vosk_model(model_path)
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
    # Linear interpolation avoids scipy's dynamic imports in packaged EXEs.
    # Use sample positions in the input rate for deterministic 16 kHz PCM.
    output_count = max(1, int(round(len(samples) * 16000 / rate)))
    positions = np.arange(output_count, dtype=np.float64) * (rate / 16000.0)
    converted = np.interp(positions, np.arange(len(samples)), samples)
    pcm = np.clip(converted, -32768, 32767).astype(np.int16).tobytes()
    model = _MODEL_CACHE.get(str(path))
    if model is None:
        model = Model(str(path))
        _MODEL_CACHE[str(path)] = model
    recognizer = KaldiRecognizer(model, 16000)
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
