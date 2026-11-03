"""ARIS / MASTEN: local Ollama backend and safe, explicit desktop tools.

The original Jarvis server.py remains intact. This is a Windows-compatible
alternative brain that can be wired to the existing voice/UI pipeline.
No cloud model or API key required.
"""
from __future__ import annotations
import datetime
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "ARIS_MASTEN"
ROOT.mkdir(parents=True, exist_ok=True)
HISTORY = ROOT / "history.json"
MODEL = os.environ.get("ARIS_MODEL", "qwen2.5:3b")
BASE = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
SYSTEM = {
    "ARIS": "Você é ARIS, assistente técnico profissional. Responda em português brasileiro, objetivamente, em até três frases. Nunca exponha raciocínio interno. Não alegue ter executado ações sem ferramentas.",
    "MASTEN": "Você é MASTEN, assistente pessoal brasileiro, jovem e amigável. Use gírias naturais com moderação, seja sincero e direto. Responda em português brasileiro, em até três frases. Não exponha raciocínio interno. Não alegue ações não executadas.",
}

def load_history():
    try:
        data = json.loads(HISTORY.read_text(encoding="utf-8"))
        return {p: list(data.get(p, []))[-12:] for p in SYSTEM}
    except (OSError, ValueError, TypeError):
        return {p: [] for p in SYSTEM}

def save_history(history):
    temp = HISTORY.with_suffix(".tmp")
    temp.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(HISTORY)

def ask(profile: str, prompt: str) -> str:
    profile = profile.upper()
    if profile not in SYSTEM:
        raise ValueError("Perfil desconhecido")
    history = load_history()
    messages = [{"role": "system", "content": SYSTEM[profile]}]
    messages += history[profile][-10:]
    messages.append({"role": "user", "content": prompt})
    body = json.dumps({
        "model": MODEL, "stream": False, "keep_alive": "10m",
        "options": {"num_predict": 180, "num_ctx": 2048},
        "messages": messages
    }, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        BASE + "/api/chat", data=body,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read(300).decode("utf-8", "replace")
        raise RuntimeError(f"Ollama HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError("Ollama offline. Abra o Ollama e tente novamente.") from exc
    answer = result.get("message", {}).get("content", "")
    answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.S | re.I).strip()
    if not answer:
        raise RuntimeError("O modelo retornou resposta vazia.")
    history[profile] = (history[profile] + [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": answer}
    ])[-12:]
    save_history(history)
    return answer

def read_only_tool(prompt: str) -> str | None:
    """Only deterministic local reads. No shell injection or file mutation."""
    text = prompt.lower().strip()
    now = datetime.datetime.now()
    if re.search(r"\b(que horas|hora atual|horário agora)\b", text):
        return f"Agora são {now:%H:%M}."
    if re.search(r"\b(que dia|data de hoje|dia de hoje)\b", text):
        return f"Hoje é {now:%d/%m/%Y}."
    return None

def plan_action(prompt: str) -> dict | None:
    """Actions require an explicit follow-up confirmation in the caller."""
    p = prompt.lower()
    programs = {
        "calculadora": ["calc.exe"],
        "bloco de notas": ["notepad.exe"],
        "explorador de arquivos": ["explorer.exe"],
    }
    for label, argv in programs.items():
        if "abrir " + label in p or "abre " + label in p:
            return {"label": f"abrir {label}", "argv": argv}
    return None

def execute_confirmed(action: dict) -> str:
    allowed = {("calc.exe",), ("notepad.exe",), ("explorer.exe",)}
    argv = tuple(action.get("argv", []))
    if argv not in allowed:
        raise ValueError("Ação não autorizada")
    if os.name != "nt":
        raise RuntimeError("Este comando só funciona no Windows")
    subprocess.Popen(list(argv), shell=False)
    return "Pronto, aplicativo aberto."
