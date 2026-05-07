from __future__ import annotations
from typing import Tuple



class BitStr:
    """
    Поток битов, хранящийся в целом числе.
    Старший бит всегда имеет индекс 0 в строковом представлении.
    Ведущие нули автоматически удаляются. Нулевая строка хранится как "0".
    """

    __slots__ = ("_bits", "_size", "_format_size")

    # ------------------------------------------------------------------
    # Конструкторы
    # ------------------------------------------------------------------
    def __init__(self, s: str | int = 0, format_size: int = 0) -> None:
        # Пустая строка или 0 — представляем как "0"
        if not s:
            self._bits = 0
            self._size = 1
            self._format_size = format_size
            return

        if isinstance(s, str):
            value = int(s, 2)
        elif isinstance(s, int):
            value = s
        else:
            raise TypeError(f"Expected str or int, got {type(s).__name__!r}")

        if value < 0:
            raise ValueError(f"BitStr does not support negative integers: {value}")

        self._bits = value
        self._size = max(1, value.bit_length())  # для 0 оставили 1, для остальных — реальная длина
        self._format_size = format_size

    # ------------------------------------------------------------------
    # Специальные методы (Python dunder)
    # ------------------------------------------------------------------
    def __str__(self) -> str:
        s = bin(self._bits)[2:] if self._size > 0 else "0"
        if self._format_size:
            return s.zfill(self._format_size)
        return s

    def __repr__(self) -> str:
        if self._format_size:
            return f"{type(self).__name__}('{self}', {self._format_size})"
        return f"{type(self).__name__}('{self}')"

    def __getitem__(self, i: int) -> int:
        if 0 <= i < self._size:
            return (self._bits >> (self._size - 1 - i)) & 1
        return 0

    def __len__(self) -> int:
        return self._size

    def __eq__(self, other: object) -> bool:
        if isinstance(other, (int, str)):
            try:
                other = BitStr(other)
            except ValueError:
                return False
        elif not isinstance(other, BitStr):
            return NotImplemented

        return self._bits == other._bits and self._size == other._size

    def __ne__(self, other: object) -> bool:
        return not self == other

    def __add__(self, other: object) -> BitStr:
        """
        Побитовый XOR с выравниванием по младшему биту.
        Старшие биты более длинного операнда копируются без изменений.
        """
        if isinstance(other, (int, str)):
            other = BitStr(other)
        elif not isinstance(other, BitStr):
            return NotImplemented

        result_val = self._bits ^ other._bits
        return BitStr(result_val)

    def __mod__(self, other: object) -> BitStr:
        """
        Остаток от деления многочленов в поле GF(2) (XOR вместо вычитания).
        """
        if isinstance(other, (int, str)):
            other = BitStr(other)
        elif not isinstance(other, BitStr):
            return NotImplemented

        if other._bits == 0:
            raise ZeroDivisionError("Division by zero BitStr")
        dd = self._bits
        ds = other._bits
        while dd.bit_length() >= other._size:
            shift = dd.bit_length() - other._size
            dd ^= (ds << shift)
        return BitStr(dd)

    # ------------------------------------------------------------------
    # Публичные методы
    # ------------------------------------------------------------------
    def __int__(self) -> int:
        """Возвращает целочисленное представление битовой строки."""
        return self._bits

    def __index__(self) -> int:
        """Чтобы BitStr можно было использовать в индексации, срезах, как аргумент range() и т.д"""
        return self._bits

    def get_size(self) -> int:
        """Возвращает длину битовой строки в битах."""
        return self._size

    def set_format_size(self, size: int) -> None:
        self._format_size = size

    def __format__(self, format_spec: str) -> str:
        """
        Возвращает строку, дополненную ведущими нулями до длины format_spec.
        Если исходная строка длиннее, возвращается без изменений.
        Может заранее помнить длину через _format_size.
        """
        s = bin(self._bits)[2:] if self._size > 0 else "0"
        if not format_spec:
            if self._format_size:
                return s.zfill(self._format_size)
            return s
        try:
            length = int(format_spec)
        except ValueError:
            raise ValueError(f"Invalid format specifier for {type(self).__name__}: {format_spec!r}")
        return s.zfill(length)
