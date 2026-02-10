import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import requests, json, threading, itertools
import time, math, random
from queue import Queue

# colors
BG = "#08080f"
SURFACE = "#111128"
CARD = "#16163a"
BORDER = "#252560"
ACCENT = "#7c3aed"
ACCENT_HVR = "#9333ea"
ACCENT_LT = "#a78bfa"
ACCENT_DIM = "#4c1d95"
GREEN = "#10b981"
RED = "#ef4444"
AMBER = "#f59e0b"
CYAN = "#06b6d4"
TEXT = "#e2e8f0"
TEXT_DIM = "#94a3b8"
TEXT_MUTED = "#475569"
P_COLORS = ["#7c3aed", "#6d28d9", "#8b5cf6", "#4c1d95", "#312e81"]


class Particle:
    def __init__(self, w, h):
        self.x = random.uniform(0, w)
        self.y = random.uniform(0, h)
        self.r = random.uniform(1.0, 2.8)
        self.vx = random.uniform(-0.35, 0.35)
        self.vy = random.uniform(-0.35, 0.35)
        self.base_a = random.uniform(0.35, 1.0)
        self.phase = random.uniform(0, math.tau)
        self.freq = random.uniform(0.012, 0.035)
        self.color = random.choice(P_COLORS)
        self.w, self.h = w, h
        self.alpha = self.base_a

    def step(self, t):
        self.x = (self.x + self.vx) % self.w
        self.y = (self.y + self.vy) % self.h
        self.alpha = self.base_a * (0.45 + 0.55 * math.sin(t * self.freq + self.phase))


def blend(hex_c, alpha):
    a = max(0.0, min(1.0, alpha))
    r1, g1, b1 = int(hex_c[1:3], 16), int(hex_c[3:5], 16), int(hex_c[5:7], 16)
    r0, g0, b0 = 8, 8, 15  # bg rgb
    return f"#{int(r1*a+r0*(1-a)):02x}{int(g1*a+g0*(1-a)):02x}{int(b1*a+b0*(1-a)):02x}"


class ParticleCanvas(tk.Canvas):
    def __init__(self, master, w=720, h=110, n=50, **kw):
        super().__init__(master, width=w, height=h, bg=BG, highlightthickness=0, **kw)
        self._cw, self._ch, self._tick = w, h, 0
        self.particles = [Particle(w, h) for _ in range(n)]

        self.dots = [self.create_oval(0,0,0,0, fill=p.color, outline="") for p in self.particles]
        self.max_lines = 90
        self.lines = [self.create_line(0,0,0,0, fill="", width=1) for _ in range(self.max_lines)]

        self.create_text(w//2, h//2 - 14, text="DARK MATTER", font=("Segoe UI", 26, "bold"), fill=TEXT)
        self.create_text(w//2, h//2 + 16, text="ai.com Botname Checker", font=("Segoe UI", 11), fill=TEXT_DIM)
        self.create_text(w - 8, h - 6, text="credits to @crysiox", font=("Segoe UI", 8), fill=TEXT_MUTED, anchor="se")

        self._animate()

    def _animate(self):
        self._tick += 1
        ci = 0

        for i, p in enumerate(self.particles):
            p.step(self._tick)
            r = p.r * (0.75 + 0.5 * p.alpha)
            self.coords(self.dots[i], p.x-r, p.y-r, p.x+r, p.y+r)
            self.itemconfigure(self.dots[i], fill=blend(p.color, p.alpha))

            for j in range(i+1, len(self.particles)):
                if ci >= self.max_lines: break
                q = self.particles[j]
                dx, dy = p.x - q.x, p.y - q.y
                d = math.sqrt(dx*dx + dy*dy)
                if d < 105:
                    la = (1 - d/105) * 0.28 * min(p.alpha, q.alpha)
                    self.coords(self.lines[ci], p.x, p.y, q.x, q.y)
                    self.itemconfigure(self.lines[ci], fill=blend(ACCENT_LT, la))
                    ci += 1

        for k in range(ci, self.max_lines):
            self.coords(self.lines[k], -1,-1,-1,-1)

        self.after(33, self._animate)


# proxy stuff

def parse_proxies(raw, ptype="http"):
    out = []
    for line in raw.strip().splitlines():
        p = line.strip()
        if not p: continue
        if "://" in p:
            out.append({"http": p, "https": p})
        else:
            url = f"{ptype}://{p}"
            out.append({"http": url, "https": url})
    return out


class ProxyCycler:
    def __init__(self, plist):
        self._all = list(plist)
        self._live = list(plist)
        self._cycle = itertools.cycle(self._live) if self._live else None
        self._lock = threading.Lock()
        self._dead = set()

    @property
    def total(self):
        return len(self._all)

    @property
    def alive(self):
        with self._lock:
            return len(self._live)

    def next(self):
        with self._lock:
            if not self._cycle or not self._live: return None
            return next(self._cycle)

    def kill(self, proxy):
        key = proxy.get("http", "")
        with self._lock:
            if key not in self._dead:
                self._dead.add(key)
                self._live = [p for p in self._live if p.get("http") != key]
                self._cycle = itertools.cycle(self._live) if self._live else None


# main gui

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Dark Matter - ai.com Checker")
        self.geometry("720x960")
        self.configure(fg_color=BG)
        self.resizable(False, False)

        self.running = False
        self.stop_flag = threading.Event()
        self.lock = threading.Lock()
        self.checked = 0
        self.avail = 0
        self.taken = 0
        self.errs = 0
        self.total = 0
        self.t0 = 0.0
        self.show_tok = False

        self.setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        ParticleCanvas(self, w=720, h=110, n=50).pack(fill="x")

        main = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        main.pack(fill="both", expand=True, padx=24, pady=(12, 24))

        # token
        tf = self.make_card(main)
        self.section_lbl(tf, "TOKEN")
        row = ctk.CTkFrame(tf, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 12))

        self.tok_entry = ctk.CTkEntry(row, placeholder_text="Paste your ai.com token...",
            fg_color=CARD, border_color=BORDER, border_width=1, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, font=("Consolas", 13), height=38, show="\u2022")
        self.tok_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(row, text="\U0001f441", width=38, height=38, fg_color=CARD,
            hover_color=ACCENT_DIM, border_width=1, border_color=BORDER,
            font=("Segoe UI", 14), command=self.toggle_tok).pack(side="right")

        # botnames
        nf = self.make_card(main)
        hdr = ctk.CTkFrame(nf, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(12, 4))
        ctk.CTkLabel(hdr, text="BOTNAMES", font=("Segoe UI", 11, "bold"),
            text_color=TEXT_DIM).pack(side="left")
        ctk.CTkButton(hdr, text="Load File", width=90, height=28, fg_color=ACCENT_DIM,
            hover_color=ACCENT, text_color=TEXT, font=("Segoe UI", 11),
            corner_radius=6, command=self.load_names).pack(side="right")

        self.names_box = ctk.CTkTextbox(nf, height=100, fg_color=CARD, border_color=BORDER,
            border_width=1, text_color=TEXT, font=("Consolas", 12), corner_radius=8)
        self.names_box.pack(fill="x", padx=16, pady=(4, 12))

        # proxies
        pf = self.make_card(main)
        phdr = ctk.CTkFrame(pf, fg_color="transparent")
        phdr.pack(fill="x", padx=16, pady=(12, 4))
        ctk.CTkLabel(phdr, text="PROXIES", font=("Segoe UI", 11, "bold"),
            text_color=TEXT_DIM).pack(side="left")

        self.proxy_type = ctk.StringVar(value="http")
        ctk.CTkSegmentedButton(phdr, values=["http", "socks5"], variable=self.proxy_type,
            font=("Segoe UI", 10), height=26, fg_color=CARD, selected_color=ACCENT,
            selected_hover_color=ACCENT_HVR, unselected_color=CARD,
            unselected_hover_color=ACCENT_DIM, text_color=TEXT).pack(side="right", padx=(8, 0))

        ctk.CTkButton(phdr, text="Load File", width=90, height=28, fg_color=ACCENT_DIM,
            hover_color=ACCENT, text_color=TEXT, font=("Segoe UI", 11),
            corner_radius=6, command=self.load_proxies).pack(side="right")

        self.proxy_box = ctk.CTkTextbox(pf, height=70, fg_color=CARD, border_color=BORDER,
            border_width=1, text_color=TEXT, font=("Consolas", 11), corner_radius=8)
        self.proxy_box.pack(fill="x", padx=16, pady=(4, 4))
        ctk.CTkLabel(pf, text="ip:port  /  user:pass@ip:port  /  leave empty for direct",
            font=("Segoe UI", 9), text_color=TEXT_MUTED).pack(anchor="w", padx=16, pady=(0, 10))

        # controls
        ctrl = ctk.CTkFrame(main, fg_color="transparent")
        ctrl.pack(fill="x", pady=(0, 10))

        left = ctk.CTkFrame(ctrl, fg_color=SURFACE, corner_radius=10,
            border_width=1, border_color=BORDER)
        left.pack(side="left")
        ctk.CTkLabel(left, text="Threads", font=("Segoe UI", 11),
            text_color=TEXT_DIM).pack(side="left", padx=(12, 6), pady=8)
        self.thr_var = ctk.StringVar(value="10")
        ctk.CTkEntry(left, textvariable=self.thr_var, width=48, height=30, fg_color=CARD,
            border_color=BORDER, border_width=1, text_color=TEXT, font=("Consolas", 13),
            justify="center").pack(side="left", padx=(0, 12), pady=8)

        self.stop_btn = ctk.CTkButton(ctrl, text="\u23f9  STOP", width=120, height=42,
            fg_color="#7f1d1d", hover_color=RED, text_color=TEXT,
            font=("Segoe UI", 13, "bold"), corner_radius=10,
            command=self.do_stop, state="disabled")
        self.stop_btn.pack(side="right", padx=(8, 0))

        self.start_btn = ctk.CTkButton(ctrl, text="\u25b6  START", width=120, height=42,
            fg_color=ACCENT, hover_color=ACCENT_HVR, text_color="white",
            font=("Segoe UI", 13, "bold"), corner_radius=10, command=self.do_start)
        self.start_btn.pack(side="right")

        # progress
        prf = self.make_card(main, pad_bot=10)
        pri = ctk.CTkFrame(prf, fg_color="transparent")
        pri.pack(fill="x", padx=16, pady=12)

        self.prog_lbl = ctk.CTkLabel(pri, text="Ready", font=("Segoe UI", 12), text_color=TEXT_DIM)
        self.prog_lbl.pack(anchor="w")

        self.pbar = ctk.CTkProgressBar(pri, height=14, corner_radius=7,
            fg_color=CARD, progress_color=ACCENT, border_width=0)
        self.pbar.pack(fill="x", pady=(6, 10))
        self.pbar.set(0)

        stats = ctk.CTkFrame(pri, fg_color="transparent")
        stats.pack(fill="x")
        self.s_avail = self.make_stat(stats, "Available", GREEN)
        self.s_taken = self.make_stat(stats, "Taken", RED)
        self.s_errs = self.make_stat(stats, "Errors", AMBER)
        self.s_proxy = self.make_stat(stats, "Proxies", CYAN, "\u2014")
        self.s_rate = self.make_stat(stats, "Rate", TEXT_DIM, "\u2014")

        # results
        rf = self.make_card(main, expand=True)
        self.section_lbl(rf, "RESULTS")
        self.log = ctk.CTkTextbox(rf, fg_color=CARD, border_color=BORDER, border_width=1,
            text_color=TEXT, font=("Consolas", 12), corner_radius=8)
        self.log.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self.log.configure(state="disabled")

        for tag, col in [("avail", GREEN), ("taken", RED), ("err", AMBER),
                         ("rl", AMBER), ("dim", TEXT_DIM), ("proxy", CYAN)]:
            self.log._textbox.tag_configure(tag, foreground=col)

    # helpers

    def make_card(self, parent, pad_bot=10, expand=False):
        f = ctk.CTkFrame(parent, fg_color=SURFACE, corner_radius=12,
            border_width=1, border_color=BORDER)
        f.pack(fill="both" if expand else "x", expand=expand, pady=(0, pad_bot))
        return f

    def section_lbl(self, parent, txt):
        ctk.CTkLabel(parent, text=txt, font=("Segoe UI", 11, "bold"),
            text_color=TEXT_DIM).pack(anchor="w", padx=16, pady=(12, 4))

    def make_stat(self, parent, label, color, init="0"):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(side="left", expand=True)
        v = ctk.CTkLabel(f, text=init, font=("Segoe UI", 18, "bold"), text_color=color)
        v.pack()
        ctk.CTkLabel(f, text=label, font=("Segoe UI", 10), text_color=TEXT_MUTED).pack()
        return v

    def toggle_tok(self):
        self.show_tok = not self.show_tok
        self.tok_entry.configure(show="" if self.show_tok else "\u2022")

    def load_names(self):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All", "*.*")])
        if path:
            with open(path, "r", encoding="utf-8") as f:
                self.names_box.delete("1.0", "end")
                self.names_box.insert("1.0", f.read())

    def load_proxies(self):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All", "*.*")])
        if path:
            with open(path, "r", encoding="utf-8") as f:
                self.proxy_box.delete("1.0", "end")
                self.proxy_box.insert("1.0", f.read())

    def write_log(self, text, tag):
        self.log.configure(state="normal")
        self.log._textbox.insert("end", text + "\n", tag)
        self.log._textbox.see("end")
        self.log.configure(state="disabled")

    def update_stats(self, cycler=None):
        self.s_avail.configure(text=str(self.avail))
        self.s_taken.configure(text=str(self.taken))
        self.s_errs.configure(text=str(self.errs))
        if cycler:
            a, t = cycler.alive, cycler.total
            self.s_proxy.configure(text=f"{a}/{t}" if t else "off",
                text_color=GREEN if a == t else AMBER if a else RED)
        if self.total > 0:
            pct = self.checked / self.total
            self.pbar.set(pct)
            self.prog_lbl.configure(text=f"Checking...  {self.checked}/{self.total}  ({pct:.0%})")
        if self.checked > 0:
            rate = self.checked / max(time.time() - self.t0, 0.01)
            self.s_rate.configure(text=f"{rate:.1f}/s")

    def flash(self, msg):
        self.prog_lbl.configure(text=msg, text_color=RED)
        self.after(3000, lambda: self.prog_lbl.configure(text="Ready", text_color=TEXT_DIM))

    def pulse(self):
        if not self.running:
            self.pbar.configure(progress_color=ACCENT)
            return
        t = time.time()
        f = 0.5 + 0.5 * math.sin(t * 3.5)
        r = int(0x7c + (0xa7 - 0x7c) * f)
        g = int(0x3a + (0x8b - 0x3a) * f)
        b = int(0xed + (0xfa - 0xed) * f)
        self.pbar.configure(progress_color=f"#{r:02x}{g:02x}{b:02x}")
        self.after(45, self.pulse)

    # main logic

    def do_start(self):
        token = self.tok_entry.get().strip()
        if not token:
            self.flash("Enter your token first")
            return

        raw = self.names_box.get("1.0", "end").strip()
        names = [n.strip() for n in raw.splitlines() if len(n.strip()) >= 4]
        if not names:
            self.flash("Add botnames (min 4 chars each)")
            return

        try: n_thr = max(1, min(100, int(self.thr_var.get())))
        except ValueError: n_thr = 10

        proxy_raw = self.proxy_box.get("1.0", "end").strip()
        plist = parse_proxies(proxy_raw, self.proxy_type.get())
        cycler = ProxyCycler(plist)

        self.running = True
        self.stop_flag.clear()
        self.checked = self.avail = self.taken = self.errs = 0
        self.total = len(names)
        self.t0 = time.time()
        self.pbar.set(0)
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.prog_lbl.configure(text=f"Checking...  0/{self.total}  (0%)", text_color=TEXT_DIM)
        self.s_rate.configure(text="\u2014")
        self.s_proxy.configure(
            text=f"{cycler.total}" if cycler.total else "off",
            text_color=CYAN if cycler.total else TEXT_MUTED)
        self.pulse()

        if cycler.total:
            self.after(0, lambda: self.write_log(
                f" \u25cb Loaded {cycler.total} proxies ({self.proxy_type.get()}), {n_thr} threads", "proxy"))
        else:
            self.after(0, lambda: self.write_log(
                f" \u25cb Direct mode (no proxies), {n_thr} threads", "dim"))

        q = Queue()
        for name in names: q.put(name)

        def worker():
            while not q.empty() and not self.stop_flag.is_set():
                name = q.get()
                resp, tag = "", "err"
                retries = max(cycler.total, 1) * 2
                attempt = 0

                while not self.stop_flag.is_set():
                    attempt += 1
                    proxy = cycler.next()
                    try:
                        r = requests.post("https://api.ai.com/user/botname/check",
                            data=json.dumps({"botname": name}),
                            headers={"Content-Type": "application/json",
                                     "Cookie": f"token={token};"},
                            proxies=proxy, timeout=15)
                        resp = r.text.strip()

                        if "exceeded the site's rate limits" in resp.lower():
                            self.after(0, lambda n=name: self.write_log(
                                f" \u23f3 {n}: rate-limited, retrying...", "rl"))
                            time.sleep(10)
                            continue

                        # try parsing json response
                        try:
                            data = json.loads(resp)
                            if data.get("available", False):
                                tag = "avail"
                                with self.lock: self.avail += 1
                            else:
                                tag = "taken"
                                with self.lock: self.taken += 1
                        except (json.JSONDecodeError, AttributeError):
                            # fallback to string matching
                            if "available" in resp.lower():
                                tag = "avail"
                                with self.lock: self.avail += 1
                            elif "taken" in resp.lower() or "unavailable" in resp.lower():
                                tag = "taken"
                                with self.lock: self.taken += 1
                            else:
                                with self.lock: self.errs += 1
                        break

                    except Exception as exc:
                        if proxy and attempt < retries:
                            cycler.kill(proxy)
                            if cycler.alive > 0: continue
                        resp = str(exc)[:80]
                        with self.lock: self.errs += 1
                        break

                with self.lock: self.checked += 1
                icon = {"avail": "\u2713", "taken": "\u2717", "err": "\u26a0"}.get(tag, "\u00b7")
                self.after(0, lambda n=name, rt=resp, t=tag, ic=icon:
                    self.write_log(f" {ic} {n}: {rt}", t))
                self.after(0, lambda: self.update_stats(cycler))

                with self.lock:
                    with open("checked.txt", "a", encoding="utf-8") as f:
                        f.write(f"{name}: {resp}\n")
                q.task_done()

        def run():
            threads = [threading.Thread(target=worker, daemon=True) for _ in range(n_thr)]
            for t in threads: t.start()
            for t in threads: t.join()
            self.after(0, self.finish)

        threading.Thread(target=run, daemon=True).start()

    def do_stop(self):
        self.stop_flag.set()
        self.prog_lbl.configure(text=f"Stopping...  {self.checked}/{self.total}")

    def finish(self):
        self.running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        elapsed = time.time() - self.t0
        self.pbar.set(1.0 if self.checked >= self.total else self.checked / max(self.total, 1))
        self.prog_lbl.configure(
            text=f"Done \u2014 {self.checked}/{self.total} checked in {elapsed:.1f}s", text_color=GREEN)
        self.write_log(f"\n Finished in {elapsed:.1f}s  "
            f"({self.avail} available, {self.taken} taken, {self.errs} errors)", "dim")

    def on_close(self):
        self.stop_flag.set()
        self.after(100, self.destroy)


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    App().mainloop()
