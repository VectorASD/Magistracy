from misc import float_eq, edge_enumerate
from number_decorator import decorate_num, exists_decor
from math import pi, tan, sin, cos, hypot

from qubit import Qubit, Q_0, s2

pi_2   = pi / 2
pi_180 = pi / 180

def ctg(num):
    # return 1 / tan(num)
    return tan(pi_2 - num) # равнозначны



class Matrix:
    def __init__(self, *mat):
        N = len(mat)
        assert N > 0
        assert all(len(row) == N for row in mat)
        self.mat = mat
        self.letter = "M"

    def __repr__(self):
        mat = self.mat
        if all(all(row) for row in mat):
            new = tuple(tuple(e * s2 for e in row) for row in mat)
            div_mode = exists_decor(*(e for row in new for e in row))
            if div_mode: mat = new
        else: div_mode = False

        mat = tuple(tuple(map(decorate_num, row)) for row in mat)
        lens = tuple(max(map(len, col)) for col in zip(*mat))
        format = ", ".join("{:%s}" % x for x in lens).format

        sep = "\n" + " " * (len(self.letter) + len(' = ') + len('1/√2 ') * div_mode)
        Str = sep.join(f'{"⎧⎪⎩("[e]}{format(*row)}{"⎫⎪⎭)"[e]}' for e, row in edge_enumerate(mat))
        return f"{self.letter} = {'1/√2 ' if div_mode else ''}{Str}"

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
        gen = (sum(a * b for a, b in zip(row, vec)) for row in self.mat)
        return tuple(gen) if T is tuple else T(*gen)

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
    def perspective(fovy, aspect, near, far):
        fovy = ctg(fovy * pi_180 / 2) # inverted fovy_factor
        return Matrix(*(
            (fovy / aspect, 0, 0, 0),
            (0, fovy, 0, 0),
            (0, 0, -(far + near) / (far - near), -2 * far * near / (far - near)),
            (0, 0, -1, 0)
        ))

    @staticmethod
    def view(x, y, z, yaw, pitch, roll):
        yaw   *= pi_180
        pitch *= pi_180
        roll  *= pi_180
        sY, cY = sin(yaw),   cos(yaw)
        sP, cP = sin(pitch), cos(pitch)
        sR, cR = sin(roll),  cos(roll)

        r00, r01, r02 = right = cY*cR,             -cY*sR,            sY
        r10, r11, r12 = up    = sP*sY*cR + cP*sR,  -sP*sY*sR + cP*cR, -sP*cY
        r20, r21, r22 =         -cP*sY*cR + sP*sR, cP*sY*sR + sP*cR,  cP*cY
        forward = -r20, -r21, -r22

        """ Проверено!!!
        Y = Matrix((cY, 0, sY), (0, 1, 0), (-sY, 0, cY))
        P = Matrix((1, 0, 0), (0, cP, -sP), (0, sP, cP))
        R = Matrix((cR, -sR, 0), (sR, cR, 0), (0, 0, 1))
        YPR = P @ Y @ R

        YPR2 = Matrix((r00, r01, r02), (r10, r11, r12), (r20, r21, r22))
        print(YPR)
        print(YPR2)
        print(YPR == YPR2)
        """

        x, y, z = -x, -y, -z
        return Matrix(
            (r00, r01, r02, r00*x + r01*y + r02*z),
            (r10, r11, r12, r10*x + r11*y + r12*z),
            (r20, r21, r22, r20*x + r21*y + r22*z),
            (0,   0,   0,   1),
        ), forward, right, up

    def project(self, x, y, z, color, winX, winY):
        x, y, z, w = self * (x, y, z, 1)
        if w:
            return (x / w + 1) * (winX / 2), (1 - y / w) * (winY / 2), z / w, color
        return 0, 0, 2, color
        # z = -1 (далеко)
        # z = 1 (близко)
        # z > 1 (за камерой)

    def __call__(self, letter):
        self.letter = letter
        return self

    @property
    def is_rotation_orthonormal(self, eps=1e-6):
        mat = self.mat
        r00, r01, r02, _ = mat[0]
        r10, r11, r12, _ = mat[1]
        r20, r21, r22, _ = mat[2]

        # Проверка нормированности
        if abs(hypot(r00, r01, r02) - 1) > eps: return False
        if abs(hypot(r10, r11, r12) - 1) > eps: return False
        if abs(hypot(r20, r21, r22) - 1) > eps: return False

        # Проверка ортогональности
        if abs(r00*r10 + r01*r11 + r02*r12) > eps: return False
        if abs(r00*r20 + r01*r21 + r02*r22) > eps: return False
        if abs(r10*r20 + r11*r21 + r12*r22) > eps: return False

        return True

    @staticmethod
    def test():
        print("\n~~~ test Matrix ~~~\n")
        print(H("H"))
        print(NOT * Q_0)
        print(H   * Q_0)
        print((~H)("~H"))
        print(H.is_unitary())
        print(~C == C, C.is_unitary())
        print()

        proj = Matrix.perspective(90, 1, 0.01, 100)
        print(Matrix.view(0, 0, 0, 60,  0,  0)[0]("Y-rot")) # sY = √3/2; cY = 1/2
        print(Matrix.view(0, 0, 0,  0, 60,  0)[0]("P-rot")) # sP = √3/2; cP = 1/2
        print(Matrix.view(0, 0, 0,  0,  0, 60)[0]("R-rot")) # sR = √3/2; cR = 1/2
        view, F, R, U = Matrix.view(-30, 0, 0, 0, 90, 0)
        proj_view = proj @ view
        print(proj("proj"), "affin:", proj.is_rotation_orthonormal)
        print(view("view"), "affin:", view.is_rotation_orthonormal)
        print(proj_view("p@v"), "affin:", proj_view.is_rotation_orthonormal)
        print("Forward:", F)
        print("Right:",   R)
        print("Up:",      U)
        print(proj_view.project(5, 5/2, 0, "color", 64, 64))

I   = Matrix((1, 0), (0, 1))
NOT = Matrix((0, 1), (1, 0))
H   = Matrix((1, 1), (1, -1)) * (1/s2) # Hadamard
C   = Matrix((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1), (0, 0, 1, 0))



if __name__ == "__main__":
    Qubit.test()
    Matrix.test()
