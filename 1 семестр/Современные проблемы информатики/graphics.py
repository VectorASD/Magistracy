import tkinter as tk
from math import pi, sin, cos, hypot, tan
from time import time

from matrix import Matrix, pi_180
from misc import wrap_rounded_rectangle
from geometry import distance



class Camera:
    def __init__(self):
        # self.x, self.y, self.z = self.pos = 0, 0, 5
        self.pos = 0, 0, 2
        self.YPR = -20, 30, 0

        self.fovy   = 90
        self.aspect = 1
        self.near   = 0.1
        self.far    = 100

        self.R            = 1.5
        self.orbital_mode = True

        self.update_proj()

    def update_proj(self):
        fovy, near, far = self.fovy, self.near, self.far
        self.fovy_factor = ff = tan(fovy * pi_180 / 2)
        self.depth_states = near, far, ff

        self.proj = Matrix.perspective(fovy, self.aspect, near, far)
        self.update_proj_view()

    def update_proj_view(self):
        self.view, self.forward, self.right, self.up = Matrix.view(*self.pos, *self.YPR)

        if self.orbital_mode:
            x, y, z = self.forward
            R = -self.R
            self.pos = x * R, y * R, z * R
            self.view, self.forward, self.right, self.up = Matrix.view(*self.pos, *self.YPR)

        self.proj_view = self.proj @ self.view
        self.inv_proj_view = Matrix.fast_inv_proj_view(self.fovy, self.aspect, self.near, self.far, *self.pos, *self.YPR)

    def project_dots(self, dots_arr, viewport):
        return self.proj_view.project(dots_arr, viewport)
    def unproject(self, x, y, viewport):
        return self.inv_proj_view.unproject(x, y, self.proj, viewport)

    def move_to(self, x, y, z):
        self.pos = x, y, z
        self.update_proj_view()
    def move(self, dx, dy, dz):
        x, y, z = self.pos
        self.pos = x + dx, y + dy, z + dz
        self.update_proj_view()
    def rotate(self, dY, dP, dR):
        Y, P, R = self.YPR
        self.YPR = Y + dY, max(-75, min(P + dP, 75)), R + dR
        self.update_proj_view()

    def move_forward(self, dt):
        if self.orbital_mode:
            mul = 1 + abs(dt) * 1.001
            self.R *= 1/mul if dt > 0 else mul
            self.update_proj_view()
        else:
            dx, dy, dz = self.forward
            self.move(dx * dt, dy * dt, dz * dt)

    def move_right(self, dt):
        if self.orbital_mode:
            self.rotate(dt * -90, 0, 0)
            return
        dx, dy, dz = self.right
        self.move(dx * dt, dy * dt, dz * dt)

    def move_up(self, dt):
        if self.orbital_mode:
            self.rotate(0, dt * 90, 0)
            return
        # dx, dy, dz = self.up
        dx, dy, dz = 0, 1, 0 # рациональнее независимый от поворота камеры вариант
        self.move(dx * dt, dy * dt, dz * dt)

    def test(self):
        print(self.proj_view)
        self.move(0, 0, 2)
        self.rotate(0, 0, 45)
        print(self.proj_view)



class KeyboardHandler:
    dbg_keys = {}
    key_table = ('x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'BackSpace', 'Tab', 'x', 'x', 'Clear', 'Return', 'x', 'x', 'Shift_L', 'Control_R', 'Alt_R', 'x', 'Caps_Lock', 'x', 'x', 'x', 'x', 'x', 'x', 'Escape', 'x', 'x', 'x', 'x', 'space', 'Prior', 'Next', 'End', 'Home', 'Left', 'Up', 'Right', 'Down', 'x', 'x', 'x', 'x', 'Insert', 'Delete', 'x', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', 'Win_L', 'x', 'x', 'x', 'x', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'asterisk', 'plus', 'x', 'minus', 'period', 'slash', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'Num_Lock', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'semicolon', 'equal', 'comma', 'minus', 'period', 'slash', 'grave', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'bracketleft', 'backslash', 'bracketright', 'apostrophe')

    def __init__(self, context):
        self.ctx = context
        self.last_time = time()
        self.key_state = set()

    def on_key_press(self, event):
        # KeyboardHandler.dbg_keys[event.keycode] = event.keysym
        key_table = KeyboardHandler.key_table
        key = key_table[event.keycode] if event.keycode in range(len(key_table)) else 'x'
        self.key_state.add(key)
        # print(f"[↓] {key} нажата")

        if key == "q":
            self.ctx.render.change_orbital_mode()

    def on_key_release(self, event):
        key_table = KeyboardHandler.key_table
        key = key_table[event.keycode] if event.keycode in range(len(key_table)) else 'x'
        self.key_state.discard(key)
        # print(f"[↑] {key} отпущена")

    def bind(self):
        root = self.ctx.root
        root.bind("<KeyPress>",   self.on_key_press)
        root.bind("<KeyRelease>", self.on_key_release)
        return self

    def update_move(self):
        T = time()
        dt = T - self.last_time
        self.last_time = T

        key_state = self.key_state
        # if key_state: print(key_state)
        speed = 3 * (2.5 if "Shift_L" in key_state or "Shift_R" in key_state else 1)
        dx = dy = dz = 0

        if "w" in key_state or "Up" in key_state: dz += 1
        if "a" in key_state or "Left" in key_state: dx -= 1
        if "s" in key_state or "Down" in key_state: dz -= 1
        if "d" in key_state or "Right" in key_state: dx += 1
        if "space" in key_state: dy += 1
        if "Control_L" in key_state or "Control_R" in key_state: dy -= 1
        if 27 in key_state:
            key_table = tuple(KeyboardHandler.dbg_keys.get(i, 'x') for i in range(max(keys) + 1))
            print(key_table)
        elif "Escape" in key_state:
            self.ctx.root.destroy()
            return

        L = hypot(dx, dy, dz)
        if L: dx /= L; dy /= L; dz /= L # нормализация вектора

        camera = self.ctx.camera
        if dz: camera.move_forward(dt * speed * dz)
        if dx: camera.move_right  (dt * speed * dx)
        if dy: camera.move_up     (dt * speed * dy)
        if L: self.ctx.render.redraw()



class MouseHandler:
    def __init__(self, context):
        self.ctx = context
        self.last_mouse_pos = None
        self.ray_cb = None

        self.press_time = 0
        self.press_mouse_pos = None
        self.threshold_time = 0.5 # секунды
        self.threshold_dist = 64  # пикселей
        self.moved = False

    def ray_handler(self, x, y):
        if self.ray_cb is None: return

        render = self.ctx.render
        dot = self.ctx.camera.unproject(x, y, render.viewport)
        # print(distance(dot, self.ctx.camera.pos))
        return self.ray_cb(self, dot)

    def on_press(self, event):
        self.ctx.focus_me()

        self.press_time = time()
        self.press_mouse_pos = event.x, event.y
        self.moved = False

        if self.ray_handler(event.x, event.y): return
        # print(f"Нажатие: x={}, y={event.y}")

        self.last_mouse_pos = event.x, event.y
        self.ctx.render.redraw()

    def on_move(self, event):
        pos = self.press_mouse_pos
        if pos is not None:
            dpos = hypot(pos[0] - event.x, pos[1] - event.y)
            if dpos > self.threshold_dist: self.moved = True

        if self.ray_handler(event.x, event.y): return
        # print(f"Движение: x={event.x}, y={event.y}")

        if self.last_mouse_pos is None:
            # self.last_mouse_pos = event.x, event.y
            return

        x0, y0 = self.last_mouse_pos
        dx = event.x - x0
        dy = event.y - y0
        self.last_mouse_pos = event.x, event.y

        if dx or dy:
            sensitivity = 0.4  # коэффициент чувствительности

            dYaw   = dx * sensitivity
            dPitch = dy * sensitivity

            self.ctx.camera.rotate(dYaw, dPitch, 0)
            self.ctx.render.redraw()

    def on_release(self, event):
        # print(f"Отпускание: x={event.x}, y={event.y}")
        pos = self.press_mouse_pos
        if pos is not None and not self.moved:
            dt = time() - self.press_time
            dpos = hypot(pos[0] - event.x, pos[1] - event.y)
            if dt <= self.threshold_time and dpos <= self.threshold_dist:
                # print("CLICK!")
                self.ctx.render.handle_click(event.x, event.y)

        self.last_mouse_pos = self.press_mouse_pos = None

    def on_zoom(self, event):
        self.ctx.focus_me()

        up = hasattr(event, "delta") and event.delta > 0 or event.num == 5
        # print("Scroll:", "up" if up else "down")
        self.ctx.camera.move_forward(0.25 * (1 if up else -1) * (1 if self.ctx.camera.orbital_mode else 2))
        self.ctx.render.redraw()

    def bind(self, n):
        self.button = n

        canvas = self.ctx.canvas
        canvas.bind(f"<ButtonPress-{n}>",   self.on_press) # всё равно перезаписывает <Button-{n}>
        canvas.bind(f"<B{n}-Motion>",       self.on_move)
        canvas.bind(f"<ButtonRelease-{n}>", self.on_release)

        # Windows/macOS
        canvas.bind("<MouseWheel>", self.on_zoom)
        # Linux-проблема
        canvas.bind("<Button-4>", self.on_zoom)
        canvas.bind("<Button-5>", self.on_zoom)

        return self



class Render:
    def __init__(self, context):
        self.ctx = context
        self.viewport = 0, 50, 640, 640

        self.last_time = time()
        self.frame_count = 0
        self.fps_text_id = None

        self.model   = ()
        self.markers = {}
        self.lines   = {}
        self.click_handlers = {}

        vp = self.viewport
        canvas = tk.Canvas(context.frame, width=vp[0]+vp[2], height=vp[1]+vp[3], bg="white")
        canvas.pack()
        self.canvas = canvas
        wrap_rounded_rectangle(canvas)

        self.draw_mode_indicator()

    def set_line(self, id, start, end, size, size_end, color, color_end):
        def maker():
            x,  y,  z  = start
            x2, y2, z2 = end
            dx, dy, dz = x2 - x, y2 - y, z2 - z
            count = round((hypot(dx, dy, dz) - size_end) / size)
            misc = (color, size, 0)
            for i in range(count):
                i /= count
                yield x + i*dx, y + i*dy, z + i*dz, misc
            yield x2, y2, z2, (color_end, size_end, 1)
        self.lines[id] = tuple(maker())

    def remove_line(self, id):
        try: del self.lines[id]
        except KeyError: return False
        return True

    def redraw(self):
        canvas = self.canvas
        camera = self.ctx.camera

        canvas.delete("circles")

        dots = camera.project_dots((self.model, self.markers, self.lines), self.viewport)
        # print((dots[0][2] * 0.5 + 0.5) * (camera.far - camera.near) + camera.near)
        # print(1 - (dots[-1][2] * 0.5 + 0.5))

        near, far, fovy_factor = camera.depth_states

        pixels_per_world_unit = self.viewport[3] / (2 * fovy_factor)

        for x, y, z, (color, size, T) in dots:
            depth = 0.5 - z * 0.5
            # 0.05 -> 3.2
            # 0.1  -> 1.6
            radius = pixels_per_world_unit * (size * 6.25) * depth

            if T == 0:
                canvas.create_oval(
                    x - radius, y - radius,
                    x + radius, y + radius,
                    fill=color, outline="", tags="circles"
                )
            elif T == 1:
                R1 = radius // 3
                R2 = R1 * 2
                canvas.create_oval(
                    x - R2, y - R2,
                    x + R2, y + R2,
                    outline=color, width = R1, tags="circles"
                )
            else:
                assert type(T) is str
                font_size = max(int(radius), 1)
                canvas.create_text(
                    x, y,
                    text=T, font=("Arial", font_size),
                    fill=color, tags="circles",
                    anchor="w"
                )

        self.frame_count += 1

        canvas.tag_raise("fps")
        canvas.tag_raise("indicator")

    def update_fps(self):
        canvas = self.ctx.canvas

        if self.fps_text_id is None:
            vp = self.viewport
            fps_pos = (10, vp[1]+vp[3] - 10), "sw"
            fps_pos = (10, 10),               "nw"
            self.fps_text_id = canvas.create_text(*fps_pos[0], anchor=fps_pos[1], text="FPS: 0", font=("Arial", 12), fill="black", tags="fps")

        T = time()
        elapsed = T - self.last_time
        if elapsed >= 0.1:
            fps = self.frame_count / elapsed
            canvas.itemconfig(self.ctx.render.fps_text_id, text=f"FPS: {int(fps)}")
            self.last_time = T
            self.frame_count = 0
        canvas.after(10, self.update_fps)

        self.ctx.keyboard_handler.update_move()

    def set_size(self, width, height):
        self.canvas.config(width = width, height = height)
        camera = self.ctx.camera
        camera.aspect = width / height
        camera.update_proj()

        self.viewport = self.viewport[0], self.viewport[1], width, height

        self.redraw()
        self.draw_mode_indicator()

    def draw_mode_indicator(self):
        canvas = self.canvas
        canvas.delete("indicator")

        dx, dy, width, height = self.viewport

        # Размеры и позиционирование
        box_width = 100
        box_height = 30
        marginX = 10
        marginY = (dy - box_height) // 2
        x0, x1 = width - box_width - marginX, width - marginX
        y0, y1 = marginY, marginY + box_height
        mid_x = (x0 + x1) // 2

        # Цвета
        bg_color     = "#2c2c2c"
        border_color = "#555"
        text_color   = "#888"

        # Рисуем фон
        canvas.create_rectangle(x0, y0, x1, y1, radius=11, fill=bg_color, outline=border_color, width=1, tags="indicator")
        self.click_handlers["orbital_mode"] = range(x0, x1+1), range(y0, y1+1), self.change_orbital_mode

        # Вертикальная линия
        canvas.create_rectangle(mid_x-1, y0, mid_x+1, y1, fill=border_color, tags="indicator")

        # Подсветка активного режима
        mode = self.ctx.camera.orbital_mode
        if mode:
            canvas.create_rectangle(mid_x+4, y0+3, x1-3, y1-2, radius=10, fill="#00afff", outline="#0070ff", width=2, tags="indicator")
        else:
            canvas.create_rectangle(x0+3, y0+3, mid_x-3, y1-2, radius=10, fill="#00afff", outline="#0070ff", width=2, tags="indicator")

        # Текст
        canvas.create_text((x0 + mid_x) // 2, y0 + box_height // 2 - 1, text="fps", fill=text_color if mode else "#c6e7ff", font=("Segoe UI", 12, "bold"), tags="indicator")
        canvas.create_text((mid_x + x1) // 2, y0 + box_height // 2 - 1, text="orb", fill="#c6e7ff" if mode else text_color, font=("Segoe UI", 12, "bold"), tags="indicator")

    def change_orbital_mode(self):
        camera = self.ctx.camera
        camera.orbital_mode = not camera.orbital_mode
        camera.R = hypot(*camera.pos)
        camera.update_proj_view()
        self.redraw()
        self.draw_mode_indicator()

    def handle_click(self, x, y):
        for x_range, y_range, cb in self.click_handlers.values():
            if x in x_range and y in y_range: cb()



class Context_3d:
    contexts = []
    def __init__(self, root, **kwargs):
        Context_3d.contexts.append(self)

        self.root = root

        frame = tk.Frame(root, padx=4, pady=4, bg="white")
        frame.grid(**kwargs)
        self.frame = frame

        self.camera = Camera()
        self.render = render = Render(self)
        self.canvas = render.canvas

        self.keyboard_handler = KeyboardHandler(self)
        self.mouse_handlers = (
            None,
            MouseHandler(self).bind(1), # ЛКМ
            MouseHandler(self).bind(2), # СКМ
            MouseHandler(self).bind(3), # ПКМ
        )

        render.redraw()
        render.update_fps()

    def focus_me(self):
        if self.is_focused: return

        for context in Context_3d.contexts:
            context.canvas.config(highlightbackground = ("SystemButtonFace", "dodgerblue")[context == self])
        self.keyboard_handler.bind()

    @property
    def is_focused(self):
        self.canvas["highlightbackground"] == "dodgerblue"

    @staticmethod
    def focused():
        for context in Context_3d.contexts:
            if context.is_focused: return context

    @property
    def width(self):
        return (self.frame["padx"] + int(self.canvas["highlightthickness"])) * 2 + int(self.canvas["width"])

    @property
    def height(self):
        return (self.frame["pady"] + int(self.canvas["highlightthickness"])) * 2 + int(self.canvas["height"])

    def set_canvas_size(self, width, height):
        thickness = int(self.canvas["highlightthickness"])
        width  -= (self.frame["padx"] + thickness) * 2
        height -= (self.frame["pady"] + thickness) * 2
        self.render.set_size(width, height)

    def set_ray_cb(self, buttons, ray_cb):
        if type(buttons) is int: buttons = (buttons,)
        for button in buttons:
            self.mouse_handlers[button].ray_cb = ray_cb



class Context_QGA: # QuantumGridAnalyzer
    def __init__(self, root, **kwargs):
        self.root = root
        self.grid_size = None
        self.width = self.height = 320

        self.selected_option = tk.StringVar(value="?")
        self.qubit = None

        frame = tk.Frame(root, padx=4, pady=4)
        frame.grid(**kwargs)
        self.frame = frame

        self.make_control_frame(frame)

        canvas = tk.Canvas(frame, bg="white", width=self.width, height=self.height)
        canvas.grid(row=1, column=0, columnspan=3)
        self.canvas = canvas

        self.update_grid_size(16)
        self.redraw()
        self.bind_all_mouse_buttons()

    def make_control_frame(self, frame):
        label = tk.Label(frame, text="Размер сетки:")
        label.grid(row=0, column=0, sticky="e")

        control_frame = tk.Frame(frame)
        control_frame.grid(row=0, column=1, sticky="w")
        self.control_frame = control_frame

        tk.Button(control_frame, text="◀◀", width=2, command=lambda: self.update_grid_size(-10)).pack(side="left")
        tk.Button(control_frame, text="◀",  width=2, command=lambda: self.update_grid_size(-1)).pack(side="left")

        size_label = tk.Label(control_frame, text="?×?", width=6)
        size_label.pack(side="left")
        self.size_label = size_label

        tk.Button(control_frame, text="▶",  width=2, command=lambda: self.update_grid_size(1)).pack(side="left")
        tk.Button(control_frame, text="▶▶", width=2, command=lambda: self.update_grid_size(10)).pack(side="left")

        option_menu = tk.OptionMenu(frame, self.selected_option, "?")
        option_menu.grid(row=0, column=2, sticky="e")
        self.option_menu = option_menu

    def set_size(self, width, height):
        if height > width: height = width
        self.canvas.config(width = width, height = height)
        self.width = width
        self.height = height
        self.redraw()

    def set_canvas_size(self, width, height):
        def set_canvas_size():
            nonlocal width, height
            thickness = int(self.canvas["highlightthickness"])
            width  -= (self.frame["padx"] + thickness) * 2
            height -= (self.frame["pady"] + thickness) * 2 + max(self.control_frame.winfo_height(), self.option_menu.winfo_height())
            self.set_size(width, height)

        #self.frame.update_idletasks()
        #self.control_frame.update_idletasks()
        #self.option_menu.update_idletasks()
        self.root.after_idle(set_canvas_size)

    def update_grid_size(self, value):
        old = self.grid_size
        if old is None: new = value
        else: new = old + value
        new = max(1, min(new, 64))

        self.grid_size = new
        self.size_label.config(text = f"{new}×{new}")
        self.redraw()

    def redraw(self, window_size_changed = True):
        canvas = self.canvas
        redraw_lines = window_size_changed

        if redraw_lines: canvas.delete("grid")
        canvas.delete("quantum")
        canvas.delete("bars")
        canvas.delete("verdict")

        bar_width = 40
        spacing = 20
        bottom_margin = 40

        # Размеры холста
        canvas_width = self.width
        canvas_height = self.height

        # Вычисляем доступную область под сетку
        grid_area_width = canvas_width - spacing - bar_width * 2 - spacing
        grid_area_height = canvas_height - bottom_margin

        # Размер ячейки
        grid_size = self.grid_size
        cell_size = min(grid_area_width // grid_size, grid_area_height // grid_size)

        # Фактические размеры сетки
        grid_width = cell_size * grid_size
        grid_height = cell_size * grid_size

        # Смещение сетки от левого верхнего угла
        grid_offset_x = 0
        grid_offset_y = 0

        passed_count = 0
        total = grid_size * grid_size

        if redraw_lines:
            # Рисуем сетку через линии
            for i in range(grid_size + 1):
                x = grid_offset_x + i * cell_size
                canvas.create_line(x, grid_offset_y, x, grid_offset_y + grid_height, fill="gray", tags="grid")

            for j in range(grid_size + 1):
                y = grid_offset_y + j * cell_size
                canvas.create_line(grid_offset_x, y, grid_offset_x + grid_width, y, fill="gray", tags="grid")

        qubit = self.qubit
        if qubit:
            # Рисуем клетки
            samples = qubit.measure(total)
            margin = int(cell_size > 5)
            for y in range(grid_size):
                for x in range(grid_size):
                    x0 = grid_offset_x + x * cell_size
                    y0 = grid_offset_y + y * cell_size
                    x1 = x0 + cell_size
                    y1 = y0 + cell_size

                    if samples[x + grid_size * y]:
                        passed_count += 1
                        canvas.create_rectangle(x0 + 1 + margin, y0 + 1 + margin, x1 - margin, y1 - margin,
                                                fill="green", outline="", tags="quantum")

        # Бары
        failed_count = total - passed_count
        bar_x0 = grid_offset_x + grid_width + spacing
        bar_x1 = bar_x0 + bar_width
        bar2_x0 = bar_x1 + spacing
        bar2_x1 = bar2_x0 + bar_width

        failed_height = min(grid_height-2, int(grid_height * failed_count / total))
        passed_height = min(grid_height-2, int(grid_height * passed_count / total))

        canvas.create_rectangle(bar_x0, grid_height - failed_height, bar_x1, grid_height,
                                fill="white", outline="black", tags="bars")
        canvas.create_text((bar_x0 + bar_x1) // 2, max(grid_height - failed_height - 10, 10),
                           text=f"{round(failed_count * 100 / total)}%", fill="black", font=("Arial", 10), tags="bars")

        canvas.create_rectangle(bar2_x0, grid_height - passed_height, bar2_x1, grid_height,
                                fill="green", outline="black", tags="bars")
        canvas.create_text((bar2_x0 + bar2_x1) // 2, max(grid_height - passed_height - 10, 10),
                           text=f"{round(passed_count * 100 / total)}%", fill="black", font=("Arial", 10), tags="bars")

        # Вердикт
        verdict = ("⚠️ Отсутсвует квантовый поток ⚠️" if self.qubit is None
                   else "Преобладает успех" if passed_count > failed_count
                   else "Преобладает отказ")
        canvas.create_text(20, canvas_height - 20, text=verdict, anchor="w", font=("Arial", 12, "bold"), tags="verdict")

    def set_qubits(self, options, default):
        menu = self.option_menu["menu"]
        menu.delete(0, "end") # Удалить старые пункты

        selected_option = self.selected_option

        def setter(value):
            selected_option.set(value)
            self.qubit = options[value]
            self.redraw(False)

        for option in options:
            menu.add_command(label=option, command=lambda value=option: setter(value))

        if selected_option.get() == "?": selected_option.set(default)
        self.qubit = options[selected_option.get()]
        self.redraw(False)

    def bind_all_mouse_buttons(self):
        for i in range(1, 6):
            self.canvas.bind(f"<Button-{i}>", lambda event: self.redraw(False))
            self.canvas.bind(f"<B{i}-Motion>", lambda event: self.redraw(False))



def default_model():
    dots = []
    append = dots.append

    red   = ("pink", 0.05, 0), ("red",   0.05, 0)
    green = ("lime", 0.05, 0), ("green", 0.05, 0)
    blue  = ("aqua", 0.05, 0), ("blue",  0.05, 0)

    circle_count = 128
    part = 2 * pi / circle_count
    for i in range(circle_count):
        angle = i * part
        ci = cos(angle)
        si = sin(angle)
        append((0, ci, si, red  [i % 2]))
        append((ci, 0, si, green[i % 2]))
        append((ci, si, 0, blue [i % 2]))
    # print(distance(dots[0], dots[1])) # 0.049 шпилек между вершинами

    # for i in range(41):
    #     ii = i / 20 - 1
    #     append((ii, -1.2, 0, ("aqua", "blue")[i % 2]))
    #     if ii: append((0, -1.2, ii, ("lime", "green")[i % 2]))

    for i in range(1, 11):
        ii = i / 20
        append((ii, 0, 0, red  [i % 2]))
        append((0, ii, 0, green[i % 2]))
        append((0, 0, ii, blue [i % 2]))

    return dots



if __name__ == "__main__":
    import main
    main.main()
