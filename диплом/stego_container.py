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
        return f"{s:{self.capacity}}"  # format(s, str(self.capacity))

    def write_to_container(self, sm: str | int) -> str:
        s = BitStr(sm)
        if len(s) > self.capacity:
            raise ValueError(f"Message length ({len(s)}) exceeds container capacity ({self.capacity})")
        em = BitStr(self.empty_message)
        prime = BitStr(PRIMES[self.capacity])
        u = em % prime
        v = u + s
        d = self._lambda.get_d_by_code(v)
        w = em + d
        return f"{w:{self.len}}"  # format(w, str(self.len))

    def info(self) -> None:
        self._lambda.show()
