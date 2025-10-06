import tkinter as tk

from graphics import default_model, Context
from geometry import distance, intersect_unit_sphere
from qubit import Qubit
from matrix import NOT, H



def ray_handler(mouse_handler, dot):
    camera = mouse_handler.ctx.camera
    render = mouse_handler.ctx.render

    intersections = intersect_unit_sphere(*camera.pos, *dot)
    # интересное наблюдение: intersections[0] всегда выдаёт точку, что ближе всего к камере, а intersections[1] наоборот

    misc = ("magenta", 0.05, 1)

    render.markers[0] = ((*dot, misc),)
    # render.markers[1] = tuple((*dot, misc) for dot in intersections)

    if intersections:
        near_dot = intersections[0]
        qubit = Qubit.from_Bloch(*near_dot)
        qubit2 = NOT * qubit
        qubit3 = H * qubit

        render.set_line(0, (0, 0, 0), qubit.to_Bloch(), 0.025, 0.07, "PowderBlue", "MediumPurple")
        render.set_line(1, (0, 0, 0), qubit2.to_Bloch(), 0.025, 0.07, "PowderBlue", "MediumPurple")
        render.set_line(2, (0, 0, 0), qubit3.to_Bloch(), 0.025, 0.07, "PowderBlue", "MediumPurple")

    render.redraw()
    return True # отменяется дефолтное вращение камеры



def main():
    global contexts

    prev_width = prev_height = None
    def on_resize(event):
        nonlocal prev_width, prev_height
        if event.widget == root and (event.width != prev_width or event.height != prev_height):
            prev_width  = W = event.width
            prev_height = H = event.height
            # print(f"Новый размер: {W} x {H}")
            contexts[0].set_canvas_size(W // 2, H)
            contexts[1].set_canvas_size(W - W // 2, H)

    root = tk.Tk()
    root.title("OpenGL-like 2D rendering")

    model = default_model()

    def context_maker():
        context = Context(root)
        context.set_ray_cb(1, ray_handler)

        render = context.render
        render.model = model
        # render.set_line(0, (0, 0, 0), (0.707, 0.707, 0), 0.025, 0.07, "PowderBlue", "MediumPurple")
        # print("REMOVE:", render.remove_line(0))

        return context

    contexts = (
        context_maker(),
        context_maker()
    )

    # root.after(100, lambda: print(root.winfo_width(), root.winfo_height()))
    # print(contexts[0].width + contexts[1].width, contexts[0].height)

    root.bind("<Configure>", on_resize)
    root.mainloop()



if __name__ == "__main__":
    main()
