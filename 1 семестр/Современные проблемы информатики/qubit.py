from misc import float_eq
from number_decorator import decorate_num, exists_decor
from random import random



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

        if a0 and a1:
            # div = 1 / s2
            # new = a0 / div, a1 / div
            new = a0 * s2, a1 * s2
            div_mode = exists_decor(*new)
            if div_mode: a0, a1 = new
        else: div_mode = False

        a0 = "" if a0 == 1 else "-" if a0 == -1 else decorate_num(a0) + ' '
        a1 = "" if abs(a1) == 1 else decorate_num(abs(a1)) + ' '
        return f"|φ> {'1/√2 (' if div_mode else ''}{a0}|0> {'-' if sign else '+'}{' ' if a1 else ''}{a1}|1>{')' if div_mode else ''}"

    def vec_repr(self):
        a0, a1 = self.a0, self.a1
        if a0 and a1:
            new = a0 * s2, a1 * s2
            div_mode = exists_decor(*new)
            if div_mode: a0, a1 = new
        else: div_mode = False

        a0 = decorate_num(a0)
        a1 = decorate_num(a1)
        size = max(len(a0), len(a1))
        return f"      {'     ' if div_mode else ''}⎧ {a0.rjust(size)} ⎫\
               \n|φ> = {'1/√2 ' if div_mode else ''}⎪ {' ' * size} ⎪\
               \n      {'     ' if div_mode else ''}⎩ {a1.rjust(size)} ⎭"
        # Cascadia Mono, 14px, no bold

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
        print("270°:", Q_270) # |φ> 0 |0> -|1>
        print()

        print(Q_45.vec_repr())
        print(Q_60.vec_repr())
        print("measure( 0°):", Q_0.measure())
        print("measure(30°):", Q_30.measure())
        print("measure(45°):", Q_45.measure())
        print("measure(60°):", Q_60.measure())
        print("measure(90°):", Q_90.measure())

    def measure(self, count = 64):
        w0 = abs(self.a0) ** 2
        # w1 = abs(self.a1) ** 2
        return "".join("01"[random() > w0] for i in range(count))

s2 = 2 ** 0.5
s3 = 3 ** 0.5
Q_0   = Qubit(  1,     0)
Q_30  = Qubit( s3/2,   0.5)
Q_45  = Qubit(  1/s2,  1/s2)
Q_60  = Qubit(  0.5,  s3/2)
Q_90  = Qubit(  0,     1)
Q_180 = Qubit( -1,     0)
Q_210 = Qubit(-s3/2,  -0.5)
Q_225 = Qubit( -1/s2, -1/s2)
Q_270 = Qubit(  0,    -1)



if __name__ == "__main__":
    Qubit.test()
