import inspect
from io import StringIO
from math import log2, ceil

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

    def __init__(self, n, source=None, inputs=None, outputs=" y", is_rows=False):
        outputs = (outputs,) if type(outputs) is str else outputs
        if is_rows:
            self.truth_rows = source
        else:
            if source is None:
                self.truth_rows = ((),) * (2 ** n)
                outputs = ()
            elif len(outputs) == 1:
                truth_table = (self.read_truth_table(n, source),)
                self.truth_rows = tuple(zip(*truth_table))
            else:
                if len(source) != len(outputs):
                    raise ValueError("Неверное количество столбиков истинности")
                truth_table = tuple(self.read_truth_table(n, column) for column in source)
                self.truth_rows = tuple(zip(*truth_table))

        self.n = n
        self.inputs  = n if inputs is None else inputs
        self.outputs = outputs

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
        print_table(table, io, middle_sep = False, column_sep = False)
        return io.getvalue()

    def get_f(self):
        n     = self.n
        skip  = n - self.inputs
        truth = self.truth_rows
        # one  = len(self.outputs) == 1
        dict = {}

        for i in range(2 ** n):
            I = int_to_bits(i, n, skip)
            O = truth[i] # truth[i][0] if one else truth[i]
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
        func = f.get_f()

        new_rows = []
        append   = new_rows.append

        for i in range(2 ** n):
            I   = int_to_bits(i, n, skip)
            inv = func(*I)
            if type(inv) is set:
                raise ValueError(f"Неопределённое состояние при {I}: {inv}")
            row = truth[i]
            row = tuple(a^b for a, b in zip(row, inv))
            append(row)

        outputs = tuple(name.strip() + "⊕" + name2.strip() for name, name2 in zip(self.outputs, f.outputs))
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

    def shift(self, count):
        n     = self.n
        skip  = n - self.inputs
        truth = self.truth_rows
        rows = tuple(int_to_bits(i, skip+count, skip) + truth[i]
                     for i in range(2 ** n))

        outputs = self.outputs
        if outputs and outputs[-1] == " y": # восстанавливаем 'y₁' из 'y'
            outputs = (*outputs[:-1], "y1")

        if skip == 0 and count == 1:
            outputs = (" y",) # 'y' вместо 'y₁'
        else:
            outputs = (*(f"y{i}" for i in range(skip+count, skip, -1)), *outputs)

        return BooleanFunction(n, rows, self.inputs-count, outputs, is_rows=True)

    @staticmethod
    def synthesize(n, func):
        sig = inspect.signature(func)
        if len(sig.parameters) != 1:
            raise ValueError(f"Функция должна принимать 1 аргумент (иметь вид lambda x: ...)")
        items = tuple(func(i) for i in range(2 ** n))
        bits = ceil(log2(max(items) + 1))
        rows = tuple(int_to_bits(i, bits) for i in items)

        outputs = tuple(f"f{i}" for i in range(bits, 0, -1))
        return BooleanFunction(n, rows, None, outputs, is_rows=True)
        



assert repr(BooleanFunction(2, (1, 1, 0, 1))) == """
+----------+
| x₂ x₁  y |
+----------+
|  0  0  1 |
|  0  1  1 |
|  1  0  0 |
|  1  1  1 |
+----------+
""".strip()

assert repr(BooleanFunction(2, lambda a, b: a <= b)) == """
+----------+
| x₂ x₁  y |
+----------+
|  0  0  1 |
|  0  1  1 |
|  1  0  0 |
|  1  1  1 |
+----------+
""".strip()

assert repr(BooleanFunction(3, lambda a, b, c: a == b, None, ("name",))) == """
+---------------+
| x₃ x₂ x₁ name |
+---------------+
|  0  0  0    1 |
|  0  0  1    1 |
|  0  1  0    0 |
|  0  1  1    0 |
|  1  0  0    0 |
|  1  0  1    0 |
|  1  1  0    1 |
|  1  1  1    1 |
+---------------+
""".strip()

assert repr(BooleanFunction(3, (lambda a, b, c: a == b, lambda a, b, c: a != b), 2, ("y1", "y2"))) == """
+-------------+
| x₂ x₁ y₁ y₂ |
+-------------+
|  0  0  1  0 |
|  0  0  1  0 |
|  0  1  0  1 |
|  0  1  0  1 |
|  1  0  0  1 |
|  1  0  0  1 |
|  1  1  1  0 |
|  1  1  1  0 |
+-------------+
""".strip()

assert repr(BooleanFunction(3).shift(1)) == """
+----------+
| x₂ x₁  y |
+----------+
|  0  0  0 |
|  0  0  1 |
|  0  1  0 |
|  0  1  1 |
|  1  0  0 |
|  1  0  1 |
|  1  1  0 |
|  1  1  1 |
+----------+
""".strip()

assert repr(BooleanFunction(3).shift(2)) == """
+----------+
| x₁ y₂ y₁ |
+----------+
|  0  0  0 |
|  0  0  1 |
|  0  1  0 |
|  0  1  1 |
|  1  0  0 |
|  1  0  1 |
|  1  1  0 |
|  1  1  1 |
+----------+
""".strip() == repr(BooleanFunction(3).shift(1).shift(1))



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

        io.truncate(io.tell() - 1)
        return io.getvalue()

    def to_matrix(self):
        return Matrix(*self.to_rows())



def check_quantum_transform(L, R, file):
    ft = L.quantum_transform(R)
    print("ft:", ft, sep="\n", file=file)

    print(file=file)

    C_mat = ft.to_C()
    print("C_mat:", C_mat, sep="\n", file=file)
    print("А как это выглядит в памяти:", C_mat.C, file=file)
    mat = C_mat.to_matrix()
    # print(mat, file=file)
    print("Унитарная?", "❌✅"[mat.is_unitary()], file=file)



def universal_synthesizer(n, func, file):
    synth = BooleanFunction.synthesize(n, func)
    print("synth:", synth, sep="\n", file=file)

    bits = len(synth.outputs)
    f = BooleanFunction(n + bits).shift(bits)
    print("f:", f, sep="\n", file=file)

    check_quantum_transform(f, synth, file)



if __name__ == "__main__":
    from sys import stdout
    from time import time

    f1 = BooleanFunction(3).shift(1) # раньше shift не было... BooleanFunction(3, (0, 1) * 4, 2)
    print("f1:", f1, sep="\n")
    f2 = BooleanFunction(2, lambda a, b: a <= b, outputs=" f")
    print("f2:", f2, sep="\n")
    check_quantum_transform(f1, f2, stdout)

    print()
    print("~" * 77)
    print()

    f = BooleanFunction(4).shift(2)
    print("f:", f, sep="\n")
    synth = BooleanFunction.synthesize(2, lambda x: 3 * x % 4)
    print("synth:", synth, sep="\n")
    check_quantum_transform(f, synth, stdout)

    print()
    print("~" * 77)
    print()

    a = 3
    mod = 15
    n = ceil(log2(mod))

    with open("solve3.txt", "w", encoding="utf-8") as file:
        T1 = time()
        print(f"Функция: {a} ^ x mod {mod}", file=file)
        universal_synthesizer(n, lambda x: pow(a, x, mod), file)
        T2 = time()
        print("Время расчётов и записи в этот файл:", T2 - T1, "с.", file=file)
    print("Время расчётов и записи в файл 'solve3.txt':", T2 - T1, "с.")



r"""
Python 3.13.7 (tags/v3.13.7:bcee1c3, Aug 14 2025, 14:15:11) [MSC v.1944 64 bit (AMD64)] on win32
Enter "help" below or click "Help" above for more information.

================================= RESTART: C:\Users\VectorASD\Desktop\Учёба\1 семестр\Современные проблемы информатики\logic.py ================================
f1:
+----------+
| x₂ x₁  y |
+----------+
|  0  0  0 |
|  0  0  1 |
|  0  1  0 |
|  0  1  1 |
|  1  0  0 |
|  1  0  1 |
|  1  1  0 |
|  1  1  1 |
+----------+
f2:
+----------+
| x₂ x₁  f |
+----------+
|  0  0  1 |
|  0  1  1 |
|  1  0  0 |
|  1  1  1 |
+----------+
ft:
+-----------+
| x₂ x₁ y⊕f |
+-----------+
|  0  0   1 |
|  0  0   0 |
|  0  1   1 |
|  0  1   0 |
|  1  0   0 |
|  1  0   1 |
|  1  1   1 |
|  1  1   0 |
+-----------+

C_mat:
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
А как это выглядит в памяти: (1, 0, 3, 2, 4, 5, 7, 6)
Унитарная? ✅

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

f:
+-------------+
| x₂ x₁ y₂ y₁ |
+-------------+
|  0  0  0  0 |
|  0  0  0  1 |
|  0  0  1  0 |
|  0  0  1  1 |
|  0  1  0  0 |
|  0  1  0  1 |
|  0  1  1  0 |
|  0  1  1  1 |
|  1  0  0  0 |
|  1  0  0  1 |
|  1  0  1  0 |
|  1  0  1  1 |
|  1  1  0  0 |
|  1  1  0  1 |
|  1  1  1  0 |
|  1  1  1  1 |
+-------------+
synth:
+-------------+
| x₂ x₁ f₂ f₁ |
+-------------+
|  0  0  0  0 |
|  0  1  1  1 |
|  1  0  1  0 |
|  1  1  0  1 |
+-------------+
ft:
+-------------------+
| x₂ x₁ y₂⊕f₂ y₁⊕f₁ |
+-------------------+
|  0  0     0     0 |
|  0  0     0     1 |
|  0  0     1     0 |
|  0  0     1     1 |
|  0  1     1     1 |
|  0  1     1     0 |
|  0  1     0     1 |
|  0  1     0     0 |
|  1  0     1     0 |
|  1  0     1     1 |
|  1  0     0     0 |
|  1  0     0     1 |
|  1  1     0     1 |
|  1  1     0     0 |
|  1  1     1     1 |
|  1  1     1     0 |
+-------------------+

C_mat:
+---------------------------------+
| 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 |
| 0 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 |
| 0 0 1 0 0 0 0 0 0 0 0 0 0 0 0 0 |
| 0 0 0 1 0 0 0 0 0 0 0 0 0 0 0 0 |
| 0 0 0 0 0 0 0 1 0 0 0 0 0 0 0 0 |
| 0 0 0 0 0 0 1 0 0 0 0 0 0 0 0 0 |
| 0 0 0 0 0 1 0 0 0 0 0 0 0 0 0 0 |
| 0 0 0 0 1 0 0 0 0 0 0 0 0 0 0 0 |
| 0 0 0 0 0 0 0 0 0 0 1 0 0 0 0 0 |
| 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 0 |
| 0 0 0 0 0 0 0 0 1 0 0 0 0 0 0 0 |
| 0 0 0 0 0 0 0 0 0 1 0 0 0 0 0 0 |
| 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 |
| 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 |
| 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 |
| 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 |
+---------------------------------+
А как это выглядит в памяти: (0, 1, 2, 3, 7, 6, 5, 4, 10, 11, 8, 9, 13, 12, 15, 14)
Унитарная? ✅

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Время расчётов и записи в файл 'solve3.txt': 0.02521204948425293 с.
"""
