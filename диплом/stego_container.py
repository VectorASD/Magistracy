from bitstr import BitStr
from lambda_table import Lambda

from math import floor, log2

PRIMES = (1, 3, 7, 13, 19, 37, 67, 131, 283)



class StegoContainer:
    """Стеганографический контейнер на основе кодов поля GF(2^m)."""

    def __init__(self, empty_message: str) -> None:
        self.len = len(empty_message)
        self.capacity = int(floor(log2(self.len + 1)))
        if self.capacity >= 9:
            raise ValueError("Capacity too large (>= 9)")
        prime = PRIMES[self.capacity]
        self._lambda = Lambda(self.capacity, prime)
        self.empty_message = empty_message

    def get_container_capacity(self) -> int:
        return self.capacity

    def read_from_container(self, st_cont: str) -> str:
        d = BitStr(st_cont)
        s = self._lambda.f_lambda(d)
        return s.get_formated_string(self.capacity)

    def write_to_container(self, sm: str) -> str:
        if len(sm) != self.capacity:
            raise ValueError("Message length must match capacity")
        s = BitStr(sm)
        em = BitStr(self.empty_message)
        prime = BitStr(self._lambda.dec2bin(PRIMES[self.capacity]))
        u = em % prime
        v = u + s
        d = self._lambda.get_d_by_code(v)
        w = em + d
        return w.get_formated_string(self.len)

    def info(self) -> None:
        self._lambda.show()
