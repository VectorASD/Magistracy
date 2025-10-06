from misc import float_eq, EPS
from number_decorator import decorate_num, exists_decor
from random import random
from math import cos, sin, acos, atan2



class Qubit:
    def __init__(self, a0, a1):
        if not float_eq(abs(a0)**2 + abs(a1)**2, 1):
            raise ValueError("Состояние кватерниона должно лежать на сфере: |a0|² + |a1|² = 1")
        self.a0 = a0
        self.a1 = a1
        self.rounding = None

    def vector(self):
        return self.a0, self.a1

    def __repr__(self):
        a0, a1 = self.a0, self.a1

        signer = lambda n: "" if float_eq(abs(n), 1) else "-" if float_eq(abs(n), -1) else decorate_num(n, self.rounding) + ' '

        if float_eq(abs(a1), 0): return f"|φ> {signer(a0)}|0>"
        if float_eq(abs(a0), 0): return f"|φ> {signer(a1)}|1>"

        if a0 and a1:
            # div = 1 / s2
            # new = a0 / div, a1 / div
            new = a0 * s2, a1 * s2
            div_mode = exists_decor(*new)
            if div_mode: a0, a1 = new
        else: div_mode = False
        # print("***", div_mode, a0, a1, abs(a1), decorate_num(a1))

        a0 = signer(a0)

        a1_real = a1.real
        a1 = "" if float_eq(abs(a1_real), 1) else decorate_num(a1, self.rounding) + ' '
        if a1.endswith("i "): a1 = a1[:-1]

        if   a1.startswith('-'): sign = ''
        elif a1.startswith('i'): sign = '+'
        else:
            sign = '-' if a1_real < 0 else '+'
            a1 = ' ' + a1 if a1 else a1
    
        return f"|φ> {'1/√2 (' if div_mode else ''}{a0}|0> {sign}{a1}|1>{')' if div_mode else ''}"

    def vec_repr(self):
        a0, a1 = self.a0, self.a1
        if a0 and a1:
            new = a0 * s2, a1 * s2
            div_mode = exists_decor(*new)
            if div_mode: a0, a1 = new
        else: div_mode = False

        a0 = decorate_num(a0, self.rounding)
        a1 = decorate_num(a1, self.rounding)
        size = max(len(a0), len(a1))
        return f"      {'     ' if div_mode else ''}⎧ {a0.rjust(size)} ⎫\
               \n|φ> = {'1/√2 ' if div_mode else ''}⎪ {' ' * size} ⎪\
               \n      {'     ' if div_mode else ''}⎩ {a1.rjust(size)} ⎭"
        # Cascadia Mono, 14px, no bold

    def measure_str(self, count = 64):
        w0 = abs(self.a0) ** 2
        # w1 = abs(self.a1) ** 2
        return "".join("01"[random() >= w0] for i in range(count))

    def measure(self, count = 64):
        w0 = abs(self.a0) ** 2
        return tuple(random() >= w0 for i in range(count))

    @staticmethod
    def from_Bloch(x, y, z):
        if not float_eq(x**2 + y**2 + z**2, 1):
            raise ValueError("Точка должна лежать на сфере: x² + y² + z² = 1")

        z, y, x = y, x, z # вращение с осей 3d-движка в оси иллюстрации

        # import cmath
        #   cmath.exp(1j * phi)
        # = (cos(phi) + 1j * sin(phi))
        # = complex(cos(phi), sin(phi))

        half_theta = acos(z) / 2
        phi = atan2(y, x)

        a = cos(half_theta)
        b = complex(cos(phi), sin(phi)) * sin(half_theta)

        #if float_eq(b.imag, 0): b = b.real
        return Qubit(a, b)

    def to_Bloch(self):
        # Нормировка
        # norm = abs(a)**2 + abs(b)**2
        # a = a / math.sqrt(norm)
        # b = b / math.sqrt(norm)
        # Не нужна, т.к. в конструкторе стоит условие, гарантирующее norm = 1)

        a, b = self.a0, self.a1
        part = a.conjugate() * b
        x = 2 * part.real
        y = 2 * part.imag
        z = abs(a)**2 - abs(b)**2

        if abs(x % 1) < EPS or float_eq(abs(x), 1): x = round(x)
        if abs(y % 1) < EPS or float_eq(abs(y), 1): y = round(y)
        if abs(z % 1) < EPS or float_eq(abs(z), 1): z = round(z)

        y, x, z = z, y, x # вращение с осей иллюстрации в оси 3d-движка
        return x, y, z

    @staticmethod
    def test():
        print("\n~~~ test Qubit ~~~\n")
        print("  0°:", Q_0)   # |φ> |0> + 0 |1>
        print(" 30°:", Q_30)  # |φ> √3/2 |0> + 1/2 |1>
        print(" 45°:", Q_45)  # |φ> 1/√2 (|0> + |1>)
        print(" 60°:", Q_60)  # |φ> 1/2 |0> + √3/2 |1>
        print(" 90°:", Q_90)  # |φ> 0 |0> + |1>
        print("180°:", Q_180) # |φ> -|0> + 0 |1>
        print("210°:", Q_210) # |φ> -√3/2 |0> - 1/2 |1>
        print("225°:", Q_225) # |φ> 1/√2 (-|0> -|1>)
        print("240°:", Q_240) # |φ> -1/2 |0> -√3/2 |1>
        print("270°:", Q_270) # |φ> 0 |0> -|1>
        print()

        print(Q_45.vec_repr())
        print(Q_60.vec_repr())
        print("measure( 0°):", Q_0.measure_str())
        print("measure(30°):", Q_30.measure_str())
        print("measure(45°):", Q_45.measure_str())
        print("measure(60°):", Q_60.measure_str())
        print("measure(90°):", Q_90.measure_str())

        print("\nОсь 3d-отрисовщика (ось из иллюстраций)")
        print("+Y (+Z):", Qubit.from_Bloch(0,  1, 0)) # +Y (+Z): |φ> |0>
        print("-Y (-Z):", Qubit.from_Bloch(0, -1, 0)) # -Y (-Z): |φ> |1>
        print("+X (+Y):", Qubit.from_Bloch( 1, 0, 0)) # +X (+Y): |φ> 1/√2 (|0> +i|1>)
        print("-X (-Y):", Qubit.from_Bloch(-1, 0, 0)) # -X (-Y): |φ> 1/√2 (|0> -i|1>)
        print("+Z (+X):", Qubit.from_Bloch(0, 0,  1)) # +Z (+X): |φ> 1/√2 (|0> +|1>)
        print("-Z (-X):", Qubit.from_Bloch(0, 0, -1)) # -Z (-X): |φ> 1/√2 (|0> -|1>)

        print()
        print(Qubit.from_Bloch(0,  1, 0).to_Bloch()) # (0, 1, 0)  = (Q_0 или Q_180).to_Bloch()
        print(Qubit.from_Bloch(0, -1, 0).to_Bloch()) # (0, -1, 0) = (Q_90 или Q_270).to_Bloch()
        print(Qubit.from_Bloch( 1, 0, 0).to_Bloch()) # (1, 0, 0)
        print(Qubit.from_Bloch(-1, 0, 0).to_Bloch()) # (-1, 0, 0)
        print(Qubit.from_Bloch(0, 0,  1).to_Bloch()) # (0, 0, 1)   = Q_45.to_Bloch()
        print(Qubit.from_Bloch(0, 0, -1).to_Bloch()) # (0, 0, -1)

        print("Q_30: ",  Q_30.to_Bloch()) # (0, 0.4999999999999999, 0.8660254037844386)
        print("Q_210:", Q_210.to_Bloch()) # = Q_30.to_Bloch()
        print("Q_45: ",  Q_45.to_Bloch()) # (0, 0, 1)
        print("Q_225:", Q_225.to_Bloch()) # = Q_45.to_Bloch()
        print("Q_60: ",  Q_60.to_Bloch()) # (0, -0.4999999999999999, 0.8660254037844386)
        print("Q_240:", Q_240.to_Bloch()) # = Q_60.to_Bloch()



s2 = 2 ** 0.5
s3 = 3 ** 0.5
Q_0   = Qubit( 1,    0)
Q_30  = Qubit(s3/2,  0.5)
Q_45  = Qubit( 1/s2, 1/s2)
Q_60  = Qubit( 0.5, s3/2)
Q_90  = Qubit( 0,    1)

Q_180 = Qubit( -1,     0)    # = Q_0
Q_210 = Qubit(-s3/2,  -0.5)  # = Q_30
Q_225 = Qubit( -1/s2, -1/s2) # = Q_45
Q_240 = Qubit( -0.5, -s3/2)  # = Q_60
Q_270 = Qubit(  0,    -1)    # = Q_90



if __name__ == "__main__":
    Qubit.test()
