"""ARIS / MASTEN desktop app for Windows. Run: python -m aris_masten.desktop"""
import json
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
from pathlib import Path

from aris_masten import engine, voice

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", ROOT))
VOSK = Path(os.environ.get("ARIS_VOSK_MODEL", str(BUNDLE_ROOT / "vosk-model")))
BG, PANEL, BLUE, PURPLE, WHITE = "#050914", "#0d1729", "#27baff", "#aa82ff", "#eaf6ff"


class Desktop:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ARIS / MASTEN | Neural Desktop")
        self.root.geometry("1440x850")
        self.root.minsize(1250, 700)
        self.root.configure(bg=BG)
        self.profile = "ARIS"
        self.events = queue.Queue()
        self.busy = False
        self.pending = None
        self.history = []
        self.logs = {"ARIS": [], "MASTEN": []}
        self.play_process = None
        self.running = True
        self.microphone_paused = threading.Event()
        self.wake_deadline = 0.0
        self.animation_phase = 0
        self._build()
        self.root.after(80, self.poll)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        threading.Thread(target=self.listen_forever, daemon=True).start()
        self.root.after(100, self.animate)

    def _build(self):
        self.root.configure(bg=BG)
        self.header = tk.Frame(self.root, bg=BG)
        self.header.pack(fill="x", padx=24, pady=(15, 8))
        tk.Label(self.header, text="A / M   //   NEURAL COMMAND CENTER",
                 fg=BLUE, bg=BG, font=("Consolas", 16, "bold")).pack(side="left")
        self.status = tk.Label(self.header, text="● ONLINE", fg=BLUE, bg=BG,
                               font=("Consolas", 10, "bold"))
        self.status.pack(side="right")
        tk.Frame(self.root, bg="#25435a", height=1).pack(fill="x", padx=24, pady=5)

        self.tabs = tk.Frame(self.root, bg=BG)
        self.tabs.pack(fill="x", padx=24, pady=(5, 0))
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

        self.hudrow = tk.Frame(self.root, bg=BG)
        self.hudrow.pack(fill="both", expand=True, padx=24, pady=(10, 6))
        self.left_rail = tk.Frame(self.hudrow, bg="#091626", width=225,
                                  highlightbackground="#1d597b", highlightthickness=1)
        self.left_rail.pack(side="left", fill="y", padx=(0, 8))
        self.left_rail.pack_propagate(False)
        tk.Label(self.left_rail, text="◈  MODULES / SYSTEM", bg="#091626", fg=BLUE,
                 font=("Consolas", 10, "bold")).pack(anchor="w", padx=14, pady=(17, 14))
        self.module_buttons = {}
        for module in ("GMAIL", "WHATSAPP", "INSTAGRAM", "SPOTIFY", "AGENDA", "AUTOMAÇÃO"):
            panel = tk.Frame(self.left_rail, bg="#0e2236")
            panel.pack(fill="x", padx=10, pady=4)
            btn = tk.Button(panel, text="▹  " + module, anchor="w", bg="#0e2236", fg="#c4e7fa",
                            activebackground="#173c54", activeforeground=WHITE,
                            bd=0, padx=10, pady=8, font=("Consolas", 10),
                            command=lambda m=module: self.show_module(m), cursor="hand2")
            btn.pack(fill="x")
            self.module_buttons[module] = btn
        tk.Label(self.left_rail, text="CONEXÕES EXTERNAS", bg="#091626", fg="#7993aa",
                 font=("Consolas", 9, "bold")).pack(anchor="w", padx=14, pady=(24, 3))
        tk.Label(self.left_rail, text="● AGUARDANDO VÍNCULO", bg="#091626", fg="#efbd70",
                 font=("Consolas", 9)).pack(anchor="w", padx=14)

        self.right_rail = tk.Frame(self.hudrow, bg="#091626", width=235,
                                   highlightbackground="#1d597b", highlightthickness=1)
        self.right_rail.pack(side="right", fill="y", padx=(8, 0))
        self.right_rail.pack_propagate(False)
        tk.Label(self.right_rail, text="◈  TELEMETRIA", bg="#091626", fg=BLUE,
                 font=("Consolas", 11, "bold")).pack(anchor="w", padx=15, pady=(18, 20))
        for label, value in (("IA LOCAL", "OLLAMA / QWEN 3B"),
                             ("LINGUAGEM", "PORTUGUÊS BR"),
                             ("COMANDOS", "WINDOWS / LOCAL"),
                             ("ARQUITETURA", "DUAL PERSONA")):
            tk.Label(self.right_rail, text=label, fg="#6e95ac", bg="#091626",
                     font=("Consolas", 9)).pack(anchor="w", padx=15, pady=(8, 2))
            tk.Label(self.right_rail, text=value, fg=WHITE, bg="#091626",
                     font=("Consolas", 10, "bold")).pack(anchor="w", padx=15)
            tk.Frame(self.right_rail, bg="#183950", height=1).pack(fill="x", padx=15, pady=8)
        tk.Label(self.right_rail, text="◈  PERMISSÕES", bg="#091626", fg=BLUE,
                 font=("Consolas", 11, "bold")).pack(anchor="w", padx=15, pady=(18, 7))
        tk.Label(self.right_rail, text="✓ APLICATIVOS LOCAIS\n✓ CONTROLE DE VOLUME\n○ CONTAS NÃO VINCULADAS",
                 justify="left", bg="#091626", fg="#a5c0d0",
                 font=("Consolas", 9)).pack(anchor="w", padx=15)

        self.canvas = tk.Canvas(self.hudrow, bg=BG, highlightthickness=0, height=300)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.draw())

        self.body = tk.Frame(self.root, bg=BG)
        self.body.pack(fill="both", padx=24, pady=(0, 6))
        tk.Label(self.body, text="▰  COMMAND / ACTIVITY STREAM", bg=BG, fg=BLUE,
                 font=("Consolas", 10, "bold")).pack(anchor="w", pady=(0, 5))
        self.output = tk.Text(self.body, bg="#091524", fg=WHITE, insertbackground=WHITE,
                              font=("Segoe UI", 11), height=7, wrap="word",
                              relief="flat", padx=16, pady=12, state="disabled")
        self.output.pack(fill="both", expand=True)

        self.controls = tk.Frame(self.root, bg=BG)
        self.controls.pack(fill="x", padx=24, pady=(8, 16))
        tk.Label(self.controls, text="● MICROFONE AUTOMÁTICO", fg=BLUE, bg=BG,
                 font=("Consolas", 9, "bold")).pack(side="left", padx=(0, 12))
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

    def show_module(self, module):
        """The dashboard is explicit about connectors not yet configured."""
        self.append("MÓDULO", f"{module}: integração ainda não vinculada. Nenhuma conta foi acessada.")

    def animate(self):
        if not self.running:
            return
        self.animation_phase = (self.animation_phase + 1) % 360
        self.draw()
        self.root.after(110, self.animate)

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
        self.root.title(f"ARIS / MASTEN | {profile} • Neural Command Center")
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
        x, y = w * .51, h * .52
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
            angle = i * 2 * math.pi / 48 + self.animation_phase * math.pi / 180
            r1, r2 = (99, 105) if i % 4 else (99, 111)
            c.create_line(x+math.cos(angle)*r1, y+math.sin(angle)*r1,
                          x+math.cos(angle)*r2, y+math.sin(angle)*r2,
                          fill=accent if i % 4 == 0 else "#315267")
        # Orbiting markers and counter-rotating scope rings.
        phase = self.animation_phase * math.pi / 180
        for angle_offset, radius, size in ((0, 119, 4), (2.1, 119, 3), (4.3, 77, 3)):
            a = phase + angle_offset
            px, py = x + math.cos(a) * radius, y + math.sin(a) * radius
            c.create_oval(px-size, py-size, px+size, py+size, fill=accent, outline="")
        c.create_arc(x-122, y-122, x+122, y+122, start=self.animation_phase,
                     extent=76, style="arc", outline=accent, width=3)
        c.create_arc(x-135, y-135, x+135, y+135, start=270-self.animation_phase,
                     extent=42, style="arc", outline="#225b86", width=2)
        c.create_oval(x-32, y-32, x+32, y+32, fill="#102c40",
                      outline=accent, width=3)
        c.create_oval(x-14, y-14, x+14, y+14, fill=accent, outline="")
        c.create_text(x, y+158, text="NEURAL CORE  //  ACTIVE", fill=accent,
                      font=("Consolas", 10, "bold"))
        c.create_text(x, y+178, text="LOCAL AI  •  COMMAND ROUTER  •  DUAL PROFILE", fill="#668da4",
                      font=("Consolas", 8))
        c.create_text(30, 53, text="PERSONA / SYSTEM ONLINE", anchor="w",
                      fill="#7195ab", font=("Consolas", 10))
        c.create_text(30, 99, text=self.profile, anchor="w",
                      fill=accent, font=("Segoe UI", 32, "bold"))
        subtitle = "YOUR TECHNICAL INTELLIGENCE" if self.profile == "ARIS" else "YOUR EVERYDAY COMPANION"
        c.create_text(32, 126, text=subtitle, anchor="w",
                      fill=WHITE, font=("Consolas", 9))
        c.create_line(30, 145, max(35, x-128), 145, fill=accent)
        c.create_text(w-28, 54, text="SYSTEM STATUS", anchor="e",
                      fill=accent, font=("Consolas", 10))
        c.create_text(w-28, 79, text="CORE    OLLAMA", anchor="e",
                      fill="#a2bac9", font=("Consolas", 9))
        c.create_text(w-28, 100, text="VOICE    STANDBY", anchor="e",
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

    def listen_forever(self):
        """Record continuously in bounded phrases; only wake names trigger commands."""
        import sounddevice as sd
        try:
            sd.query_devices(kind="input")
        except Exception:
            self.events.put(("mic_error", "Nenhum microfone detectado. Comandos digitados continuam disponíveis."))
            return
        while self.running:
            if self.microphone_paused.is_set() or self.busy:
                time.sleep(.15)
                continue
            try:
                text, diagnostics = voice.listen_once(str(VOSK), seconds=7)
                if text:
                    self.events.put(("heard", text, diagnostics))
            except Exception as exc:
                self.events.put(("mic_error", str(exc)))
                time.sleep(3)

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
                    answer = engine.set_system_volume(text)
                if answer is None:
                    action = engine.plan_action(text)
                    if action:
                        self.events.put(("action_done", profile, engine.execute_confirmed(action)))
                        return
                    answer = engine.ask(profile, text)
                self.events.put(("answer", profile, answer))
            except Exception as exc:
                self.events.put(("error", str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def speak(self, profile, text):
        self.microphone_paused.set()
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
                audio_type = "waveaudio" if mp3.suffix.lower() == ".wav" else "mpegvideo"
                code = mci(f'open "{mp3}" type {audio_type} alias {alias}', None, 0, None)
                if code:
                    raise RuntimeError(f"Windows MCI open error {code}")
                mci(f"play {alias}", None, 0, None)
                # Don't let the mic re-hear the assistant's own spoken reply.
                status = __import__("ctypes").create_unicode_buffer(64)
                for _ in range(600):
                    if not self.running:
                        break
                    mci(f"status {alias} mode", status, len(status), None)
                    if status.value.lower() != "playing":
                        break
                    time.sleep(.1)
            except Exception as exc:
                self.events.put(("voice_error", str(exc)))
            finally:
                time.sleep(.35)
                self.microphone_paused.clear()
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
                    text, diagnostics = args
                    names = re.search(r"\b(aris|áris|masten)\b", text, re.I)
                    if names:
                        self.wake_deadline = time.monotonic() + 10
                        remaining = re.sub(r"\b(aris|áris|masten)\b", "", text, flags=re.I).strip(" ,.!?")
                        if remaining:
                            self.wake_deadline = 0
                            self.submit(text)
                        else:
                            self.switch_profile("MASTEN" if names.group().lower() == "masten" else "ARIS")
                            self.set_status("ESCUTANDO COMANDO")
                    elif time.monotonic() < self.wake_deadline:
                        self.wake_deadline = 0
                        self.submit(text)
                elif kind == "answer":
                    profile, answer = args
                    self.busy = False
                    self.set_status("PRONTO")
                    self.append(profile, answer)
                    self.speak(profile, answer)
                elif kind == "action_done":
                    profile, message = args
                    self.busy = False
                    self.set_status("PRONTO")
                    self.append(profile, message)
                    self.speak(profile, message)
                elif kind == "voice_error":
                    self.append("VOZ", "Falha na síntese/reprodução: " + args[0])
                elif kind == "error":
                    self.busy = False
                    self.set_status("ERRO")
                    self.append("ERRO", args[0])
                elif kind == "mic_error":
                    self.set_status("MICROFONE INDISPONÍVEL")
                    self.append("MIC", args[0] + " (nova tentativa em 3 segundos)")
        except queue.Empty:
            pass
        self.root.after(80, self.poll)

    def close(self):
        self.running = False
        self.stop_audio()
        self.root.destroy()

def main():
    Desktop().root.mainloop()

if __name__ == "__main__":
    main()
