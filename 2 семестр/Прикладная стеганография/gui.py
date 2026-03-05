from PIL import Image, ImageTk # pip install pillow
import numpy as np             # pip install numpy

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
        self.is_combo = None
        self._bind_mousewheel()

    def _on_frame_configure(self, event):
        # Получаем реальный размер внутреннего фрейма
        w = self.inner.winfo_reqwidth()
        h = self.inner.winfo_reqheight()

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
        if self.is_combo.get():
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

            assert names, "Нужны имена"
            assert len(callbacks) == 1, "Должен быть ровно один callback"

            callback = callbacks[0]

            # Кнопка
            if len(names) == 1:
                name = names[0]
                def on_press(cb=callback):
                    cb()
                btn = ttk.Button(self, text=name, command=on_press)
                btn.pack(side="left", padx=4)

            # Чекбокс
            elif len(names) == 2 and names[0] == names[1]:
                name = names[0]
                def on_toggle(event, cb=callback):
                    cb(event.widget._var.get())
                var = tk.BooleanVar()
                chk = ttk.Checkbutton(self, text=name, variable=var)
                chk.bind("<ButtonRelease-1>", on_toggle)
                chk.pack(side="left", padx=4)
                chk._var = var

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
                self.combos.append(combo)

    def postinit(self):
        for combo in self.combos:
            combo.current(0)
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
        self.geometry("1400x1000")
        self.bind("d", lambda e: dump_tree(self))

        self.plane_cb = plane_cb # (pix, k) -> (plane, k_label) 
        self.pixs     = None
        self.pix      = None
        self.prev_idx = None
        self.zoom     = 1.

        root = ScrollableFrame(self, self.ctrl_cb)
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
                if Button1:
                    x = event.x_root
                    y = event.y_root
                    w = event.widget.winfo_containing(x, y)
                    if hasattr(w, "_idx"):
                        self.on_click_original(w._idx)
            lbl.bind("<Motion>", on_motion)

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

    def ctrl_cb(self, direction, units):
        self.zoom = max(0.2, min(self.zoom / 1.25 ** direction, 2))
        self.show_original_previews()
        self.show_bit_planes()



if __name__ == "__main__":
    from solve_1 import gui_main
    gui_main()
