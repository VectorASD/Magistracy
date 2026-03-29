from PIL import Image, ImageTk, ImageDraw # pip install pillow
import numpy as np                        # pip install numpy



import tkinter as tk
from tkinter import ttk

"""
tk  — это классические виджеты Tk, созданные ещё в 90‑х.
ttk — это “themed Tk”, современная библиотека поверх Tk, добавляющая темы и стили.

tk‑виджеты выглядят одинаково на всех ОС (серые, квадратные).
ttk‑виджеты используют нативные темы ОС (Windows, macOS, Linux).

Пример:
tk.Button  выглядит как старый серый прямоугольник.
ttk.Button выглядит как нормальная кнопка Windows/macOS.
"""

import platform
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
from functools import lru_cache

win = platform.system() == "Windows"



def debug_widget_tree(widget, indent=0):
    pad = "  " * indent
    cls = widget.__class__.__name__
    geom = widget.winfo_manager()

    try:
        x, y = widget.winfo_x(), widget.winfo_y()
        w, h = widget.winfo_width(), widget.winfo_height()
        rw, rh = widget.winfo_reqwidth(), widget.winfo_reqheight()
    except:
        x = y = w = h = rw = rh = -1

    print(f"{pad}{cls}  geom={geom}  pos=({x},{y})  size=({w}×{h})  req=({rw}×{rh})")

    # Если это Canvas — покажем scrollregion
    if isinstance(widget, tk.Canvas):
        print(f"{pad}  scrollregion={widget.cget('scrollregion')}")

    # Рекурсивно обходим детей
    for child in widget.winfo_children():
        debug_widget_tree(child, indent + 1)

def dump_tree(app):
    app.update_idletasks()
    debug_widget_tree(app)



class ScrollableFrame(ttk.Frame):
    def __init__(self, parent, ctrl_cb=None, *, to_bottom=False):
        super().__init__(parent)

        # Критично: дать фрейму реальный минимальный размер
        self.config(width=200, height=200)
        self.pack_propagate(False)

        # Контейнер для Canvas
        # Иначе, нижний ползунок будет занимать минимальную область справа от холста :///
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(side="left", fill="both", expand=True)

        # Холст
        self.canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        self.canvas.pack(side="top", fill="both", expand=True)

        # Скроллбары
        self.h_scroll = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self.canvas.xview)
        self.v_scroll = ttk.Scrollbar(self,         orient="vertical", command=self.canvas.yview)
        
        self.h_scroll.pack(side="bottom", fill="x")
        self.v_scroll.pack(side="right", fill="y")

        self.canvas.configure(
            yscrollcommand=self.v_scroll.set,
            xscrollcommand=self.h_scroll.set
        )

        # Внутренний фрейм, который будет скроллиться
        self.inner    = ttk.Frame(self.canvas)
        self.inner_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        # Обновление scrollregion при изменении размера
        self.inner.bind("<Configure>",  self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.to_bottom = to_bottom

        # Мыщ
        self.ctrl_cb  = ctrl_cb
        self.is_combo = None
        self._bind_mousewheel()

    def _on_frame_configure(self, event):
        # Получаем реальный размер внутреннего фрейма
        w = self.inner.winfo_reqwidth()
        h = self.inner.winfo_reqheight()

        # Обновляем scrollregion
        self.canvas.configure(scrollregion=(0, 0, w, h))
        if self.to_bottom:
            self.to_bottom = False
            self.after(0, lambda: self.canvas.yview_moveto(1.0))

    def _on_canvas_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _bind_mousewheel(self):
        # Windows / macOS
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        # Linux
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        # события колеса мыши перехватываются Combobox
        # и дублируются в вертикальный scrollbar :/
        if self.is_combo is not None and self.is_combo.get():
            return

        # print(hex(event.state))
        is_shift = bool(event.state & 0x00001) # Shift mask
        is_ctrl  = bool(event.state & 0x00004) # Ctrl  mask
        alt_mask = 0x20000 if win else 0x00008 # Alt   mask
        is_alt   = bool(event.state & alt_mask)
        # 00002 - shift  lock (средняя лампочка клавиатуры)
        # 00008 - num    lock (нижняя  лампочка клавиатуры)
        # 00020 - scroll lock (верхняя лампочка клавиатуры)
        # 00100 - ЛКМ зажата
        # 00200 - СКМ зажата
        # 00400 - ПКМ зажата

        # mods = ('Shift', 'Lock', 'Control', 'Mod1', 'Mod2', 'Mod3', 'Mod4', 'Mod5', 'Button1', 'Button2', 'Button3', 'Button4', 'Button5')
        # прямо из: %LocalAppData%\Programs\Python\Python314\Lib\tkinter\__init__.py:272

        can       = self.canvas
        scroll_fn = (
                 self.ctrl_cb     if is_ctrl
            else can.xview_scroll if is_shift
            else can.yview_scroll
        )
        if scroll_fn is None:
            return

        if event.num == 4:   # Linux scroll up
            scroll_fn(-1, "units")
        elif event.num == 5: # Linux scroll down
            scroll_fn(1, "units")
        else:                # Windows / macOS
            scroll_fn(-1 * (event.delta // 120), "units")

class ControlPanel(ttk.Frame):
    def __init__(self, master, opts):
        super().__init__(master)
        self.combos = []
        self.is_combo = tk.BooleanVar()

        for entry in opts:
            names     = tuple(item for item in entry if isinstance(item, (str, bool, int, float, complex)))
            callbacks = tuple(item for item in entry if callable(item))
            metas     = tuple(item for item in entry if isinstance(item, dict))

            assert names, "Нужны имена"
            assert len(callbacks) == 1, "Должен быть ровно один callback"

            callback = callbacks[0]
            meta = {k: v for meta in metas for k, v in meta.items()}
            default = meta.get("default", None)

            # Кнопка
            if len(names) == 1:
                name = names[0]
                assert default is None
                def on_press(cb=callback):
                    cb()
                btn = ttk.Button(self, text=name, command=on_press)
                btn.pack(side="left", padx=4)

            # Чекбокс
            elif len(names) == 2 and names[0] == names[1]:
                name = names[0]
                var = tk.BooleanVar()
                if default is not None:
                    var.set(default)
                def on_toggle(var=var, cb=callback):
                    cb(var.get())
                chk = ttk.Checkbutton(self, text=name, variable=var, command=on_toggle)
                chk.pack(side="left", padx=4)

            # Выпадающий список
            else:
                combo = ttk.Combobox(self, values=names, state="readonly")
                def on_select(event=None, cb=callback, combo=combo):
                    cb(combo.get())
                def is_combo(event):
                    # print(event.type) # 7 и 8
                    # >>> tk.EventType.Enter -> <EventType.Enter: '7'>
                    # >>> tk.EventType.Leave -> <EventType.Leave: '8'>
                    event.widget._entered = event.type == tk.EventType.Enter
                    is_combo = any(combo._entered for combo in self.combos)
                    self.is_combo.set(is_combo)
                combo.bind("<<ComboboxSelected>>", on_select)
                combo.bind("<Enter>", is_combo)
                combo.bind("<Leave>", is_combo)
                combo.pack(side="left", padx=4)
                combo._entered = False
                combo._default = default
                self.combos.append(combo)

    def postinit(self):
        for combo in self.combos:
            combo.current(combo._default or 0)
            combo.event_generate("<<ComboboxSelected>>")



class ImageGrid(ttk.Frame):
    def __init__(self, master, rows=2, cols=4, padx=0, pady=0):
        super().__init__(master)

        self.labels = []

        for r in range(rows):
            row = []
            for c in range(cols):
                lbl = ttk.Label(self)
                lbl.grid(row=r, column=c, padx=padx, pady=pady)
                row.append(lbl)
            self.labels.append(row)



class BitPlaneGUI(tk.Tk):
    def __init__(self, plane_cb, opts):
        super().__init__()
        self.title("Bit-plane Viewer")
        x = (1920 - 1400) // 2
        self.geometry(f"1400x1000+{x}+0")
        self.bind("d", lambda e: dump_tree(self))

        self.plane_cb = plane_cb # (pix, k) -> (plane, k_label) 
        self.pixs     = None
        self.pix      = None
        self.prev_idx = None
        self.zoom     = 1.

        root = ScrollableFrame(self, self.ctrl_cb, to_bottom=True)
        root.pack(side="top", fill="both", expand=True)

        self.top = ImageGrid(root.inner, rows=2, cols=4)
        self.top.pack(side="top", pady=0)

        panel = ControlPanel(root.inner, opts)
        panel.pack(side="top", fill="x", pady=5)
        root.is_combo = panel.is_combo

        self.bottom = ImageGrid(root.inner, rows=2, cols=4)
        self.bottom.pack(side="top", pady=0)

        def on_gui_ready():
            panel.postinit()
        self.after_idle(on_gui_ready)

    def show_original_previews(self, pixs=None):
        if pixs is not None:
            self.pixs = pixs
            self.prev_idx = None
        if self.pixs is None:
            return

        assert len(self.pixs) == 8

        size = int(256 * self.zoom)
        for idx, pix in enumerate(self.pixs):
            img = Image.fromarray(pix.astype(np.uint8))
            img = img.resize((size, size), Image.NEAREST)
            tk_img = ImageTk.PhotoImage(img)

            r, c = divmod(idx, 4)

            lbl = self.top.labels[r][c]
            lbl.configure(image=tk_img)
            lbl.image = tk_img
            lbl._idx = idx

            def on_motion(event):
                Button1 = event.state & 0x00100 # ЛКМ
                if Button1 or event.type == tk.EventType.ButtonPress:
                    x = event.x_root
                    y = event.y_root
                    w = event.widget.winfo_containing(x, y)
                    if hasattr(w, "_idx"):
                        self.on_click_original(w._idx)
            lbl.bind("<ButtonPress-1>", on_motion)
            lbl.bind("<Motion>",        on_motion) # случайно переизобрёл <B1-Motion> ...

            # если не сохранить PhotoImage, мусоросборщик её съест...
            #     lbl.configure(image=tk_img) не создаёт ссылку в Python
            #     lbl.image = tk_img          создаёт ссылку
            #     self.images.append(tk_img)  тоже создаёт ссылку
            # по этому self.images НЕ нужен

    def on_click_original(self, idx):
        if self.prev_idx != idx:
            self.prev_idx = idx
            self.pix = self.pixs[idx]
            self.show_bit_planes()

    def show_bit_planes(self): # остальные 8 картинок
        if self.pix is None:
            return

        self.planes = planes = []
        size = int(256 * self.zoom)
        for k in range(1, 9):
            plane, k_label = self.plane_cb(self.pix, k)
            img = Image.fromarray(plane.astype(np.uint8))
            img = img.resize((size, size), Image.NEAREST)
            tk_img = ImageTk.PhotoImage(img)

            r, c = divmod(k - 1, 4)

            lbl = self.bottom.labels[r][c]
            lbl.configure(image=tk_img, text=k_label, compound="top")
            lbl.image = tk_img

            planes.append(plane)

    def ctrl_cb(self, direction, units):
        self.zoom = max(0.2, min(self.zoom / 1.25 ** direction, 2))
        self.show_original_previews()
        self.show_bit_planes()



class ImageGridBase:
    def __init__(self, rows=1, cols=1, preset=()):
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        win_w, win_h = 1400, 1000

        x = (screen_w - win_w) // 2
        y = (screen_h - win_h) // 2

        self.geometry(f"{win_w}x{win_h}+{x}+{y}")

        self.images = [None] * (rows * cols)
        self.zoom   = 1.
        self.error  = None

        root = ScrollableFrame(self, self.ctrl_cb, to_bottom=True)
        root.pack(side="top", fill="both", expand=True)

        self.grid = ImageGrid(root.inner, rows=rows, cols=cols)
        self.grid.pack(side="top", pady=0)

        if isinstance(preset, (tuple, list)):
            for idx, pix in enumerate(preset):
                self.set_image(idx, pix, update=False)
        else:
            self.set_image(0, preset, update=False)
        self.show()

    def calculate_async(self, cb):
        if self.plt:
            # запускаем асинхронную генерацию
            executor = ThreadPoolExecutor(max_workers=8)
            for idx, pix in enumerate(self.pixs):
                executor.submit(cb, idx, pix)

    @staticmethod
    @lru_cache
    def get_placeholder(size):
        placeholder = Image.new("RGB", (size, size), "white")
        draw = ImageDraw.Draw(placeholder)
        draw.rectangle((5, 5, size-5, size-5), outline="black", width=5)

        return placeholder

    def show_one(self, idx, text=None):
        size = int(256 * self.zoom)
        image = self.images[idx]
        image = self.get_placeholder(size) if image is None else image.resize((size, size), Image.LANCZOS if self.zoom < 1.0 else Image.NEAREST)
        tk_img = ImageTk.PhotoImage(image)

        r, c = divmod(idx, len(self.grid.labels[0]))
        lbl = self.grid.labels[r][c]
        try:
            text = self.error or text
            if text is None:
                lbl.configure(image=tk_img, text="",   compound="none")
            else:
                lbl.configure(image=tk_img, text=text, compound="top")
        except: pass
        lbl.image = tk_img

    def set_image(self, idx, pix, *, update=True):
        if isinstance(pix, np.ndarray):
            pix = Image.fromarray(pix)
        self.images[idx] = pix
        if update:
            self.after(0, lambda: self.show_one(idx))
        return self

    def show(self):
        for idx in range(len(self.images)):
            self.show_one(idx)

    def ctrl_cb(self, direction, units):
        self.zoom = max(0.2, min(self.zoom / 1.25 ** direction, 2))
        self.show()



class ImageGridGUI(tk.Tk, ImageGridBase):
    def __init__(self, rows=1, cols=1, preset=()):
        tk.Tk.__init__(self)
        self.title("Image-grid Viewer")

        ImageGridBase.__init__(self, rows, cols, preset)



class HistogramGUI(tk.Toplevel, ImageGridBase):
    def __init__(self, master, pixs, current, rows=4, cols=4):
        tk.Toplevel.__init__(self, master)
        self.title("Histograms (Original vs Stego)")

        plt = None
        try: import matplotlib.pyplot as plt
        except ImportError: self.error = "pip install matplotlib"
        self.plt = plt            

        assert len(pixs) == rows * cols
        self.pixs = pixs
        self.current   = current

        ImageGridBase.__init__(self, rows, cols) # показываем заглушки
        self.calculate_async(self.calculate_one)

    def calculate_one(self, idx, pix):
        # np_hist, bins = np.histogram(pix, bins=256, range=(0, 255))
        # аналогично:
        flat = pix.reshape(-1)
        hist = np.bincount(flat, minlength=256)

        # Рисуем matplotlib-график
        fig, ax = self.plt.subplots(figsize=(3, 2), dpi=512)
        ax.plot(hist, color="blue", linewidth=1.5)
        ax.tick_params(axis='x', colors='green')
        ax.tick_params(axis='y', colors='green')
        text = f"img#{idx+1}" if idx < 8 else f"k={idx-7}"
        if idx == self.current: text += " (CURRENT)"
        ax.set_title(text, color="black")
        ax.set_xlim(0, 255)

        # Закидываем в png
        buf = BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        self.plt.close(fig)

        # Конвертируем в tkinter-картинку
        buf.seek(0)
        img = Image.open(buf)

        # обновляем GUI
        self.set_image(idx, img)



def plot_ci(rows, title, filename):
    import matplotlib.pyplot as plt # pip install matplotlib

    # Группируем данные по базе
    bases = defaultdict(list)
    for base, k, std, low, avg, high in rows:
        bases[base].append((k, avg, low, high))

    plt.figure(figsize=(10, 6), dpi=640)

    for base, data in bases.items():
        ks, avgs, lows, highs = zip(*data)
        avgs  = np.array(avgs)
        lows  = np.array(lows)
        highs = np.array(highs)

        plt.errorbar(
            ks,
            avgs,
            yerr=(avgs - lows, highs - avgs), # восстанавливаем назад margin, но как Y в графиках
            capsize=5,
            label=base
        )

    plt.xlabel("k (битовая плоскость)")
    plt.ylabel("PSNR (дБ)")
    plt.title(title)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(filename, dpi=200)
    plt.close()
    print("График сохранён: psnr_ci_graph.png")
"""
Почему «свечи» (plt.errorbar) похожи на свечи на криптобирже?
Потому что визуально:
    есть центральное значение (у нас — среднее PSNR, на бирже — цена открытия/закрытия)
    есть верхняя граница (у нас — верхний доверительный интервал, на бирже — максимум цены)
    есть нижняя граница (у нас — нижний доверительный интервал, на бирже — минимум цены)
То есть форма похожа, но смысл разный.
"""



if __name__ == "__main__":
    from solve_1 import MainGUI
    from solve_2 import check_gradient

    # MainGUI().mainloop()
    check_gradient()
