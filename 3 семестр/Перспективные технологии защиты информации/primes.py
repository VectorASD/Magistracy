"""
Порт тестов простоты из OpenJDK BigInteger на Python.
Миллер-Рабин + Люка-Лемера + символ Якоби + битовое решето (BitSieve).
source: https://github.com/openjdk/jdk/blob/fffd0a53131784d571bd1d536778ebb7015b898c/src/java.base/share/classes/java/math/BigInteger.java#L1027
"""

from __future__ import annotations
from typing import Optional

from random import Random, SystemRandom


class BitSieve:
    """
    Сегментированное битовое решето Эратосфена для пред-фильтрации
    кандидатов (отсеивает делящиеся на малые простые до дорогого теста).

    Плотность простых падает с ростом битовой длины:
    ≈ 1/60 при 256 битах, ≈ 1/700 при 1024 битах.
    Проверять каждого случайного кандидата полным тестом prime_to_certainty
    дорого (modPow на big-int), поэтому решето сначала дешёво вычёркивает
    кратные малым простым (до 41), оставляя ~12% кандидатов на полный тест.

    source: https://github.com/openjdk/jdk/blob/15e1475a73444a9110537e3d171d44f71e226cb8/src/java.base/share/classes/java/math/BitSieve.java
    """
    # profiling: python -m cProfile -s cumulative test_primes.py 42

    small_sieve: Optional[BitSieve] = None

    def __init__(self, base: Optional[int] = None, search_len: Optional[int] = None):
        if base is None:
            # конструктор smallSieve
            self.length = 150 * 64
            self.bits = [0] * (BitSieve._unit_index(self.length - 1) + 1)

            self.set(0)
            next_index = 1
            next_prime = 3

            while True:
                self.sieve_single(self.length, next_index + next_prime, next_prime)
                next_index = self.sieve_search(self.length, next_index + 1)
                next_prime = 2 * next_index + 1
                if not (next_index > 0 and next_prime < self.length):
                    break
        else:
            if search_len is None:
                raise ValueError("search_len is required when base is specified")

            self.bits = [0] * (BitSieve._unit_index(search_len - 1) + 1)
            self.length = search_len
            start = 0

            step = BitSieve.small_sieve.sieve_search(BitSieve.small_sieve.length, start)
            converted_step = step * 2 + 1

            while True:
                start = base % converted_step
                start = converted_step - start
                if start % 2 == 0:
                    start += converted_step
                self.sieve_single(search_len, (start - 1) // 2, converted_step)

                step = BitSieve.small_sieve.sieve_search(
                    BitSieve.small_sieve.length, step + 1)
                converted_step = step * 2 + 1
                if not (step > 0):
                    break

    @staticmethod
    def _unit_index(bit_index: int) -> int:
        return bit_index >> 6

    @staticmethod
    def _bit(bit_index: int) -> int:
        return 1 << (bit_index & 63)

    def get(self, bit_index: int) -> bool:
        return (self.bits[BitSieve._unit_index(bit_index)] & BitSieve._bit(bit_index)) != 0

    def set(self, bit_index: int):
        self.bits[BitSieve._unit_index(bit_index)] |= BitSieve._bit(bit_index)

    def sieve_search(self, limit: int, start: int) -> int:
        if start >= limit:
            return -1
        b = self.bits
        for i in range(start, limit - 1):
            if not (b[i >> 6] & (1 << (i & 63))):
                return i
        return -1

    def sieve_single(self, limit: int, start: int, step: int):
        b = self.bits
        for i in range(start, limit, step):
            b[i >> 6] |= 1 << (i & 63)

    def retrieve(self, init_value: int, certainty: int, random: Random) -> Optional[int]:
        offset = 1
        for b in self.bits:
            next_long = 0xFFFFFFFFFFFFFFFF - b  # (~b) & 0xFFFFFFFFFFFFFFFF
            for _ in range(64):
                if next_long & 1:
                    candidate = init_value + offset
                    if prime_to_certainty(candidate, certainty, random):
                        return candidate
                next_long >>= 1
                offset += 2
        return None

BitSieve.small_sieve = BitSieve()


def _passes_miller_rabin(n: int, iterations: int, rnd: Random) -> bool:
    """
    Тест Миллера-Рабина (NIST FIPS 186-2).
    n — положительное нечётное > 2; iterations <= 50.
    """
    assert n > 2 and n & 1 and iterations <= 50, f"n = {n}, iterations = {iterations}"
    # Это приватный метод BigInteger.
    # Сам её факт уже заложен в функции, что используют этот метод

    n_minus_one = n - 1
    m = n_minus_one
    a = (m & -m).bit_length() - 1   # индекс младшего установленного бита
    m >>= a

    bit_len = n.bit_length()
    for _ in range(iterations):
        # случайное b в (1, n)
        b = rnd.randrange(2, n)

        j = 0
        z = pow(b, m, n)
        while not ((j == 0 and z == 1) or z == n_minus_one):
            if j > 0 and z == 1:
                return False
            j += 1
            if j == a:
                return False
            z = pow(z, 2, n)
    return True


def _lucas_lehmer_sequence(z: int, k: int, n: int) -> int:
    """Последовательность Люка U_k(1, (1-z)/4) mod n, по битам k."""
    d = z
    u = 1
    v = 1
    for i in range(k.bit_length() - 2, -1, -1):
        u2 = (u * v) % n
        v2 = (v * v + d * u * u) % n
        if v2 & 1:
            v2 -= n
        v2 >>= 1

        u, v = u2, v2
        if (k >> i) & 1:
            u2 = (u + v) % n
            if u2 & 1:
                u2 -= n
            u2 >>= 1
            v2 = (v + d * u) % n
            if v2 & 1:
                v2 -= n
            v2 >>= 1
            u, v = u2, v2
    return u


def jacobi_symbol(p: int, n: int) -> int:
    """Символ Якоби (p|n). n — положительное нечётное >= 3."""
    if p == 0:
        return 0

    j = 1
    u = n  # в Java берётся младшее слово mag; в Python хватает n

    if p < 0:
        p = -p
        n8 = u & 7
        if n8 == 3 or n8 == 7:
            j = -j

    # убираем степени двойки в p
    while (p & 3) == 0:
        p >>= 2
    if (p & 1) == 0:
        p >>= 1
        if ((u ^ (u >> 1)) & 2) != 0:
            j = -j
    if p == 1:
        return j

    # квадратичный закон взаимности
    if (p & u & 2) != 0:
        j = -j
    u = n % p

    while u != 0:
        while (u & 3) == 0:
            u >>= 2
        if (u & 1) == 0:
            u >>= 1
            if ((p ^ (p >> 1)) & 2) != 0:
                j = -j
        if u == 1:
            return j
        u, p = p, u
        if (u & p & 2) != 0:
            j = -j
        u %= p
    return 0


def _passes_lucas_lehmer(n: int) -> bool:
    """Тест Люка-Лемера. n — положительное нечётное."""
    n_plus_one = n + 1

    # d: 5, -7, 9, -11, ... пока (d|n) != -1
    d = 5
    while jacobi_symbol(d, n) != -1:
        d = abs(d) + 2 if d < 0 else -(d + 2)

    u = _lucas_lehmer_sequence(d, n_plus_one, n)
    return u % n == 0


def prime_to_certainty(n: int, certainty: int, rnd: Random) -> bool:
    """Вероятностный тест простоты. certainty — граница вероятности ошибки < 1/2^certainty."""
  # nn = (min(certainty, 2**31 - 2) + 1) // 2
    nn = (certainty + 1) // 2  # без защиты от переполнения, т.к. мы уже не в Java
    size_bits = n.bit_length()

    if size_bits < 100:
        rounds = min(50, nn)
        return _passes_miller_rabin(n, rounds, rnd)

    if size_bits < 256:
        rounds = 27
    elif size_bits < 512:
        rounds = 15
    elif size_bits < 768:
        rounds = 8
    elif size_bits < 1024:
        rounds = 4
    else:
        rounds = 2
    rounds = min(rounds, nn)

    return _passes_miller_rabin(n, rounds, rnd) and _passes_lucas_lehmer(n)


SMALL_PRIME_PRODUCT = 3 * 5 * 7 * 11 * 13 * 17 * 19 * 23 * 29 * 31 * 37 * 41

def small_prime(bit_length: int, certainty: int, rnd: Random) -> int:
    """Случайное простое ровно заданной битовой длины."""
    if bit_length < 2:
        raise ArithmeticError("bitLength < 2")

    mag_len = (bit_length + 31) >> 5
    high_bit = 1 << ((bit_length - 1) & 31)
    high_mask = ((high_bit << 1) - 1) & 0xFFFFFFFF

    while True:
        # случайный кандидат точной длины, старшее слово big-endian
        temp = [rnd.getrandbits(32) for _ in range(mag_len)]
        temp[0] = (temp[0] & high_mask) | high_bit
        if bit_length > 2:
            temp[mag_len - 1] |= 1

        candidate = 0
        for word in temp:
            candidate = (candidate << 32) | word

        # дешёвый pre-test на малые простые
        if bit_length > 6:
            r = candidate % SMALL_PRIME_PRODUCT
            if (r %  3 == 0 or r %  5 == 0 or r %  7 == 0 or r % 11 == 0 or
                r % 13 == 0 or r % 17 == 0 or r % 19 == 0 or r % 23 == 0 or
                r % 29 == 0 or r % 31 == 0 or r % 37 == 0 or r % 41 == 0):
                continue

        # для 2 и 3 бит все кандидаты простые
        if bit_length < 4:
            return candidate

        if prime_to_certainty(candidate, certainty, rnd):
            return candidate


PRIME_SEARCH_BIT_LENGTH_LIMIT = 500_000_000

def get_prime_search_len(bit_length: int) -> int:
    """Длина окна решета для поиска простого заданной битовой длины."""
    if bit_length > PRIME_SEARCH_BIT_LENGTH_LIMIT + 1:
        raise ArithmeticError("Prime search implementation restriction on bitLength")
    return bit_length // 20 * 64

def large_prime(bit_length: int, certainty: int, rnd: Random) -> int:
    """Случайное простое ≥ bitLength, аналог largePrime (через BitSieve)."""
    p = rnd.getrandbits(bit_length) | (1 << (bit_length - 1))
    p &= ~1  # чётная база

    search_len = get_prime_search_len(bit_length)
    search_sieve = BitSieve(p, search_len)
    candidate = search_sieve.retrieve(p, certainty, rnd)

    while candidate is None or candidate.bit_length() != bit_length:
        p = p + 2 * search_len
        if p.bit_length() != bit_length:
            p = rnd.getrandbits(bit_length) | (1 << (bit_length - 1))
        p &= ~1
        search_sieve = BitSieve(p, search_len)
        candidate = search_sieve.retrieve(p, certainty, rnd)

    return candidate


# Два основных метода: создать простое и проверить простое

SMALL_PRIME_THRESHOLD = 95
DEFAULT_PRIME_CERTAINTY = 100

def probable_prime(bit_length: int, rnd: Optional[Random] = None) -> int:
    """Аналог BigInteger.probablePrime: создаёт случайное простое заданной битовой длины."""
    if bit_length < 2:
        raise ArithmeticError("bitLength < 2")

    if rnd is None:
        rnd = SystemRandom()

    if bit_length < SMALL_PRIME_THRESHOLD:
        return small_prime(bit_length, DEFAULT_PRIME_CERTAINTY, rnd)
    return large_prime(bit_length, DEFAULT_PRIME_CERTAINTY, rnd)

def is_probable_prime(n: int, certainty: int, rnd: Optional[Random] = None) -> bool:
    """Аналог BigInteger.isProbablePrime: фильтрует 1, 2 и чётные."""
    if certainty <= 0:
        return True
    w = abs(n)
    if w == 2:
        return True
    if not (w & 1) or w == 1:
        return False
    if w.bit_length() > PRIME_SEARCH_BIT_LENGTH_LIMIT + 1:
        raise ArithmeticError("Primality test implementation restriction on bitLength")
    if rnd is None:
        rnd = SystemRandom()
    return prime_to_certainty(w, certainty, rnd)


def modpow_naive(base: int, exp: int, mod: int) -> int:
    """Бинарное возведение в степень. Деление (%) в hot loop."""
    result = 1
    base %= mod
    while exp:
        if exp & 1:
            result = result * base % mod
        exp >>= 1
        if exp:
            base = base * base % mod
    return result


from functools import cache

@cache
def _mont_params(mod: int) -> tuple[int, int, int, int, int]:
    """
    Montgomery-параметры для нечётного mod. Кэшируется @cache.

    Возвращает (k, mask, mp, r2, r1):
        k    — bit_length(mod)
        mask — R - 1, где R = 2^k
        mp   — -mod⁻¹ mod R
        r2   — R² mod mod (для входа в Montgomery-форму)
        r1   — R mod mod (представление 1)
    """
    assert mod & 1, "mod must be odd"
    k = mod.bit_length()
    R = 1 << k
    mask = R - 1

    inv = 1
    i = 1
    while i < k:
        inv = (inv * (2 - mod * inv)) & mask
        i <<= 1
    mp = (-inv) & mask

    return k, mask, mp, (R * R) % mod, R % mod

def _mont_table(a_m: int, mp: int, m: int, K: int, MASK: int,
                r1: int) -> list[int]:
    """
    Таблица a^0, a^1, ..., a^15 в Montgomery-форме.
    a_m — base в Montgomery-форме, r1 = 1 в Montgomery-форме.
    """
    table = [0] * 16
    table[0] = r1
    table[1] = a_m

    for i in range(2, 16):
        t = table[i - 1] * a_m
        u = (t * mp) & MASK
        v = (t + u * m) >> K
        if v >= m:
            v -= m
        table[i] = v
    return table

def modpow_mont(base: int, exp: int, mod: int) -> int:
    """Montgomery + окно 4 + инлайн redc. mod — нечётный."""
    k, mask, mp, r2, r1 = _mont_params(mod)
    m, MASK, K = mod, mask, k

    # Вход в Montgomery-форму: redc(base · R²), без % mod
    t = base * r2
    u = (t * mp) & MASK
    a_m = (t + u * m) >> K
    if a_m >= m:
        a_m -= m

    # Таблица a^0..a^15
    table = _mont_table(a_m, mp, m, K, MASK, r1)

    # Экспонента MSB → LSB, окно 4
    r_m = r1
    nbits = exp.bit_length()
    i = nbits - 1

    # Первое окно (может быть неполным)
    w_first = min(4, nbits)
    wval = (exp >> (nbits - w_first)) & ((1 << w_first) - 1)
    if wval:
        r_m = table[wval]
    i -= w_first

    while i >= 0:
        w = min(4, i + 1)
        # w квадратов
        for _ in range(w):
            t = r_m * r_m
            u = (t * mp) & MASK
            r_m = (t + u * m) >> K
            if r_m >= m:
                r_m -= m
        wval = (exp >> (i - w + 1)) & ((1 << w) - 1)
        if wval:
            t = r_m * table[wval]
            u = (t * mp) & MASK
            r_m = (t + u * m) >> K
            if r_m >= m:
                r_m -= m
        i -= w

    # Выход из Montgomery-формы
    t = r_m
    u = (t * mp) & MASK
    r = (t + u * m) >> K
    if r >= m:
        r -= m
    return r

# pow = modpow_naive    # 9.246 -> 12.085
# pow = modpow_mont     # 9.246 -> 15.647
try:
    import gmpy2
    pow = gmpy2.powmod  # 9.246 -> 0.883
except ImportError:
    print("Советую использовать:")
    print("    pip install -r requirements.txt")


def test_bit_sieve():
    """
    BitSieve — приватный класс OpenJDK, прямых тестов на него нет.
    Проверяем здесь: решето не должно вычёркивать простые.
    """
    rnd = Random(42)
    base = 10**10
    search_len = 500

    sieve = BitSieve(base, search_len)

    # retrieve находит первый простой кандидат в окне
    candidate = sieve.retrieve(base, 100, rnd)
    assert candidate is not None, "BitSieve не нашёл кандидата"
    assert prime_to_certainty(candidate, 100, rnd), \
        f"BitSieve вернул составное: {candidate}"

    # Подбираем все простые в окне через Миллера-Рабина
    known_primes = []
    n = base + 1
    while n < base + 2 * search_len:
        if prime_to_certainty(n, 100, rnd):
            known_primes.append(n)
        n += 2
    assert known_primes, "Не нашли простых в окне — странно"
    print("Окно проверки:", known_primes)

    # Простые из окна НЕ должны быть вычеркнуты
    for p in known_primes:
        idx = (p - base - 1) // 2
        assert not sieve.get(idx), \
            f"Простое {p} ошибочно вычеркнуто"

    # Кратные малым простым из smallSieve ДОЛЖНЫ быть вычеркнуты
    # (перебираем smallSieve и проверяем, что первое кратное в окне помечено)
    for step in (3, 5, 7, 11, 13, 17, 19, 23, 29, 31):
        # первое кратное step, попадающее в окно [base, base + 2*search_len)
        n = ((base + step - 1) // step) * step
        if n % 2 == 0:
            n += step
        # проверяем только если step*step > base — иначе "первое кратное" может
        # быть самим step, что вычёркивается по контракту smallSieve
        if n < base + 2 * search_len and n > step:
            idx = (n - base - 1) // 2
            assert sieve.get(idx), f"Составное {n} (кратное {step}) не вычеркнуто"
    print("Окно проверки прошло проверку ситом!")

if __name__ == "__main__":
    rnd = Random(42)
    # result = [i for i in range(3, 100002, 2) if prime_to_certainty(i, DEFAULT_PRIME_CERTAINTY, rnd)]
    # print(result)
    # test_bit_sieve()

    result = probable_prime(4096, rnd)
    print("result:", result)
    print("ok:", int(str(result)[:64]) == 8608717241103186576904464565704677713537310014280151622151739693)


# profiling: python -m cProfile -s cumulative primes.py
#
#    ncalls  tottime  percall  cumtime  percall filename:lineno(function)
#         1    0.000    0.000    9.605    9.605 primes.py:1(<module>)
# решето:
#         2    0.004    0.002    0.016    0.008 primes.py:30(__init__)
#      3358    0.008    0.000    0.008    0.000 primes.py:93(sieve_single)
#      3359    0.003    0.000    0.003    0.000 primes.py:84(sieve_search)
#         1    0.000    0.000    9.586    9.586 primes.py:98(retrieve)
# основная проверка:
#        58    0.000    0.000    9.586    0.165 primes.py:229(prime_to_certainty)
#        58    0.001    0.000    9.246    0.159 primes.py:114(_passes_miller_rabin)
#         1    0.000    0.000    0.340    0.340 primes.py:216(_passes_lucas_lehmer)
#       116    9.245    0.080    9.245    0.080 {built-in method builtins.pow}
#
# Как мы видим, загрузка решета тратит всего 0.016+0.008+0.003 = 0.027 (cumtime) на инициализацию
# и 0.000 (tottime) на работу retrieve, всё остальное поглащается prime_to_certainty.
# _passes_lucas_lehmer тратит 0.340 (cumtime), но не трогает pow
# _passes_miller_rabin тритат 9.246 (cumtime), но по 9.245 (tottime) pow видно, кто виновник
#
# 9.246 / 9.605 = 96.2%  (pow)
# 0.340 / 9.605 =  3.5% (_passes_lucas_lehmer)
# 0.027 / 9.605  = 0.3% (решето)
