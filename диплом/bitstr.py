from __future__ import annotations
from typing import Tuple



class BitStr:
    """
    Поток битов, хранящийся в целом числе.
    Старший бит всегда имеет индекс 0 в строковом представлении.
    Ведущие нули автоматически удаляются. Нулевая строка хранится как "0".
    """

    __slots__ = ("_bits", "_size")

    # ------------------------------------------------------------------
    # Конструкторы
    # ------------------------------------------------------------------
    def __init__(self, s: str = "") -> None:
        if not s:
            self._bits = 0
            self._size = 1
            return
        stripped, _ = self._align(s)
        if not stripped:
            stripped = "0"
        self._bits = int(stripped, 2)
        self._size = len(stripped)

    @classmethod
    def _from_int(cls, value: int, size: int) -> BitStr:
        """Внутренний конструктор"""
        obj = cls.__new__(cls)
        obj._bits = value
        obj._size = size
        return obj

    # ------------------------------------------------------------------
    # Приватные утилиты
    # ------------------------------------------------------------------
    @staticmethod
    def _align(s: str) -> Tuple[str, int]:
        """
        Удаляет ведущие нули строки s.
        Возвращает (обрезанная_строка, количество_удалённых_нулей).
        """
        pos = 0
        length = len(s)
        while pos < length and s[pos] == '0':
            pos += 1
        if pos == length:
            return "", length
        return s[pos:], pos

    # ------------------------------------------------------------------
    # Специальные методы (Python dunder)
    # ------------------------------------------------------------------
    def __str__(self) -> str:
        return bin(self._bits)[2:] if self._size > 0 else "0"

    def __repr__(self) -> str:
        return f"BitStr('{self}')"

    def __getitem__(self, i: int) -> int:
        if 0 <= i < self._size:
            return (self._bits >> (self._size - 1 - i)) & 1
        return 0

    def __len__(self) -> int:
        return self._size

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BitStr):
            return NotImplemented
        return self._bits == other._bits and self._size == other._size

    def __ne__(self, other: object) -> bool:
        return not self == other

    def __add__(self, other: BitStr) -> BitStr:
        """
        Побитовый XOR с выравниванием по младшему биту.
        Старшие биты более длинного операнда копируются без изменений.
        """
        result_val = self._bits ^ other._bits
        return BitStr(bin(result_val)[2:])

    def __mod__(self, other: BitStr) -> BitStr:
        """
        Остаток от деления многочленов в поле GF(2) (XOR вместо вычитания).
        """
        if other._bits == 0:
            raise ZeroDivisionError("Division by zero BitStr")
        dd = self._bits
        ds = other._bits
        while dd.bit_length() >= other._size:
            shift = dd.bit_length() - other._size
            dd ^= (ds << shift)
        return BitStr(bin(dd)[2:])

    # ------------------------------------------------------------------
    # Публичные методы
    # ------------------------------------------------------------------
    def as_number(self) -> int:
        """Возвращает целочисленное представление битовой строки."""
        return self._bits

    def get_size(self) -> int:
        """Возвращает длину битовой строки в битах."""
        return self._size

    def get_formated_string(self, m: int) -> str:
        """
        Возвращает строку длиной ровно m, дополненную ведущими нулями.
        Если исходная строка длиннее m, возвращается как есть.
        """
        s = str(self)
        if len(s) >= m:
            return s
        return "0" * (m - len(s)) + s
