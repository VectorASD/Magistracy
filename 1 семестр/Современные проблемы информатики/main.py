import tkinter as tk

from graphics import default_model, Context_3d, Context_QGA
from geometry import intersect_unit_sphere, snap_sphere_point
from qubit import Qubit
from matrix import NOT, H



EDGES = (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)

def main():
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
            near_dot = snap_sphere_point(*near_dot, 16)

            qubitR = Qubit.from_Bloch(*near_dot)
            qubit2 = NOT * qubitR
            qubit3 = H   * qubitR
            qubits = {"ray": qubitR, "NOT": qubit2, "H": qubit3}

            qubitR.rounding = qubit2.rounding = qubit3.rounding = 3

            render.set_line(0, (0, 0, 0), qubitR.to_Bloch(), 0.025, 0.1, "PowderBlue", "MediumPurple")
            render.set_line(1, (0, 0, 0), qubit2.to_Bloch(), 0.025, 0.1, "PowderBlue", "MediumPurple")
            render.set_line(2, (0, 0, 0), qubit3.to_Bloch(), 0.025, 0.1, "PowderBlue", "MediumPurple")

            render.markers["qubits"] = (
                (*qubitR.to_Bloch(), ("DeepPink3", 0.1, "\n\n   ray: " + str(qubitR)[3:])),
                (*qubit2.to_Bloch(), ("DeepPink3", 0.1, "\n\n   NOT: " + str(qubit2)[3:])),
                (*qubit3.to_Bloch(), ("DeepPink3", 0.1, "\n\n   H: " + str(qubit3)[3:])),
            )
            QGA_1.set_qubits(qubits, "ray")
            QGA_2.set_qubits(qubits, "NOT")

        render.redraw()
        return True # отменяется дефолтное вращение камеры



    prev_width = prev_height = None
    def on_resize(event):
        nonlocal prev_width, prev_height
        if event.widget == root and (event.width != prev_width or event.height != prev_height):
            prev_width  = W = event.width
            prev_height = H = event.height
            # print(f"Новый размер: {W} x {H}")
            row0 = W * 3 // 8
            row2 = W // 4
            row1 = W - row0 - row2
            graph1_3d.set_canvas_size(row0, H)
            graph2_3d.set_canvas_size(row1, H)
            QGA_1.set_canvas_size(row2, H // 2)
            QGA_2.set_canvas_size(row2, H - H // 2)



    root = tk.Tk()
    root.title("OpenGL-like 2D rendering")

    model = default_model()

    def context_maker(row, column):
        context = Context_3d(root, row=row, column=column, rowspan=2)
        context.set_ray_cb(1, ray_handler)

        render = context.render
        render.model = model
        # render.set_line(0, (0, 0, 0), (0.707, 0.707, 0), 0.025, 0.07, "PowderBlue", "MediumPurple")
        # print("REMOVE:", render.remove_line(0))

        y_shift = lambda text, y: text + "\n\n" if y == 1 else text if y == 0 else "\n\n" + text
        render.markers["edges"] = tuple(
            (x, y, z, ("Purple", 0.1, y_shift(str(Qubit.from_Bloch(x, y, z))[3:], y)))
            for x, y, z in EDGES
        )
        return context

    graph1_3d = context_maker(0, 0)
    graph2_3d = context_maker(0, 1)
    QGA_1 = Context_QGA(root, row=0, column=2)
    QGA_2 = Context_QGA(root, row=1, column=2)

    # root.after(100, lambda: print(root.winfo_width(), root.winfo_height()))
    # print(graph1_3d.width + graph2_3d.width, graph1_3d.height)

    root.bind("<Configure>", on_resize)
    root.mainloop()



if __name__ == "__main__":
    main()
