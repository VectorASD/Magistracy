import tkinter as tk
import math
import time



# Параметры
canvas_size = 512
center = canvas_size // 2
circle_count = 128
circle_radius = 20
central_radius = 30
border_width = central_radius // 2

def redraw(cx, cy):
    global frame_count

    canvas.delete("circles")

    for i in range(circle_count):
        angle = 2 * math.pi * i / circle_count
        x = center + math.cos(angle) * (center - circle_radius - border_width)
        y = center + math.sin(angle) * (center - circle_radius - border_width)
        canvas.create_oval(
            x - circle_radius, y - circle_radius,
            x + circle_radius, y + circle_radius,
            fill="red", outline="", tags="circles"
        )

    canvas.create_oval(
        cx - central_radius, cy - central_radius,
        cx + central_radius, cy + central_radius,
        outline="blue", width=border_width, tags="circles"
    )
    frame_count += 1

def update_fps():
    global last_time, frame_count
    current_time = time.time()
    elapsed = current_time - last_time
    if elapsed >= 0.1:
        fps = frame_count / elapsed
        canvas.itemconfig(fps_text_id, text=f"FPS: {int(fps)}")
        last_time = current_time
        frame_count = 0
    canvas.after(10, update_fps)



# def on_canvas_click(event):
#     print(f"Клик по координатам: x={event.x}, y={event.y}")
#     redraw(event.x, event.y)
def on_press(event):
    print(f"Нажатие: x={event.x}, y={event.y}")
def on_move(event):
    # print(f"Движение: x={event.x}, y={event.y}")
    redraw(event.x, event.y)
def on_release(event):
    print(f"Отпускание: x={event.x}, y={event.y}")



root = tk.Tk()
root.title("Окружность из кругов")
canvas = tk.Canvas(root, width=canvas_size, height=canvas_size, bg="white")
canvas.pack()

last_time = time.time()
frame_count = 0
fps_position = (10, canvas_size - 10)
fps_text_id = canvas.create_text(*fps_position, anchor="sw", text="FPS: 0", font=("Arial", 12), fill="black")

redraw(center, center)
update_fps()

# canvas.bind("<Button-1>", on_canvas_click)
canvas.bind("<ButtonPress-1>", on_press) # всё равно перезаписывает <Button-1>
canvas.bind("<B1-Motion>", on_move)
canvas.bind("<ButtonRelease-1>", on_release)

root.mainloop()
