from pprint import pprint

from misc import float_eq
from number_decorator import decorate_num

class Qubit:
    def __init__(self, a0, a1):
        assert float_eq(abs(a0) ** 2 + abs(a1) ** 2, 1)
        self.a0 = a0
        self.a1 = a1
    def __repr__(self):
        return f"|φ> {decorate_num(self.a0)} |0> + {decorate_num(self.a1)} |1>"

print(Qubit(0, 1)) # |φ> 0 |0> + 1 |1>
print(Qubit(1, 0)) # |φ> 1 |0> + 0 |1>
print(Qubit(1/2**0.5, 1/2**0.5)) # |φ> 1/√2 |0> + 1/√2 |1>
