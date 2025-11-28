import inspect
from io import StringIO

from utils import print_table



def int_to_bits(n, width):
    """Преобразует число n в кортеж битов длины width (старший бит слева)."""
    return tuple(n >> shift & 1 for shift in range(width -1, -1, -1))

# print(tuple(map(ord, "₀₁₂₃₄₅₆₇₈₉"))) # (8320, 8321, 8322, 8323, 8324, 8325, 8326, 8327, 8328, 8329)
def int_to_sub(n):
    """Преобразует число n в строку с пониженным регистром"""
    return "".join(chr(int(char) + 8320) if char.isdigit() else char for char in str(n))
# print(int_to_sub("x12")) # x₁₂



class BooleanFunction:
    """Булева функция от n переменных, заданная таблицей истинности или лямбда-выражением."""

    def __init__(self, n, source, inputs=None, outputs=("y",)):
        self.n = n
        self.inputs  = inputs or n
        self.outputs = outputs
        if len(outputs) == 1:
            self.truth_table = (self.read_truth_table(n, source),)
        else:
            self.truth_table = tuple(self.read_truth_table(n, column) for column in source)

    @staticmethod
    def read_truth_table(n, source):
        if type(source) in (tuple, list):
            if len(source) != 2 ** n:
                raise ValueError("Длина таблицы истинности должна быть 2^n")
            return tuple(int(bool(v)) for v in source)

        if callable(source):
            func = source
            sig = inspect.signature(func)
            if len(sig.parameters) != n:
                raise ValueError(f"Функция должна принимать {n} аргументов")
            return tuple(
                int(bool(func(*int_to_bits(i, n))))
                for i in range(2 ** n)
            )

        raise TypeError("Ожидался список/кортеж или функция")

    def __repr__(self):
        n     = self.n
        _in   = self.inputs
        out   = self.outputs
        truth = iter(zip(*self.truth_table))
        table = (
            (*(int_to_sub(f"x{i}") for i in range(_in, 0, -1)), *map(int_to_sub, out)),
            *(
                (*int_to_bits(i, n)[:_in], *next(truth)) for i in range(2 ** n)
            ),
        )

        io = StringIO()
        print_table(table, io, middle_sep = False)
        return io.getvalue()



# f = BooleanFunction(2, (1, 1, 0, 1)); print(f)
"""
+----+----+---+
| x₂ | x₁ | y |
+----+----+---+
|  0 |  0 | 1 |
|  0 |  1 | 1 |
|  1 |  0 | 0 |
|  1 |  1 | 1 |
+----+----+---+
"""

# f = BooleanFunction(2, lambda a, b: a <= b); print(f)
"""
+----+----+---+
| x₂ | x₁ | y |
+----+----+---+
|  0 |  0 | 1 |
|  0 |  1 | 1 |
|  1 |  0 | 0 |
|  1 |  1 | 1 |
+----+----+---+
"""

# f = BooleanFunction(3, lambda a, b, c: a == b, None, ("name",)); print(f)
"""
+----+----+----+------+
| x₃ | x₂ | x₁ | name |
+----+----+----+------+
|  0 |  0 |  0 |    1 |
|  0 |  0 |  1 |    1 |
|  0 |  1 |  0 |    0 |
|  0 |  1 |  1 |    0 |
|  1 |  0 |  0 |    0 |
|  1 |  0 |  1 |    0 |
|  1 |  1 |  0 |    1 |
|  1 |  1 |  1 |    1 |
+----+----+----+------+
"""

# f = BooleanFunction(3, (lambda a, b, c: a == b, lambda a, b, c: a != b), 2, ("y1", "y2")); print(f)
"""
+----+----+----+----+
| x₂ | x₁ | y₁ | y₂ |
+----+----+----+----+
|  0 |  0 |  1 |  0 |
|  0 |  0 |  1 |  0 |
|  0 |  1 |  0 |  1 |
|  0 |  1 |  0 |  1 |
|  1 |  0 |  0 |  1 |
|  1 |  0 |  0 |  1 |
|  1 |  1 |  1 |  0 |
|  1 |  1 |  1 |  0 |
+----+----+----+----+
"""
