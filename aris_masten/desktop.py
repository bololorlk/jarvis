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

from aris_masten import engine, voice

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", ROOT))
VOSK = Path(os.environ.get("ARIS_VOSK_MODEL", str(BUNDLE_ROOT / "vosk-model")))
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
        self.logs = {"ARIS": [], "MASTEN": []}
        self.play_process = None
        self._build()
        self.root.after(80, self.poll)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _build(self):
        self.root.configure(bg=BG)
        self.header = tk.Frame(self.root, bg=BG)
        self.header.pack(fill="x", padx=30, pady=(20, 8))
        tk.Label(self.header, text="A / M   •   NEURAL SYSTEMS",
                 fg="#91a9bd", bg=BG, font=("Consolas", 12, "bold")).pack(side="left")
        self.status = tk.Label(self.header, text="● ONLINE", fg=BLUE, bg=BG,
                               font=("Consolas", 10, "bold"))
        self.status.pack(side="right")
        tk.Frame(self.root, bg="#25435a", height=1).pack(fill="x", padx=30, pady=8)

        self.tabs = tk.Frame(self.root, bg=BG)
        self.tabs.pack(fill="x", padx=30, pady=(5, 0))
        self.tab_buttons = {}
        for name in ("ARIS", "MASTEN"):
            color = BLUE if name == "ARIS" else PURPLE
            btn = tk.Button(self.tabs, text=("01  " if name == "ARIS" else "02  ") + name,
                            command=lambda p=name: self.switch_profile(p),
                            bg=PANEL, fg=color, relief="flat",
                            font=("Segoe UI", 13, "bold"), padx=26, pady=12,
                            activebackground="#16283b", activeforeground=WHITE,
                            cursor="hand2")
            btn.pack(side="left", padx=(0, 10))
            self.tab_buttons[name] = btn
        self.section = tk.Label(self.tabs, text="", fg="#809ab0", bg=BG,
                                font=("Consolas", 10))
        self.section.pack(side="right")

        self.canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0, height=275)
        self.canvas.pack(fill="both", expand=True, padx=24, pady=(5, 0))
        self.canvas.bind("<Configure>", lambda e: self.draw())

        self.body = tk.Frame(self.root, bg=BG)
        self.body.pack(fill="both", padx=30, pady=(0, 6))
        self.output = tk.Text(self.body, bg="#091524", fg=WHITE, insertbackground=WHITE,
                              font=("Segoe UI", 11), height=7, wrap="word",
                              relief="flat", padx=16, pady=12, state="disabled")
        self.output.pack(fill="both", expand=True)

        self.controls = tk.Frame(self.root, bg=BG)
        self.controls.pack(fill="x", padx=30, pady=(8, 22))
        self.listen_btn = tk.Button(self.controls, text="🎙 FALAR",
                                    command=self.listen, bg="#173650", fg=WHITE,
                                    relief="flat", font=("Segoe UI", 11, "bold"),
                                    padx=15, pady=12)
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
        self.switch_profile("ARIS")
        self.append("SISTEMA", "Pronto. Escolha ARIS ou MASTEN e fale ou digite.")

    def switch_profile(self, profile):
        if self.busy:
            return
        self.profile = profile
        accent = BLUE if profile == "ARIS" else PURPLE
        for name, btn in self.tab_buttons.items():
            selected = name == profile
            btn.configure(bg="#163047" if selected else PANEL,
                          fg=WHITE if selected else "#738da3",
                          highlightthickness=1 if selected else 0,
                          highlightbackground=accent)
        self.section.configure(text="TECH / WORK / PROJECTS" if profile == "ARIS"
                               else "LIFESTYLE / MUSIC / CULTURE")
        self.listen_btn.configure(bg="#173650" if profile == "ARIS" else "#302247")
        self.set_status("PRONTO")
        self.render_log()
        self.draw()

    def render_log(self):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        for who, msg in self.logs[self.profile]:
            self.output.insert("end", who + ": " + msg + "\n\n")
        self.output.configure(state="disabled")
        self.output.see("end")

    def draw(self):
        import math
        c = self.canvas
        c.delete("all")
        w, h = max(c.winfo_width(), 720), max(c.winfo_height(), 245)
        accent = BLUE if self.profile == "ARIS" else PURPLE
        x, y = w * .52, h * .53
        # Restrained HUD: precise outlines, concentric core, side telemetry.
        c.create_line(12, 12, 175, 12, fill="#25485c", width=2)
        c.create_line(12, 12, 12, 62, fill="#25485c", width=2)
        c.create_line(w-175, 12, w-12, 12, fill="#25485c", width=2)
        c.create_line(w-12, 12, w-12, 62, fill="#25485c", width=2)
        c.create_line(12, h-62, 12, h-12, fill="#25485c", width=2)
        c.create_line(12, h-12, 175, h-12, fill="#25485c", width=2)
        c.create_line(w-175, h-12, w-12, h-12, fill="#25485c", width=2)
        c.create_line(w-12, h-62, w-12, h-12, fill="#25485c", width=2)
        for radius in (110, 94, 79, 63, 45):
            c.create_oval(x-radius, y-radius, x+radius, y+radius,
                          outline=accent if radius in (94, 63) else "#24475a",
                          width=2 if radius == 63 else 1)
        for i in range(48):
            angle = i * 2 * math.pi / 48
            r1, r2 = (99, 105) if i % 4 else (99, 111)
            c.create_line(x+math.cos(angle)*r1, y+math.sin(angle)*r1,
                          x+math.cos(angle)*r2, y+math.sin(angle)*r2,
                          fill=accent if i % 4 == 0 else "#315267")
        c.create_oval(x-32, y-32, x+32, y+32, fill="#102c40",
                      outline=accent, width=3)
        c.create_oval(x-14, y-14, x+14, y+14, fill=accent, outline="")
        c.create_text(30, 53, text="VOICE ASSISTANT", anchor="w",
                      fill="#7195ab", font=("Consolas", 10))
        c.create_text(30, 99, text=self.profile, anchor="w",
                      fill=accent, font=("Segoe UI", 32, "bold"))
        subtitle = "YOUR TECHNICAL INTELLIGENCE" if self.profile == "ARIS" else "YOUR EVERYDAY COMPANION"
        c.create_text(32, 126, text=subtitle, anchor="w",
                      fill=WHITE, font=("Consolas", 9))
        c.create_line(30, 145, max(35, x-128), 145, fill=accent)
        c.create_text(w-28, 54, text="SYSTEM STATUS", anchor="e",
                      fill=accent, font=("Consolas", 10))
        c.create_text(w-28, 79, text="CORE     ONLINE", anchor="e",
                      fill="#a2bac9", font=("Consolas", 9))
        c.create_text(w-28, 100, text="VOICE    READY", anchor="e",
                      fill="#a2bac9", font=("Consolas", 9))
        c.create_text(w-28, 121, text="PROFILE  " + self.profile, anchor="e",
                      fill="#a2bac9", font=("Consolas", 9))

    def set_status(self, text):
        self.status.configure(text="● " + text, fg=BLUE if self.profile == "ARIS" else PURPLE)

    def append(self, who, msg):
        self.logs[self.profile].append((who, msg))
        self.logs[self.profile] = self.logs[self.profile][-60:]
        self.render_log()

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
            self.switch_profile("MASTEN")
            text = re.sub(r"\bmasten\b", "", text, flags=re.I).strip(" ,.!?")
            self.draw()
        elif re.search(r"\b(aris|áris)\b", normalized):
            self.switch_profile("ARIS")
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
