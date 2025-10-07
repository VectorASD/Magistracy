EPS = 0.0001

def float_eq(a, b):
    return abs(a - b) < EPS

def edge_enumerate(it):
    it = iter(it)
    try: a = next(it)
    except StopIteration: return
    try: b = next(it)
    except StopIteration: yield 3, a; return

    yield 0, a

    while True:
        try: a = next(it)
        except StopIteration: yield 2, b; return
        yield 1, b

        try: b = next(it)
        except StopIteration: yield 2, a; return
        yield 1, a



def wrap_rounded_rectangle(canvas):
    from tkinter import PIESLICE, ARC
    def new_create_rectangle(x1, y1, x2, y2, radius=None, fill=None, outline=None, width=1, **kwargs):
        if radius is None:
            old_create_rectangle(x1, y1, x2, y2, radius=radius, fill=fill, outline=outline, width=width, **kwargs)
            return

        _2R = 2 * radius

        # Заливка — через PIESLICE + центральные прямоугольники
        if fill:
            canvas.create_rectangle(x1 + radius, y1, x2 - radius, y2, fill=fill, outline="", width=0, **kwargs)
            canvas.create_rectangle(x1, y1 + radius, x2, y2 - radius, fill=fill, outline="", width=0, **kwargs)
            canvas.create_arc(x2 - _2R, y1, x2, y1 + _2R, start=-3,  extent=93,  style=PIESLICE, fill=fill, outline="", width=0, **kwargs)
            canvas.create_arc(x1, y1, x1 + _2R, y1 + _2R, start=87,  extent=100, style=PIESLICE, fill=fill, outline="", width=0, **kwargs)
            canvas.create_arc(x1, y2 - _2R, x1 + _2R, y2, start=180, extent=100, style=PIESLICE, fill=fill, outline="", width=0, **kwargs)
            canvas.create_arc(x2 - _2R, y2 - _2R, x2, y2, start=270, extent=90,  style=PIESLICE, fill=fill, outline="", width=0, **kwargs)

        # Обводка — через линии и дуги
        if outline:
            # Горизонтальные линии
            canvas.create_line(x1 + radius, y1, x2 - radius, y1, fill=outline, width=width, **kwargs)
            canvas.create_line(x1 + radius, y2, x2 - radius, y2, fill=outline, width=width, **kwargs)
            # Вертикальные линии
            canvas.create_line(x1, y1 + radius, x1, y2 - radius, fill=outline, width=width, **kwargs)
            canvas.create_line(x2, y1 + radius, x2, y2 - radius, fill=outline, width=width, **kwargs)
            # Угловые дуги
            canvas.create_arc(x2 - _2R, y1, x2, y1 + _2R, start=-3,  extent=93,  style=ARC, outline=outline, width=width, **kwargs)
            canvas.create_arc(x1, y1, x1 + _2R, y1 + _2R, start=87,  extent=100, style=ARC, outline=outline, width=width, **kwargs)
            canvas.create_arc(x1, y2 - _2R, x1 + _2R, y2, start=180, extent=100, style=ARC, outline=outline, width=width, **kwargs)
            canvas.create_arc(x2 - _2R, y2 - _2R, x2, y2, start=270, extent=90,  style=ARC, outline=outline, width=width, **kwargs)

    old_create_rectangle = canvas.create_rectangle
    canvas.create_rectangle = new_create_rectangle



if __name__ == "__main__":
    arr = "cat", "meow", "woof", "dog"
    for i in range(5):
        print(tuple(edge_enumerate(arr[:i])))
    # i=0: -
    # i=1: 3
    # i=2: 0, 2
    # i=3: 0, 1, 2
    # i=4: 0, 1, 1, 2
