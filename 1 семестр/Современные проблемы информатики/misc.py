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

if __name__ == "__main__":
    arr = "cat", "meow", "woof", "dog"
    for i in range(5):
        print(tuple(edge_enumerate(arr[:i])))
    # i=0: -
    # i=1: 3
    # i=2: 0, 2
    # i=3: 0, 1, 2
    # i=4: 0, 1, 1, 2
