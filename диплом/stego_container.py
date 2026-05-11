from bitstr import BitStr
from lambda_table import Lambda

from math import floor, log2

PRIMES = (1, 3, 7, 13, 19, 37, 67, 131, 283)



class StegoContainer:
    """Стеганографический контейнер на основе кодов поля GF(2^m)."""

    def __init__(self, empty_message: str | BitStr) -> None:
        if isinstance(empty_message, str):
            if not empty_message:
                raise ValueError("Empty string is not allowed as container")
            self.len = len(empty_message)
            empty_message = BitStr(empty_message)
        else:
            self.len = empty_message.format_size
            if self.len <= 0:
                raise ValueError(f"BitStr must have a strictly positive format size, not {self.len} (use format_size parameter when creating BitStr)")

        self.capacity = int(floor(log2(self.len + 1)))
        if self.capacity >= 9:
            raise ValueError("Capacity too large (>= 9)")
        prime = PRIMES[self.capacity]
        self._lambda = Lambda(self.capacity, prime)
        self.empty_message = empty_message

    def get_container_capacity(self) -> int:
        return self.capacity

    def read_from_container(self, stego: str | int | BitStr) -> str:
        if not isinstance(stego, BitStr):
            stego = BitStr(stego)
        s = self._lambda.f_lambda(stego)

      # return f"{s:{self.capacity}}"  # format(s, str(self.capacity))
        s.set_format_size(self.capacity)
        return s

    def write_to_container(self, message: str | int) -> str:
        if not isinstance(message, BitStr):
            message = BitStr(message)
        if len(message) > self.capacity:
            raise ValueError(f"Message length ({len(message)}) exceeds container capacity ({self.capacity})")
        em = self.empty_message
        prime = BitStr(PRIMES[self.capacity])
        u = em % prime
        v = u + message
        d = self._lambda.get_d_by_code(v)
        w = em + d

      # return f"{w:{self.len}}"  # format(w, str(self.len))
        w.set_format_size(self.len)
        return w

    def info(self) -> None:
        self._lambda.show()
