"""
GUI-клиент чата на tkinter.

Запуск: python chat_gui.py HOST PORT

Handshake (UID, join, password, create) — в консоли, как в client.py.
Окно создаётся при первом redraw от клиента, в фоновом потоке.
Main-поток крутит _loop Client — Ctrl+C в консоли завершает всё.
"""

import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from hashlib import sha256
from pathlib import Path

from client import app as run_client


# ---------- палитра ----------

PEER_COLORS = [
    "#e15052",  # 7  красный
    "#e0802b",  # 8  оранжевый
    "#a05ff3",  # 9  фиолетовый
    "#27a910",  # 10 зелёный
    "#27acce",  # 11 бирюзовый
    "#3391d4",  # 12 синий
    "#dd4371",  # 13 розовый
    "#247bed",  # 14 синий
    "#d67722",  # 15 тёмно-оранжевый
    "#179e42",  # 16 зелёный
    "#2894af",  # 17 тёмно-бирюзовый
    "#0c9ab3",  # 18 бирюзовый
    "#7757d6",  # 19 фиолетовый
    "#1585cf",  # 20 голубой
]

def peer_color(uid: str) -> str:
    hash = sha256(uid.encode("utf-8")).digest()
    n = int.from_bytes(hash)
    return PEER_COLORS[n % len(PEER_COLORS)]

BG           = "#98bd94"   # из текстуры фона
HEADER_BG    = "#ffffff"   # --background-color
OTHER_BUBBLE = "#ffffff"   # --background-color
MY_BUBBLE    = "#eeffde"   # --color-background-own (светло-зелёный Telegram)
TEXT         = "#000000"   # --color-text
INPUT_BG     = "#ffffff"   # --color-background
BTN_BG       = "#3390ec"   # --color-primary (голубой Telegram)
BTN_FG       = "#ffffff"

FONT_HEADER = ("Segoe UI", 10)
FONT_NAME   = ("Segoe UI", 11)
FONT_TEXT   = ("Segoe UI", 12)

MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 Mb


def format_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB", "PB", "EB"):
        if n < 1024:
            break
        n /= 1024
    return f"{n:.2f}".rstrip('0').rstrip('.') + f" {unit}"


class ChatGui:
    def __init__(self):
        self.root = None
        self.client = None
        self.uid = None
        self._last_sender = None
        self.queue = queue.Queue()
        self.ready = threading.Event()

        # виджеты
        self.header = None
        self.canvas = None
        self.scroll = None
        self.chat = None
        self.entry = None

    # ---------- точка входа из Client._loop ----------

    def redraw(self, uid, room_id, members, messages):
        """
        Вызывается из main-потока (Client._loop).
        Первый вызов — создаёт окно в daemon-потоке.
        Все вызовы кладут снимок состояния в очередь.
        """
        if self.root is None:
            self._spawn()
            self.ready.wait()
        self.queue.put((uid, room_id, members, messages))

    # ---------- GUI-поток ----------

    def _spawn(self):
        threading.Thread(target=self._gui_thread, daemon=True).start()

    def _gui_thread(self):
        self.root = tk.Tk()
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(50, self._poll)
        self.ready.set()
        self.root.mainloop()

    def _build(self):
        self.root.title("chat")
        self.root.geometry("720x600")
        self.root.configure(bg=BG)

        # --- шапка ---
        header = tk.Frame(self.root, bg=HEADER_BG, height=40)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        self.header = tk.Label(
            header, text="", bg=HEADER_BG, fg=TEXT,
            anchor="w", padx=12, font=FONT_HEADER,
        )
        self.header.pack(fill="both", expand=True)

        # --- область чата со скроллом ---
        wrap = tk.Frame(self.root, bg=BG)
        wrap.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(wrap, bg=BG, highlightthickness=0)
        self.scroll = ttk.Scrollbar(
            wrap, orient="vertical", command=self.canvas.yview,
        )
        self.chat = tk.Frame(self.canvas, bg=BG)
        self.chat.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            ),
        )
        self._canvas_window = self.canvas.create_window(
            (0, 0), window=self.chat, anchor="nw",
        )
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scroll.pack(side="right", fill="y")

        self.canvas.bind_all(
            "<MouseWheel>",
            lambda e: self.canvas.yview_scroll(-e.delta // 120, "units"),
        )

        # --- поле ввода ---
        inp = tk.Frame(self.root, bg=INPUT_BG, height=50)
        inp.pack(fill="x", side="bottom")
        inp.pack_propagate(False)

        tk.Button(
            inp, text="📎", command=self._on_attach,
            font=("Segoe UI Emoji", 20),
            bg=BTN_BG, fg=BTN_FG, relief="flat",
            width=2, activebackground=BTN_BG,
        ).pack(side="left", padx=(12, 0), pady=10)

        self.entry = tk.Entry(
            inp, bg=INPUT_BG, fg=TEXT, insertbackground=TEXT,
            relief="flat", font=FONT_TEXT,
        )
        self.entry.pack(side="left", fill="both", expand=True, padx=(8, 12), pady=10)
        self.entry.bind("<Return>", self._on_send)
        self.entry.focus_set()

        tk.Button(
            inp, text="→", command=self._on_send,
            bg=BTN_BG, fg=BTN_FG, relief="flat",
            width=4, activebackground=BTN_BG,
        ).pack(side="right", padx=(0, 12), pady=10)
        self.entry.bind("<Control-KeyPress>", self._on_ctrl)

    def _on_ctrl(self, event):
        # Windows virtual key codes: A=65, C=67, V=86, X=88
        vk = event.keycode
        if vk == 67:
            self.entry.event_generate("<<Copy>>")
        elif vk == 86:
            self.entry.event_generate("<<Paste>>")
        elif vk == 88:
            self.entry.event_generate("<<Cut>>")
        elif vk == 65:
            self.entry.select_range(0, "end")
            self.entry.icursor("end")
        return "break"

    def _on_attach(self):
        if self.client is None:
            return
        path = filedialog.askopenfilename()
        if not path:
            return

        p = Path(path)
        size = p.stat().st_size
        if size > MAX_FILE_BYTES:
            messagebox.showerror(
                "Файл слишком большой",
                f"{size / 1024 / 1024:.1f} Mb, а максимум: {MAX_FILE_BYTES // 1024 // 1024} Mb",
            )
            return

        self.client.send_message("", p.read_bytes(), p.name)

    # ---------- опрос очереди ----------

    def _poll(self):
        try:
            while True:
                uid, room_id, members, messages = self.queue.get_nowait()
                self._render(uid, room_id, members, messages)
        except queue.Empty:
            pass
        self.root.after(50, self._poll)

    # ---------- отрисовка ----------

    def _on_canvas_resize(self, event):
        """Растянуть chat-фрейм на всю ширину канваса."""
        self.canvas.itemconfig(self._canvas_window, width=event.width)

    def _render(self, uid, room_id, members, messages):
        self.uid = uid

        names = ", ".join(members) if members else "—"
        self.header.config(text=f"{room_id}  ·  ты {uid}  ·  [{names}]")

        for w in self.chat.winfo_children():
            w.destroy()
        self._last_sender = None

        # чуть меньше ширины канваса: padx row (12×2) + padx label (10×2)
        # + scrollbar + запас
        self._wrap = max(200, round(self.canvas.winfo_width() * 0.8))

        for msg in messages:
            self._render_one(msg)

        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)

    def _render_one(self, msg):
        sender = msg["sender"]
        mine = (sender == self.uid)
        first = (self._last_sender != sender)
        self._last_sender = sender

        row = tk.Frame(self.chat, bg=BG)
        row.pack(fill="x", padx=12, pady=(12 if first else 2, 0))

        bubble_bg = MY_BUBBLE if mine else OTHER_BUBBLE
        bubble_fg = peer_color(sender)
        bubble = tk.Frame(row, bg=bubble_bg)
        bubble.pack(side="right" if mine else "left")

        if first and not mine:
            tk.Label(
                bubble, text=sender, bg=bubble_bg, fg=bubble_fg,
                font=FONT_NAME, anchor="w", padx=10
            ).pack(fill="x")

        if msg.get("is_blob"):
            self._render_file(bubble, bubble_bg, msg)
        else:
            text = msg["text"]
            tk.Label(
                bubble, text=text, bg=bubble_bg, fg=TEXT,
                font=FONT_TEXT, anchor="w", justify="left",
                wraplength=self._wrap, padx=10,
            ).pack(fill="x", pady=(0, 6))

    def _render_file(self, parent, bg, msg):
        box = tk.Frame(parent, bg=bg)
        box.pack(fill="x", padx=10, pady=(4, 6))

        # иконка-документ слева
        tk.Label(
            box, text="📄", bg=bg, fg=TEXT,
            font=("Segoe UI Emoji", 23), width=2
        ).pack(side="left", padx=(0, 10), anchor="n")

        # две строки справа: имя + размер
        col = tk.Frame(box, bg=bg)
        col.pack(side="left", fill="x", expand=True)

        name_lbl = tk.Label(
            col, text=msg["filename"], bg=bg, fg=TEXT,
            font=FONT_NAME, anchor="w", justify="left",
            wraplength=self._wrap - 60,
        )
        name_lbl.pack(fill="x")

        size_lbl = tk.Label(
            col, text=format_size(msg["size"]), bg=bg, fg="#707579",
            font=FONT_HEADER, anchor="w",
        )
        size_lbl.pack(fill="x")

        # вся площадь — кликабельна, скачивание по клику
        for w in (box, name_lbl, size_lbl):
            w.configure(cursor="hand2")
            w.bind("<Button-1>", lambda e, m=msg: self._download_file(m))

    # ---------- обработчики ----------

    def _on_send(self, event=None):
        text = self.entry.get().strip()
        if not text or self.client is None:
            return
        self.client.send_message("", text.encode("utf-8"))
        self.entry.delete(0, "end")

    def _download_file(self, msg):
        def on_bytes(result: dict[str, str | bytes]):
            if "error" in result:
                messagebox.showerror("Не удалось скачать файл", result["error"])
                return
            path = filedialog.asksaveasfilename(initialfile=msg["filename"])
            if not path:
                return
            with open(path, "wb") as f:
                f.write(result["content"])

        self.client.fetch_blob(msg["uuid"], on_bytes)

    # ---------- закрытие ----------

    def _on_close(self):
        if self.client is not None:
            self.client.close()
        self.root.quit()
        self.root.destroy()


def main():
    gui = ChatGui()
    run_client(gui=gui)


if __name__ == "__main__":
    main()
