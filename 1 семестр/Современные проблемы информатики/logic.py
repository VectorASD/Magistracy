import inspect
from io import StringIO

from utils import print_table
from matrix import Matrix



def int_to_bits(n, width, skip = 0):
    """Преобразует число n в кортеж битов длины width (старший бит слева) с пропуском концовки skip."""
    return tuple(n >> shift & 1 for shift in range(width -1, skip-1, -1))

# print(tuple(map(ord, "₀₁₂₃₄₅₆₇₈₉"))) # (8320, 8321, 8322, 8323, 8324, 8325, 8326, 8327, 8328, 8329)
def int_to_sub(n):
    """Преобразует число n в строку с пониженным регистром"""
    return "".join(chr(int(char) + 8320) if char.isdigit() else char for char in str(n))
# print(int_to_sub("x12")) # x₁₂

def bits_to_int(bits):
    """Преобразует список битов в число (старший бит слева)."""
    return int("".join(map(str, bits)), 2)



class BooleanFunction:
    """Булева функция от n переменных, заданная таблицей истинности или лямбда-выражением."""

    def __init__(self, n, source, inputs=None, outputs=("y",), is_rows=False):
        self.n = n
        self.inputs  = inputs or n
        self.outputs = outputs
        if is_rows:
            self.truth_rows = source
        else:
            if len(outputs) == 1:
                truth_table = (self.read_truth_table(n, source),)
            else:
                if len(source) != len(outputs):
                    raise ValueError("Неверное количество столбиков истинности")
                truth_table = tuple(self.read_truth_table(n, column) for column in source)  
            self.truth_rows = tuple(zip(*truth_table))

    @staticmethod
    def read_truth_table(n, source):
        if type(source) in (tuple, list):
            if len(source) != 2 ** n:
                raise ValueError("Длина столбика истинности должна быть 2^n")
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
        skip  = n - _in
        out   = self.outputs
        truth = self.truth_rows
        table = (
            (*(int_to_sub(f"x{i}") for i in range(_in, 0, -1)), *map(int_to_sub, out)),
            *(
                (*int_to_bits(i, n, skip), *truth[i]) for i in range(2 ** n)
            ),
        )

        io = StringIO()
        print_table(table, io, middle_sep = False)
        return io.getvalue()

    def get_f(self):
        n     = self.n
        skip  = n - self.inputs
        truth = self.truth_rows
        one  = len(self.outputs) == 1
        dict = {}

        for i in range(2 ** n):
            I = int_to_bits(i, n, skip)
            O = truth[i][0] if one else truth[i]
            try:             dict[I].add(O)
            except KeyError: dict[I] = {O}

        for key in tuple(dict):
            if len(dict[key]) == 1: dict[key] = next(iter(dict[key]))
        # print(dict)
        return lambda *a: dict[a]

    def quantum_transform(self, f):
        n     = self.n
        skip  = n - self.inputs
        truth = self.truth_rows
        f = f.get_f()
        new_rows = []

        for i in range(2 ** n):
            I   = int_to_bits(i, n, skip)
            inv = f(*I)
            if type(inv) is not int:
                raise ValueError(f"Неопределённое состояние при {I}: {inv}")
            row = truth[i]
            if inv: row = tuple(i^1 for i in row)
            new_rows.append(row)

        outputs = tuple(name + "^f" for name in self.outputs)
        return BooleanFunction(n, new_rows, self.inputs, outputs, is_rows=True)

    def to_rows(self):
        n     = self.n
        skip  = n - self.inputs
        truth = self.truth_rows
        for i in range(2 ** n):
            yield int_to_bits(i, n, skip) + truth[i]

    def to_C(self):
        C = tuple(bits_to_int(row) for row in self.to_rows())
        # print(C) # (1, 0, 3, 2, 4, 5, 7, 6)
        return CompactMatrix(C)

    # def to_matrix(self):
    #     return Matrix(*self.to_rows())
    # УПС! Старое правило мешает: матрицы всегда квадратные ;'-}
    # Класс НЕ рассчитан на прямоугольные матрицы, увы



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



class CompactMatrix:
    """Компактно хранит разряженную матрицу"""

    def __init__(self, C):
        self.C = C

    def to_rows(self):
        C = self.C
        n = len(C)
        for pos in C:
            yield tuple(int(i == pos) for i in range(n))

    def __repr__(self):
        n   = len(self.C)
        sep = f"+{'-' * (n * 2 + 1)}+\n"
        io  = StringIO(); write = io.write

        write(sep)
        for row in self.to_rows():
            row = " ".join(map(str, row))
            write(f"| {row} |\n")
        write(sep)

        return io.getvalue()

    def to_matrix(self):
        return Matrix(*self.to_rows())



f1 = BooleanFunction(2, lambda a, b: a <= b)
f2 = BooleanFunction(3, (0, 1) * 4, 2)
ft = f2.quantum_transform(f1)
""" print(ft)
+----+----+-----+
| x₂ | x₁ | y^f |
+----+----+-----+
|  0 |  0 |   1 |
|  0 |  0 |   0 |
|  0 |  1 |   1 |
|  0 |  1 |   0 |
|  1 |  0 |   0 |
|  1 |  0 |   1 |
|  1 |  1 |   1 |
|  1 |  1 |   0 |
+----+----+-----+
"""
C_mat = ft.to_C()
""" print(C_mat)
+-----------------+
| 0 1 0 0 0 0 0 0 |
| 1 0 0 0 0 0 0 0 |
| 0 0 0 1 0 0 0 0 |
| 0 0 1 0 0 0 0 0 |
| 0 0 0 0 1 0 0 0 |
| 0 0 0 0 0 1 0 0 |
| 0 0 0 0 0 0 0 1 |
| 0 0 0 0 0 0 1 0 |
+-----------------+
"""
mat = C_mat.to_matrix()
print(mat)
print("Унитарная?", "❌✅"[mat.is_unitary()])
"""
M = ⎧0, 1, 0, 0, 0, 0, 0, 0⎫
    ⎪1, 0, 0, 0, 0, 0, 0, 0⎪
    ⎪0, 0, 0, 1, 0, 0, 0, 0⎪
    ⎪0, 0, 1, 0, 0, 0, 0, 0⎪
    ⎪0, 0, 0, 0, 1, 0, 0, 0⎪
    ⎪0, 0, 0, 0, 0, 1, 0, 0⎪
    ⎪0, 0, 0, 0, 0, 0, 0, 1⎪
    ⎩0, 0, 0, 0, 0, 0, 1, 0⎭
Унитарная? ✅
"""




