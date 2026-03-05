from PIL import Image, ImageTk # pip install pillow
import numpy as np             # pip install numpy

from solve_1 import get_k_layer

import tkinter as tk
from tkinter import ttk
import platform

"""
tk  — это классические виджеты Tk, созданные ещё в 90‑х.
ttk — это “themed Tk”, современная библиотека поверх Tk, добавляющая темы и стили.

tk‑виджеты выглядят одинаково на всех ОС (серые, квадратные).
ttk‑виджеты используют нативные темы ОС (Windows, macOS, Linux).

Пример:
tk.Button  выглядит как старый серый прямоугольник.
ttk.Button выглядит как нормальная кнопка Windows/macOS.
"""

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
    def __init__(self, parent, ctrl_cb):
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

        # Мыщ
        self.ctrl_cb  = ctrl_cb
        self.is_combo = False
        self._bind_mousewheel()

    def _on_frame_configure(self, event):
        # Получаем реальный размер внутреннего фрейма
        w = self.inner.winfo_reqwidth()
        h = self.inner.winfo_reqheight()

        # Обновляем размер окна внутри Canvas
        #self.canvas.itemconfig(self.inner_id, width=w)

        # Обновляем scrollregion
        self.canvas.configure(scrollregion=(0, 0, w, h))

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
        if self.is_combo:
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

        can       = self.canvas
        scroll_fn = (
                 self.ctrl_cb     if is_ctrl
            else can.xview_scroll if is_shift
            else can.yview_scroll
        )

        if event.num == 4:   # Linux scroll up
            scroll_fn(-1, "units")
        elif event.num == 5: # Linux scroll down
            scroll_fn(1, "units")
        else:                # Windows / macOS
            scroll_fn(-1 * (event.delta // 120), "units")



class BitPlaneGUI(tk.Tk):
    @staticmethod
    def _grid(root):
        frame = ttk.Frame(root)
        frame.pack(pady=10)

        labels = []
        for r in range(2):
            row = []
            for c in range(4):
                label = ttk.Label(frame)
                label.grid(row=r, column=c, padx=0, pady=0)
                row.append(label)
            labels.append(row)
        return labels

    def __init__(self, container_names, cb):
        super().__init__()
        self.title("Bit-plane Viewer")
        self.geometry("1400x1000")

        self.cb   = cb
        self.pixs = None
        self.pix  = None
        self.images = []
        self.zoom = 1.

        root = ScrollableFrame(self, self.ctrl_cb)
        root.pack(side="top", fill="both", expand=True)

        self.top_labels = self._grid(root.inner)

        # Выпадающий список выбора набора
        self.combo = combo = ttk.Combobox(
            root.inner,
            values=container_names,
            state="readonly"
        )
        combo.pack(pady=0)
        combo.bind("<<ComboboxSelected>>", self.on_select_base)
        def is_combo(value): root.is_combo = value
        combo.bind("<Enter>", lambda e: is_combo(True))
        combo.bind("<Leave>", lambda e: is_combo(False))
        combo.current(0)

        self.bottom_labels = self._grid(root.inner)

        self.on_select_base()

    def on_select_base(self, event=None):
        base = self.combo.get()

        self.pixs = self.cb(base)

        self.show_original_previews()
        self.on_click_original(0)

    def show_original_previews(self):
        self.images.clear()
        assert len(self.pixs) == 8

        size = int(256 * self.zoom)
        for idx, pix in enumerate(self.pixs):
            img = Image.fromarray(pix.astype(np.uint8))
            img = img.resize((size, size), Image.NEAREST)
            tk_img = ImageTk.PhotoImage(img)

            r, c = divmod(idx, 4)

            lbl = self.top_labels[r][c]
            lbl.configure(image=tk_img)
            lbl.image = tk_img

            # важно: сохранить индекс, чтобы знать, по какой картинке кликнули
            lbl.bind("<Button-1>", lambda e, i=idx: self.on_click_original(i))

            # если не сохранить PhotoImage, мусоросборщик её съест...
            self.images.append(tk_img)

    def on_click_original(self, idx):
        self.pix = self.pixs[idx]
        self.show_bit_planes()

    def show_bit_planes(self): # остальные 8 картинок
        if self.pix is None:
            return

        size = int(256 * self.zoom)
        for k in range(1, 9):
            plane = get_k_layer(self.pix, k) * 255
            img = Image.fromarray(plane.astype(np.uint8))
            img = img.resize((size, size), Image.NEAREST)
            tk_img = ImageTk.PhotoImage(img)

            r, c = divmod(k - 1, 4)

            lbl = self.bottom_labels[r][c]
            lbl.configure(image=tk_img, text=f"k={k}", compound="top")
            lbl.image = tk_img

            self.images.append(tk_img)

    def ctrl_cb(self, direction, units):
        self.zoom = max(0.2, min(self.zoom / 1.25 ** direction, 2))
        self.show_original_previews()
        self.show_bit_planes()



if __name__ == "__main__":
    from solve_1 import bmp_sampler_from_zip
    container_names = ("BOSSbase", "medical", "portrait")
    def cb(name):
        match name:
            case "BOSSbase": path = "bossbase_containers.zip"
            case "medical":  path = "medical_containers.zip"
            case "portrait": path = "portrait_containers.zip"
        return bmp_sampler_from_zip(path, 8)

    app = BitPlaneGUI(container_names, cb)
    app.bind("d", lambda e: dump_tree(app))
    app.mainloop()
