"""
Dark Matter — ai.com Botname Checker
Animated dark-themed GUI with particle effects.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import requests
import json
import threading
import time
import math
import random
from queue import Queue

# ═══════════════════════════════════════════════════════════════════════
#  THEME
# ═══════════════════════════════════════════════════════════════════════
BG          = "#08080f"
SURFACE     = "#111128"
CARD        = "#16163a"
BORDER      = "#252560"
ACCENT      = "#7c3aed"
ACCENT_HVR  = "#9333ea"
ACCENT_LT   = "#a78bfa"
ACCENT_DIM  = "#4c1d95"
GREEN       = "#10b981"
RED         = "#ef4444"
AMBER       = "#f59e0b"
TEXT        = "#e2e8f0"
TEXT_DIM    = "#94a3b8"
TEXT_MUTED  = "#475569"
PARTICLE_COLORS = ["#7c3aed", "#6d28d9", "#8b5cf6", "#4c1d95", "#312e81"]


# ═══════════════════════════════════════════════════════════════════════
#  PARTICLE SYSTEM
# ═══════════════════════════════════════════════════════════════════════
class Particle:
    __slots__ = ("x", "y", "r", "vx", "vy", "base_a", "phase", "freq",
                 "color", "w", "h", "alpha")

    def __init__(self, w, h):
        self.x = random.uniform(0, w)
        self.y = random.uniform(0, h)
        self.r = random.uniform(1.0, 2.8)
        self.vx = random.uniform(-0.35, 0.35)
        self.vy = random.uniform(-0.35, 0.35)
        self.base_a = random.uniform(0.35, 1.0)
        self.phase = random.uniform(0, math.tau)
        self.freq = random.uniform(0.012, 0.035)
        self.color = random.choice(PARTICLE_COLORS)
        self.w, self.h = w, h
        self.alpha = self.base_a

    def step(self, t):
        self.x = (self.x + self.vx) % self.w
        self.y = (self.y + self.vy) % self.h
        self.alpha = self.base_a * (0.45 + 0.55 * math.sin(t * self.freq + self.phase))


class ParticleCanvas(tk.Canvas):
    """Animated dark-matter particle header with connecting lines."""

    def __init__(self, master, w=720, h=110, n=50, **kw):
        super().__init__(master, width=w, height=h, bg=BG, highlightthickness=0, **kw)
        self._cw, self._ch, self._tick = w, h, 0
        self._particles = [Particle(w, h) for _ in range(n)]

        # Pre-create canvas items for performance
        self._dots = [self.create_oval(0, 0, 0, 0, fill=p.color, outline="")
                      for p in self._particles]
        self._max_lines = 90
        self._lines = [self.create_line(0, 0, 0, 0, fill="", width=1)
                       for _ in range(self._max_lines)]

        # Title
        self.create_text(w // 2, h // 2 - 14, text="DARK MATTER",
                         font=("Segoe UI", 26, "bold"), fill=TEXT)
        self.create_text(w // 2, h // 2 + 16, text="ai.com Botname Checker",
                         font=("Segoe UI", 11), fill=TEXT_DIM)
        self.create_text(w - 8, h - 6, text="credits to @crysiox",
                         font=("Segoe UI", 8), fill=TEXT_MUTED, anchor="se")

        self._animate()

    @staticmethod
    def _blend(hex_c, alpha):
        a = max(0.0, min(1.0, alpha))
        r1, g1, b1 = int(hex_c[1:3], 16), int(hex_c[3:5], 16), int(hex_c[5:7], 16)
        r0, g0, b0 = 8, 8, 15  # BG rgb
        return f"#{int(r1*a+r0*(1-a)):02x}{int(g1*a+g0*(1-a)):02x}{int(b1*a+b0*(1-a)):02x}"

    def _animate(self):
        self._tick += 1
        ps = self._particles
        ci = 0  # connection index

        for i, p in enumerate(ps):
            p.step(self._tick)
            r = p.r * (0.75 + 0.5 * p.alpha)
            self.coords(self._dots[i], p.x - r, p.y - r, p.x + r, p.y + r)
            self.itemconfigure(self._dots[i], fill=self._blend(p.color, p.alpha))

            # Lines to nearby particles
            for j in range(i + 1, len(ps)):
                if ci >= self._max_lines:
                    break
                q = ps[j]
                dx, dy = p.x - q.x, p.y - q.y
                d = math.sqrt(dx * dx + dy * dy)
                if d < 105:
                    la = (1 - d / 105) * 0.28 * min(p.alpha, q.alpha)
                    self.coords(self._lines[ci], p.x, p.y, q.x, q.y)
                    self.itemconfigure(self._lines[ci],
                                       fill=self._blend(ACCENT_LT, la))
                    ci += 1

        for k in range(ci, self._max_lines):
            self.coords(self._lines[k], -1, -1, -1, -1)

        self.after(33, self._animate)


# ═══════════════════════════════════════════════════════════════════════
#  MAIN APP
# ═══════════════════════════════════════════════════════════════════════
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Dark Matter — ai.com Checker")
        self.geometry("720x870")
        self.configure(fg_color=BG)
        self.resizable(False, False)

        # State
        self._running = False
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._checked = 0
        self._avail = 0
        self._taken = 0
        self._errs = 0
        self._total = 0
        self._t0 = 0.0
        self._show_tok = False

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI construction ──────────────────────────────────────────────
    def _build(self):
        ParticleCanvas(self, w=720, h=110, n=50).pack(fill="x")

        main = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        main.pack(fill="both", expand=True, padx=24, pady=(12, 24))

        # ── Token ────────────────────────────────────────────────────
        tf = self._card(main)
        self._label(tf, "TOKEN")
        row = ctk.CTkFrame(tf, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 12))

        self._tok = ctk.CTkEntry(
            row, placeholder_text="Paste your ai.com token...",
            fg_color=CARD, border_color=BORDER, border_width=1,
            text_color=TEXT, placeholder_text_color=TEXT_MUTED,
            font=("Consolas", 13), height=38, show="\u2022")
        self._tok.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            row, text="\U0001f441", width=38, height=38, fg_color=CARD,
            hover_color=ACCENT_DIM, border_width=1, border_color=BORDER,
            font=("Segoe UI", 14), command=self._toggle_tok
        ).pack(side="right")

        # ── Botnames ─────────────────────────────────────────────────
        nf = self._card(main)
        hdr = ctk.CTkFrame(nf, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(12, 4))
        ctk.CTkLabel(hdr, text="BOTNAMES", font=("Segoe UI", 11, "bold"),
                     text_color=TEXT_DIM).pack(side="left")
        ctk.CTkButton(hdr, text="Load File", width=90, height=28,
                      fg_color=ACCENT_DIM, hover_color=ACCENT,
                      text_color=TEXT, font=("Segoe UI", 11),
                      corner_radius=6, command=self._load_file).pack(side="right")

        self._names = ctk.CTkTextbox(
            nf, height=120, fg_color=CARD, border_color=BORDER,
            border_width=1, text_color=TEXT, font=("Consolas", 12),
            corner_radius=8)
        self._names.pack(fill="x", padx=16, pady=(4, 12))

        # ── Controls ─────────────────────────────────────────────────
        ctrl = ctk.CTkFrame(main, fg_color="transparent")
        ctrl.pack(fill="x", pady=(0, 10))

        tf2 = ctk.CTkFrame(ctrl, fg_color=SURFACE, corner_radius=10,
                            border_width=1, border_color=BORDER)
        tf2.pack(side="left")
        ctk.CTkLabel(tf2, text="Threads", font=("Segoe UI", 11),
                     text_color=TEXT_DIM).pack(side="left", padx=(12, 6), pady=8)
        self._thr_var = ctk.StringVar(value="5")
        ctk.CTkEntry(tf2, textvariable=self._thr_var, width=48, height=30,
                     fg_color=CARD, border_color=BORDER, border_width=1,
                     text_color=TEXT, font=("Consolas", 13),
                     justify="center").pack(side="left", padx=(0, 12), pady=8)

        self._stop_btn = ctk.CTkButton(
            ctrl, text="\u23f9  STOP", width=120, height=42,
            fg_color="#7f1d1d", hover_color=RED, text_color=TEXT,
            font=("Segoe UI", 13, "bold"), corner_radius=10,
            command=self._do_stop, state="disabled")
        self._stop_btn.pack(side="right", padx=(8, 0))

        self._start_btn = ctk.CTkButton(
            ctrl, text="\u25b6  START", width=120, height=42,
            fg_color=ACCENT, hover_color=ACCENT_HVR, text_color="white",
            font=("Segoe UI", 13, "bold"), corner_radius=10,
            command=self._do_start)
        self._start_btn.pack(side="right")

        # ── Progress ─────────────────────────────────────────────────
        pf = self._card(main, pad_bot=12)
        pi = ctk.CTkFrame(pf, fg_color="transparent")
        pi.pack(fill="x", padx=16, pady=12)

        self._prog_lbl = ctk.CTkLabel(pi, text="Ready",
                                       font=("Segoe UI", 12), text_color=TEXT_DIM)
        self._prog_lbl.pack(anchor="w")

        self._pbar = ctk.CTkProgressBar(
            pi, height=14, corner_radius=7, fg_color=CARD,
            progress_color=ACCENT, border_width=0)
        self._pbar.pack(fill="x", pady=(6, 10))
        self._pbar.set(0)

        stats = ctk.CTkFrame(pi, fg_color="transparent")
        stats.pack(fill="x")
        self._s_avail = self._stat(stats, "Available", GREEN)
        self._s_taken = self._stat(stats, "Taken", RED)
        self._s_errs  = self._stat(stats, "Errors", AMBER)
        self._s_rate  = self._stat(stats, "Rate", TEXT_DIM, "—")

        # ── Results log ──────────────────────────────────────────────
        rf = self._card(main, expand=True)
        self._label(rf, "RESULTS")

        self._log = ctk.CTkTextbox(
            rf, fg_color=CARD, border_color=BORDER, border_width=1,
            text_color=TEXT, font=("Consolas", 12), corner_radius=8)
        self._log.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self._log.configure(state="disabled")

        # Color tags
        for tag, col in [("avail", GREEN), ("taken", RED),
                         ("err", AMBER), ("rl", AMBER), ("dim", TEXT_DIM)]:
            self._log._textbox.tag_configure(tag, foreground=col)

    # ── Helpers ──────────────────────────────────────────────────────
    def _card(self, parent, pad_bot=12, expand=False):
        f = ctk.CTkFrame(parent, fg_color=SURFACE, corner_radius=12,
                         border_width=1, border_color=BORDER)
        f.pack(fill="both" if expand else "x", expand=expand, pady=(0, pad_bot))
        return f

    def _label(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=("Segoe UI", 11, "bold"),
                     text_color=TEXT_DIM).pack(anchor="w", padx=16, pady=(12, 4))

    def _stat(self, parent, label, color, init="0"):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(side="left", expand=True)
        v = ctk.CTkLabel(f, text=init, font=("Segoe UI", 18, "bold"),
                         text_color=color)
        v.pack()
        ctk.CTkLabel(f, text=label, font=("Segoe UI", 10),
                     text_color=TEXT_MUTED).pack()
        return v

    def _toggle_tok(self):
        self._show_tok = not self._show_tok
        self._tok.configure(show="" if self._show_tok else "\u2022")

    def _load_file(self):
        p = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All", "*.*")])
        if p:
            with open(p, "r", encoding="utf-8") as f:
                self._names.delete("1.0", "end")
                self._names.insert("1.0", f.read())

    def _append_log(self, text, tag):
        self._log.configure(state="normal")
        self._log._textbox.insert("end", text + "\n", tag)
        self._log._textbox.see("end")
        self._log.configure(state="disabled")

    def _refresh_stats(self):
        self._s_avail.configure(text=str(self._avail))
        self._s_taken.configure(text=str(self._taken))
        self._s_errs.configure(text=str(self._errs))
        if self._total > 0:
            pct = self._checked / self._total
            self._pbar.set(pct)
            self._prog_lbl.configure(
                text=f"Checking...  {self._checked}/{self._total}  ({pct:.0%})")
        if self._checked > 0:
            rate = self._checked / max(time.time() - self._t0, 0.01)
            self._s_rate.configure(text=f"{rate:.1f}/s")

    def _flash(self, msg):
        self._prog_lbl.configure(text=msg, text_color=RED)
        self.after(3000,
                   lambda: self._prog_lbl.configure(text="Ready", text_color=TEXT_DIM))

    # ── Pulse animation for progress bar ─────────────────────────────
    def _pulse(self):
        if not self._running:
            self._pbar.configure(progress_color=ACCENT)
            return
        t = time.time()
        f = 0.5 + 0.5 * math.sin(t * 3.5)
        r1, g1, b1 = 0x7c, 0x3a, 0xed
        r2, g2, b2 = 0xa7, 0x8b, 0xfa
        r = int(r1 + (r2 - r1) * f)
        g = int(g1 + (g2 - g1) * f)
        b = int(b1 + (b2 - b1) * f)
        self._pbar.configure(progress_color=f"#{r:02x}{g:02x}{b:02x}")
        self.after(45, self._pulse)

    # ── Core logic ───────────────────────────────────────────────────
    def _do_start(self):
        token = self._tok.get().strip()
        if not token:
            self._flash("Enter your token first")
            return

        raw = self._names.get("1.0", "end").strip()
        names = [n.strip() for n in raw.splitlines() if len(n.strip()) >= 4]
        if not names:
            self._flash("Add botnames (min 4 chars each)")
            return

        try:
            n_thr = max(1, min(20, int(self._thr_var.get())))
        except ValueError:
            n_thr = 5

        # Reset
        self._running = True
        self._stop.clear()
        self._checked = self._avail = self._taken = self._errs = 0
        self._total = len(names)
        self._t0 = time.time()
        self._pbar.set(0)
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._prog_lbl.configure(text=f"Checking...  0/{self._total}  (0%)",
                                  text_color=TEXT_DIM)
        self._s_rate.configure(text="—")
        self._pulse()

        q = Queue()
        for name in names:
            q.put(name)

        def worker():
            while not q.empty() and not self._stop.is_set():
                name = q.get()
                resp, tag = "", "err"

                while not self._stop.is_set():
                    try:
                        r = requests.post(
                            "https://api.ai.com/user/botname/check",
                            data=json.dumps({"botname": name}),
                            headers={
                                "Content-Type": "application/json",
                                "Cookie": f"token={token};"
                            },
                            timeout=15
                        )
                        resp = r.text.strip()

                        if "exceeded the site's rate limits" in resp.lower():
                            self.after(0, lambda n=name: self._append_log(
                                f" \u23f3 {n}: rate-limited, retrying...", "rl"))
                            time.sleep(10)
                            continue

                        try:
                            data = json.loads(resp)
                            if data.get("available", False):
                                tag = "avail"
                                with self._lock:
                                    self._avail += 1
                            else:
                                tag = "taken"
                                with self._lock:
                                    self._taken += 1
                        except (json.JSONDecodeError, AttributeError):
                            if "available" in resp.lower():
                                tag = "avail"
                                with self._lock:
                                    self._avail += 1
                            elif "taken" in resp.lower() or "unavailable" in resp.lower():
                                tag = "taken"
                                with self._lock:
                                    self._taken += 1
                            else:
                                with self._lock:
                                    self._errs += 1
                        break
                    except Exception as exc:
                        resp = str(exc)[:80]
                        with self._lock:
                            self._errs += 1
                        break

                with self._lock:
                    self._checked += 1

                icon = {
                    "avail": "\u2713", "taken": "\u2717", "err": "\u26a0"
                }.get(tag, "\u00b7")

                self.after(0, lambda n=name, rt=resp, t=tag, ic=icon:
                           self._append_log(f" {ic} {n}: {rt}", t))
                self.after(0, self._refresh_stats)

                with self._lock:
                    with open("checked.txt", "a", encoding="utf-8") as f:
                        f.write(f"{name}: {resp}\n")

                q.task_done()

        def run():
            threads = [threading.Thread(target=worker, daemon=True)
                       for _ in range(n_thr)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            self.after(0, self._finish)

        threading.Thread(target=run, daemon=True).start()

    def _do_stop(self):
        self._stop.set()
        self._prog_lbl.configure(text=f"Stopping...  {self._checked}/{self._total}")

    def _finish(self):
        self._running = False
        self._start_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        elapsed = time.time() - self._t0
        self._pbar.set(1.0 if self._checked >= self._total else
                       self._checked / max(self._total, 1))
        self._prog_lbl.configure(
            text=f"Done \u2014 {self._checked}/{self._total} checked in {elapsed:.1f}s",
            text_color=GREEN)
        self._append_log(f"\n Finished in {elapsed:.1f}s  "
                         f"({self._avail} available, {self._taken} taken, "
                         f"{self._errs} errors)", "dim")

    def _on_close(self):
        self._stop.set()
        self.after(100, self.destroy)


# ═══════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = App()
    app.mainloop()
