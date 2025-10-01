import tkinter as tk
from math import pi, sin, cos, hypot, tan
import time
from lab1 import Matrix

pi_180 = pi / 180



class Camera:
    def __init__(self):
        # self.x, self.y, self.z = self.pos = 0, 0, 5
        self.pos = 0, 0, 3
        self.YPR = 0, 0, 0
        self.update_proj()

    def update_proj(self, fovy = 90, aspect = 1, near = 0.1, far = 100):
        self.near        = near
        self.far         = far
        self.fovy_factor = ff = tan(fovy * pi_180 / 2)
        self.depth_states = near, far, ff

        self.proj = Matrix.perspective(fovy, aspect, near, far)
        self.update_proj_view()

    def update_proj_view(self):
        self.view, self.forward, self.right, self.up = Matrix.view(*self.pos, *self.YPR)
        self.proj_view = self.proj @ self.view

    def project_dots(self, dots, winX, winY):
        project = self.proj_view.project
        return tuple(project(*dot, winX, winY) for dot in dots)

    def move_to(self, x, y, z):
        self.pos = x, y, z
        self.update_proj_view()
    def move(self, dx, dy, dz):
        x, y, z = self.pos
        self.pos = x + dx, y + dy, z + dz
        self.update_proj_view()
    def rotate(self, dY, dP, dR):
        Y, P, R = self.YPR
        self.YPR = Y + dY, P + dP, R + dR
        self.update_proj_view()

    def move_forward(self, dt):
        x, y, z = self.pos
        dx, dy, dz = self.forward
        self.pos = x + dx * dt, y + dy * dt, z + dz * dt
        self.update_proj_view()

    def move_right(self, dt):
        x, y, z = self.pos
        dx, dy, dz = self.right
        self.pos = x + dx * dt, y + dy * dt, z + dz * dt
        self.update_proj_view()

    def move_up(self, dt):
        x, y, z = self.pos
        dx, dy, dz = self.up
        self.pos = x + dx * dt, y + dy * dt, z + dz * dt
        self.update_proj_view()



camera = Camera()
# print(camera.proj_view)
# camera.move(0, 0, 2)
# camera.rotate(0, 0, 45)
# print(camera.proj_view)



canvas_size = 640
center = canvas_size // 2
model = None

def init_model():
    global model

    circle_count = 128

    dots = []
    R = 1
    part = 2 * pi / circle_count
    for i in range(circle_count):
        angle = i * part
        dots.append((cos(angle) * R, sin(angle) * R, 0))
    for i in range(41):
        i = i / 20 - 1
        dots.append((i, -1, 0))
        if i: dots.append((0, -1, i))
    model = dots

circle_pos = center, center

def redraw():
    global frame_count

    canvas.delete("circles")

    circle_radius = 20
    central_radius = 30
    border_width = central_radius // 2

    dots = camera.project_dots(model, canvas_size, canvas_size)
    # print((dots[0][2] * 0.5 + 0.5) * (camera.far - camera.near) + camera.near)
    # print(1 - (dots[-1][2] * 0.5 + 0.5))

    near, far, fovy_factor = camera.depth_states
    object_size = 100

    for x, y, z in dots:
        if z > 1: continue

        depth = z * 0.5 + 0.5
        # screen_scale = (near + depth * (far - near))
        # circle_radius = object_size * screen_scale * fovy_factor
        # pixels_per_world_unit = canvas_size / (2 * fovy_factor)
        # circle_radius = object_size * pixels_per_world_unit / screen_scale
        circle_radius = object_size * (1 - depth)

        canvas.create_oval(
            x - circle_radius, y - circle_radius,
            x + circle_radius, y + circle_radius,
            fill="red", outline="", tags="circles"
        )

    cx, cy = circle_pos
    canvas.create_oval(
        cx - central_radius, cy - central_radius,
        cx + central_radius, cy + central_radius,
        outline="blue", width=border_width, tags="circles"
    )
    frame_count += 1



fps_last_time = time.time()
frame_count = 0
fps_position = (10, canvas_size - 10)

def update_fps():
    global fps_last_time, frame_count
    T = time.time()
    elapsed = T - fps_last_time
    if elapsed >= 0.1:
        fps = frame_count / elapsed
        canvas.itemconfig(fps_text_id, text=f"FPS: {int(fps)}")
        fps_last_time = T
        frame_count = 0
    canvas.after(10, update_fps)

    update_move()



last_mouse_pos = None

def on_press(event):
    global last_mouse_pos
    last_mouse_pos = event.x, event.y
    # print(f"Нажатие: x={}, y={event.y}")
def on_move(event):
    # print(f"Движение: x={event.x}, y={event.y}")
    global circle_pos
    circle_pos = event.x, event.y

    global last_mouse_pos
    if last_mouse_pos is None:
        last_mouse_pos = (event.x, event.y)
        return

    x0, y0 = last_mouse_pos
    dx = event.x - x0
    dy = event.y - y0
    last_mouse_pos = (event.x, event.y)

    sensitivity = 0.4  # коэффициент чувствительности

    dYaw = dx * sensitivity
    dPitch  = dy * sensitivity

    camera.rotate(dYaw, dPitch, 0)

    redraw()
def on_release(event):
    global last_mouse_pos
    last_mouse_pos = None
    # print(f"Отпускание: x={event.x}, y={event.y}")



key_state = set()
dbg_keys = {}
key_table = ('x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'BackSpace', 'Tab', 'x', 'x', 'Clear', 'Return', 'x', 'x', 'Shift_L', 'Control_R', 'Alt_R', 'x', 'Caps_Lock', 'x', 'x', 'x', 'x', 'x', 'x', 'Escape', 'x', 'x', 'x', 'x', 'space', 'Prior', 'Next', 'End', 'Home', 'Left', 'Up', 'Right', 'Down', 'x', 'x', 'x', 'x', 'Insert', 'Delete', 'x', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', 'Win_L', 'x', 'x', 'x', 'x', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'asterisk', 'plus', 'x', 'minus', 'period', 'slash', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'Num_Lock', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'semicolon', 'equal', 'comma', 'minus', 'period', 'slash', 'grave', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'bracketleft', 'backslash', 'bracketright', 'apostrophe')
def on_key_press(event):
    # dbg_keys[event.keycode] = event.keysym
    key = key_table[event.keycode] if event.keycode in range(len(key_table)) else 'x'
    key_state.add(key)
    # print(f"[↓] {key} нажата")
def on_key_release(event):
    key = key_table[event.keycode] if event.keycode in range(len(key_table)) else 'x'
    key_state.discard(key)
    # print(f"[↑] {key} отпущена")



last_time = time.time()
def update_move():
    global last_time
    T = time.time()
    dt = T - last_time
    last_time = T

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
        key_table = tuple(dbg_keys.get(i, 'x') for i in range(max(keys) + 1))
        print(key_table)

    L = hypot(dx, dy, dz)
    if L: dx /= L; dy /= L; dz /= L # нормализация вектора

    if dz: camera.move_forward(dt * speed * dz)
    if dx: camera.move_right  (dt * speed * dx)
    if dy: camera.move_up     (dt * speed * dy)
    if L: redraw()



if __name__ == "__main__":
    root = tk.Tk()
    root.title("Окружность из кругов")
    canvas = tk.Canvas(root, width=canvas_size, height=canvas_size, bg="white")
    canvas.pack()

    fps_text_id = canvas.create_text(*fps_position, anchor="sw", text="FPS: 0", font=("Arial", 12), fill="black")

    init_model()
    redraw()
    update_fps()

    canvas.bind("<ButtonPress-1>", on_press) # всё равно перезаписывает <Button-1>
    canvas.bind("<B1-Motion>", on_move)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.bind("<KeyPress>", on_key_press)
    root.bind("<KeyRelease>", on_key_release)

    root.mainloop()
