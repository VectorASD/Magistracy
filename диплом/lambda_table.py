from __future__ import annotations
from bitstr import BitStr



class Lambda:
    """
    Таблица поля GF(2^m) с примитивным многочленом prime.
    code[i] – представление элемента x^{i-1} mod prime (для i>0), code[0] = "0".
    """
    __slots__ = ("m", "N", "prime_int", "prime_polynom", "code", "_log_table")

    def __init__(self, m: int, prime: int) -> None:
        if m > 10:
            raise ValueError("m too large (max 10)")
        if prime.bit_length() != m + 1:
            raise ValueError("prime polynomial must have degree m")
        self.m = m
        self.N = 1 << m
        self.prime_int = prime
        self.prime_polynom = BitStr(bin(prime)[2:])
        self._build_table()

    def _build_table(self) -> None:
        """Генерация элементов поля рекуррентным сдвигом и XOR."""
        code = [None] * self.N
        code[0] = BitStr("0")
        elem = 1                      # x^0
        code[1] = BitStr("1")
        for i in range(2, self.N):
            elem <<= 1
            if (elem >> self.m) & 1:  # вытесненный бит за пределы m
                elem ^= self.prime_int
            code[i] = BitStr(bin(elem)[2:])
        self.code = code
        # Таблица логарифмов: для ненулевого элемента int -> индекс в code
        self._log_table = {code[i]._bits: i for i in range(1, self.N)}
        # Для нуля логарифм не определён, обработка отдельно

    def dec2bin(self, x: int) -> str:
        """Двоичное представление целого числа без ведущих нулей (0 -> "0")."""
        return bin(x)[2:] if x != 0 else "0"

    def show(self) -> None:
        for i in range(self.N):
            print(f"{i} -> {self.code[i].get_formated_string(self.m)}")

    def f_lambda(self, b: BitStr) -> BitStr:
        """Остаток от деления b на примитивный многочлен."""
        return b % self.prime_polynom

    def get_d_by_code(self, a: BitStr) -> BitStr:
        """Дискретный логарифм: возвращает x^{log(a)} как "1" + '0'*log (или "0" для нуля)."""
        power = self._discrete_log(a)
        if power == -1:
            return BitStr("0")
        return BitStr(bin(1 << power)[2:])

    def _discrete_log(self, a: BitStr) -> int:
        """Возвращает степень x, дающую a, или -1 для a == 0."""
        if a._bits == 0:
            return -1
        idx = self._log_table.get(a._bits)
        if idx is None:
            raise ValueError("Element not in field")
        return idx - 1
