class DiscrLog:
    """Дискретный логарифм в поле GF(2)[x]/(P)."""
    def __init__(self, p: int, y: int) -> None:
        self.p = p
        self.size_p = max(p.bit_length(), 1)
        self.y = y
        self.size_y = max(y.bit_length(), 1)
        self.a = 1                # многочлен 1
        self.size_a = 1
        self.power = -1

    # 'Snosim' is here
    def align_to_p_size(self) -> int:
        """
        Сдвигает A влево, пока размер не сравняется с размером P.
        Возвращает количество выполненных сдвигов.
        """
        count = max(0, self.size_p - self.size_a)
        self.a     <<= count
        self.size_a += count
        return count

    def divide(self) -> None:
        if self.size_y > self.size_p:
            raise ValueError
        if self.y == 0:
            return
        self.power += 1
        while self.a != self.y:
            if self.size_a < self.size_p:
                self.a <<= 1
                self.size_a += 1
                self.power += 1
            else:
                self.a ^= self.p
                self.size_a = max(self.a.bit_length(), 1)

    def get_power(self) -> int:
        return self.power
