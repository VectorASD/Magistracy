from pprint import pprint

from misc import float_eq, edge_enumerate
from number_decorator import decorate_num



class Qubit:
    def __init__(self, a0, a1):
        assert float_eq(abs(a0) ** 2 + abs(a1) ** 2, 1)
        self.a0 = a0
        self.a1 = a1
    def vector(self):
        return self.a0, self.a1

    def __repr__(self):
        a0, a1 = self.a0, self.a1
        sign = a1 < 0
        a0 = "1 " if a0 == 1 else "-" if a0 == -1 else decorate_num(a0) + ' '
        a1 = "" if a1 == -1 else decorate_num(abs(a1)) + ' '
        return f"|φ> {a0}|0> {'-' if sign else '+'} {a1}|1>"

    def vec_repr(self):
        a0 = decorate_num(self.a0)
        a1 = decorate_num(self.a1)
        size = max(len(a0), len(a1))
        return f"      ⎧ {a0.rjust(size)} ⎫\n|φ> = ⎪ {' ' * size} ⎪\n      ⎩ {a1.rjust(size)} ⎭"
        # Cascadia Mono, 14px, no bold

    @staticmethod
    def test():
        print("  0°:", Q_0)   # |φ> 1 |0> + 0 |1>
        print(" 30°:", Q_30)  # |φ> √3/2 |0> + 1/2 |1>
        print(" 45°:", Q_45)  # |φ> 1/√2 |0> + 1/√2 |1>
        print(" 60°:", Q_60)  # |φ> 1/2 |0> + √3/2 |1>
        print(" 90°:", Q_90)  # |φ> 0 |0> + |1>
        print("210°:", Q_210) # |φ> -√3/2 |0> - 1/2 |1>
        print("225°:", Q_225) # |φ> -1/√2 |0> - 1/√2 |1>

        print(Q_60.vec_repr())

s2 = 2 ** 0.5
s3 = 3 ** 0.5
Q_0   = Qubit(  1,     0)
Q_30  = Qubit( s3/2,   0.5)
Q_45  = Qubit(  1/s2,  1/s2)
Q_60  = Qubit(  0.5,  s3/2)
Q_90  = Qubit(  0,     1)
Q_210 = Qubit(-s3/2,  -0.5)
Q_225 = Qubit( -1/s2, -1/s2)

# Qubit.test()



class Matrix:
    def __init__(self, *mat):
        N = len(mat)
        assert N > 0
        assert all(len(row) == N for row in mat)
        self.mat = mat

    def __repr__(self):
        mat = tuple(tuple(map(decorate_num, row)) for row in self.mat)
        lens = tuple(max(map(len, col)) for col in zip(*mat))
        format = ", ".join("{:%s}" % x for x in lens).format

        Str = "\n    ".join(f'{"⎧⎪⎩("[e]}{format(*row)}{"⎫⎪⎭)"[e]}' for e, row in edge_enumerate(mat))
        return f"M = {Str}"

    def __mul__(self, R):
        T = type(R)

        if T is tuple:
            vec = R
        elif hasattr(R, "vector"):
            vec = R.vector()
            assert type(vec) is tuple
        else:
            assert T in (int, float, complex)
            return Matrix(*(tuple(e * R for e in row) for row in self.mat))

        assert len(self.mat) == len(vec)
        return T(*(sum(a * b for a, b in zip(row, vec)) for row in self.mat))

    def __invert__(self): # conjugate и транспонирование
        return Matrix(*(tuple(e.conjugate() for e in row) for row in zip(*self.mat)))

    def __matmul__(self, right):
        A = self.mat
        B = right.mat
        assert len(A) == len(B)
        Range = range(len(A))
        return Matrix(*(tuple(sum(A[i][k] * B[k][j] for k in Range) for j in Range) for i in Range))

    def __eq__(self, right):
        A = self.mat
        B = right.mat
        if len(A) != len(B): return False
        return all(float_eq(a, b) for row_A, row_B in zip(A, B) for a, b in zip(row_A, row_B))

    def is_unitary(self):
        return (H @ ~H) == I

    @staticmethod
    def test():
        print(H)
        print(NOT * Q_0)
        print(H   * Q_0)
        print(~H)
        print(H.is_unitary())
        print(~C == C, C.is_unitary())

I   = Matrix((1, 0), (0, 1))
NOT = Matrix((0, 1), (1, 0))
H   = Matrix((1, 1), (1, -1)) * (1/s2) # Hadamard
C   = Matrix((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1), (0, 0, 1, 0))

Matrix.test()
