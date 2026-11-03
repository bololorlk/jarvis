"""ARIS / MASTEN desktop app for Windows. Run: python -m aris_masten.desktop"""
import json
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from . import engine, voice

ROOT = Path(__file__).resolve().parents[1]
VOSK = Path(os.environ.get("ARIS_VOSK_MODEL", str(ROOT / "vosk-model")))
BG, PANEL, BLUE, PURPLE, WHITE = "#050914", "#0d1729", "#27baff", "#aa82ff", "#eaf6ff"


class Desktop:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ARIS / MASTEN | Neural Desktop")
        self.root.geometry("1000x680")
        self.root.minsize(780, 540)
        self.root.configure(bg=BG)
        self.profile = "ARIS"
        self.events = queue.Queue()
        self.busy = False
        self.pending = None
        self.history = []
        self.play_process = None
        self._build()
        self.root.after(80, self.poll)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _build(self):
        self.top = tk.Frame(self.root, bg=BG)
        self.top.pack(fill="x", padx=24, pady=(18, 8))
        tk.Label(self.top, text="A / M     N E U R A L   D E S K T O P",
                 bg=BG, fg=WHITE, font=("Segoe UI", 17, "bold")).pack(side="left")
        self.status = tk.Label(self.top, text="● PRONTO", bg=BG, fg=BLUE,
                               font=("Consolas", 11, "bold"))
        self.status.pack(side="right")
        self.canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0, height=285)
        self.canvas.pack(fill="both", expand=True, padx=24)
        self.canvas.bind("<Configure>", lambda e: self.draw())
        self.body = tk.Frame(self.root, bg=BG)
        self.body.pack(fill="both", padx=24, pady=8)
        self.output = tk.Text(self.body, bg=PANEL, fg=WHITE, insertbackground=WHITE,
                              font=("Segoe UI", 12), height=7, wrap="word",
                              relief="flat", padx=16, pady=12, state="disabled")
        self.output.pack(fill="both", expand=True)
        self.controls = tk.Frame(self.root, bg=BG)
        self.controls.pack(fill="x", padx=24, pady=(8, 22))
        self.listen_btn = tk.Button(self.controls, text="🎙 FALAR (8s)", command=self.listen,
                                    bg="#1b3754", fg=WHITE, relief="flat",
                                    font=("Segoe UI", 11, "bold"), padx=15, pady=12)
        self.listen_btn.pack(side="left", padx=(0, 8))
        self.input = tk.Entry(self.controls, bg=PANEL, fg=WHITE, insertbackground=WHITE,
                              relief="flat", font=("Segoe UI", 12))
        self.input.pack(side="left", fill="x", expand=True, ipady=13)
        self.input.bind("<Return>", lambda e: self.send())
        tk.Button(self.controls, text="ENVIAR", command=self.send,
                  bg=BLUE, fg="#00101c", relief="flat",
                  font=("Segoe UI", 11, "bold"), padx=16, pady=12).pack(side="left", padx=(8, 0))
        tk.Button(self.controls, text="PARAR VOZ", command=self.stop_audio,
                  bg="#26364c", fg=WHITE, relief="flat",
                  font=("Segoe UI", 10), padx=9, pady=12).pack(side="left", padx=(8, 0))
        self.set_status("PRONTO")
        self.draw()
        self.append("SISTEMA", "Pronto. Digite uma mensagem ou clique FALAR. Diga 'Aris' ou 'Masten' para trocar de perfil.")

    def draw(self):
        c = self.canvas
        c.delete("all")
        w, h = max(c.winfo_width(), 700), max(c.winfo_height(), 260)
        x, y = w / 2, h / 2
        accent = BLUE if self.profile == "ARIS" else PURPLE
        for radius in (115, 125, 136):
            c.create_oval(x-radius, y-radius, x+radius, y+radius,
                          outline="#173550", width=1)
        for i in range(100):
            angle = i * 2.399963
            r = (i / 100) ** 0.5 * 106
            import math
            px, py = x + math.cos(angle)*r, y + math.sin(angle)*r
            c.create_oval(px-1.4, py-1.4, px+1.4, py+1.4, fill=accent, outline="")
        c.create_oval(x-72, y-72, x+72, y+72, fill="#091c34", outline="#2a628b", width=2)
        c.create_text(x, y-7, text=self.profile, fill=WHITE,
                      font=("Segoe UI", 30, "bold"))
        c.create_text(x, y+31, text="LOCAL INTELLIGENCE", fill=accent,
                      font=("Consolas", 9))
        c.create_text(12, 20, text="01 / VOZ E COMANDOS", anchor="w",
                      fill="#7295b4", font=("Consolas", 10))
        c.create_text(w-12, 20, text="02 / PRIVACIDADE LOCAL", anchor="e",
                      fill="#7295b4", font=("Consolas", 10))

    def set_status(self, text):
        self.status.configure(text="● " + text, fg=BLUE if self.profile == "ARIS" else PURPLE)

    def append(self, who, msg):
        self.output.configure(state="normal")
        self.output.insert("end", who + ": " + msg + "\n\n")
        self.output.see("end")
        self.output.configure(state="disabled")

    def send(self):
        text = self.input.get().strip()
        self.input.delete(0, "end")
        self.submit(text)

    def listen(self):
        if self.busy:
            self.append("SISTEMA", "Aguarde a resposta atual.")
            return
        self.busy = True
        self.set_status("OUVINDO 8 SEGUNDOS")
        self.listen_btn.configure(state="disabled")
        def work():
            try:
                text, diagnostics = voice.listen_once(str(VOSK), seconds=8)
                self.events.put(("heard", text, diagnostics))
            except Exception as exc:
                self.events.put(("error", "Microfone: " + str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def submit(self, text):
        if not text:
            self.set_status("NÃO RECONHECI A FALA")
            return
        if self.busy:
            self.append("SISTEMA", "Ainda processando. Aguarde.")
            return
        normalized = text.lower().strip()
        if re.search(r"\b(masten)\b", normalized):
            self.profile = "MASTEN"
            text = re.sub(r"\bmasten\b", "", text, flags=re.I).strip(" ,.!?")
            self.draw()
        elif re.search(r"\b(aris|áris)\b", normalized):
            self.profile = "ARIS"
            text = re.sub(r"\b(aris|áris)\b", "", text, flags=re.I).strip(" ,.!?")
            self.draw()
        if not text:
            text = "Me cumprimente brevemente."
        self.append("VOCÊ", text)
        self.busy = True
        self.set_status("PROCESSANDO")
        profile = self.profile
        def work():
            try:
                answer = engine.read_only_tool(text)
                if answer is None:
                    action = engine.plan_action(text)
                    if action:
                        self.events.put(("confirm", action))
                        return
                    answer = engine.ask(profile, text)
                self.events.put(("answer", profile, answer))
            except Exception as exc:
                self.events.put(("error", str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def speak(self, profile, text):
        def work():
            try:
                mp3 = voice.speak(profile, text)
                # Windows Media Player via native MCI API, no external audio player.
                if os.name != "nt":
                    return
                import ctypes
                mci = ctypes.windll.winmm.mciSendStringW
                alias = "arisvoice"
                mci(f"close {alias}", None, 0, None)
                code = mci(f'open "{mp3}" type mpegvideo alias {alias}', None, 0, None)
                if code:
                    raise RuntimeError(f"Windows MCI open error {code}")
                mci(f"play {alias}", None, 0, None)
            except Exception as exc:
                self.events.put(("voice_error", str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def stop_audio(self):
        if os.name == "nt":
            import ctypes
            ctypes.windll.winmm.mciSendStringW("stop arisvoice", None, 0, None)
            ctypes.windll.winmm.mciSendStringW("close arisvoice", None, 0, None)

    def poll(self):
        try:
            while True:
                kind, *args = self.events.get_nowait()
                if kind == "heard":
                    self.busy = False
                    self.listen_btn.configure(state="normal")
                    text, diagnostics = args
                    self.append("MIC", f"Reconhecido: {text or '(nenhuma palavra)'} | "
                                f"Entrada: {diagnostics['device']} | Pico: {diagnostics['peak']}")
                    self.set_status("PRONTO")
                    if text:
                        self.submit(text)
                elif kind == "answer":
                    profile, answer = args
                    self.busy = False
                    self.set_status("PRONTO")
                    self.append(profile, answer)
                    self.speak(profile, answer)
                elif kind == "confirm":
                    action = args[0]
                    self.busy = False
                    self.set_status("AGUARDANDO CONFIRMAÇÃO")
                    self.append("SISTEMA", "Confirmar ação: " + action["label"] + "?")
                    if messagebox.askyesno("Confirmar ação", "Deseja " + action["label"] + "?"):
                        try:
                            self.append("SISTEMA", engine.execute_confirmed(action))
                        except Exception as exc:
                            self.append("ERRO", str(exc))
                    else:
                        self.append("SISTEMA", "Ação cancelada.")
                    self.set_status("PRONTO")
                elif kind == "voice_error":
                    self.append("VOZ", "Falha na síntese/reprodução: " + args[0])
                elif kind == "error":
                    self.busy = False
                    self.listen_btn.configure(state="normal")
                    self.set_status("ERRO")
                    self.append("ERRO", args[0])
        except queue.Empty:
            pass
        self.root.after(80, self.poll)

    def close(self):
        self.stop_audio()
        self.root.destroy()

def main():
    Desktop().root.mainloop()

if __name__ == "__main__":
    main()
