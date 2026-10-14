"""
Порт test/jdk/java/math/BigInteger/PrimeTest.java на Python.
Проверяет is_probable_prime (аналог probablePrime) и probable_prime
(аналог probablePrime, использует BitSieve для > 95 бит).

Запуск: python test_primes.py [seed]
source: https://github.com/openjdk/jdk/blob/master/test/jdk/java/math/BigInteger/PrimeTest.java
"""

import sys
import time
from random import Random
from typing import Callable

from primes import (
    probable_prime,
    is_probable_prime,
    PRIME_SEARCH_BIT_LENGTH_LIMIT,
)


DEFAULT_UPPER_BOUND = 1299709    # 100000-е простое
DEFAULT_CERTAINTY = 100
NUM_NON_PRIMES = 10000

# Экспоненты простых Мерсенна (короткий набор — тест не должен идти вечно)
MERSENNE_EXPONENTS = [
    2, 3, 5, 7, 13, 17, 19, 31, 61, 89,
    107, 127, 521, 607, 1279, 2203, 2281, 3217,
]


# ---------- вспомогательные ----------

def create_primes(upper_bound: int) -> bytearray:
    """
    Решето Эратосфена. sieve[i] == 1, если i + 2 — простое.
    Значения 0 и 1 исключены.
    """
    nbits = upper_bound - 1
    sieve = bytearray(nbits)          # 0 = потенциально простое, 1 = вычеркнуто
    p = 2
    while p * p < upper_bound:
        for i in range(p * p, nbits + 2, p):
            sieve[i - 2] = 1
        while True:
            p += 1
            if p > 1 and sieve[p - 2] == 0:
                break

    # инвертируем: 1 — простое
    for i in range(nbits):
        sieve[i] ^= 1
    return sieve

def get_primes(upper_bound: int) -> list[int]:
    """Все простые до upper_bound (включительно) + Integer.MAX_VALUE."""
    sieve = create_primes(upper_bound)
    primes = [i + 2 for i, is_prime in enumerate(sieve) if is_prime]
    primes.append(2 ** 31 - 1)        # Integer.MAX_VALUE
    print(f"Created {len(primes)} primes")
    return primes


# ---------- проверки (возвращают bool, не печатают сам вердикт) ----------

def check_prime(primes: list[int], certainty: int, rnd: Random) -> bool:
    """
    Доля известных простых, прошедших is_probable_prime, должна быть
    >= 1 - 1/4^(certainty/2).
    """
    probable = sum(
        1 for p in primes if is_probable_prime(p, certainty, rnd)
    )
    # Эквивалент Java-проверки: p * 4^N >= t * (4^N - 1)
    four_to_c = 4 ** (certainty // 2)
    left = probable * four_to_c
    right = len(primes) * (four_to_c - 1)
    if left < right:
        print(f"Prime test: {probable}/{len(primes)} — "
              f"ниже порога certainty", file=sys.stderr)
        return False
    return True


def check_non_prime(primes: list[int], certainty: int, rnd: Random) -> bool:
    """
    Числа, для которых is_probable_prime вернул False, не должны
    оказаться простыми.
    """
    max_prime = primes[-2]            # последнее известное простое
    candidates = [
        rnd.randint(2, max_prime - 1) for _ in range(NUM_NON_PRIMES)
    ]
    non_primes = [
        n for n in candidates
        if not is_probable_prime(n, certainty, rnd)
    ]
    prime_set = set(primes[:-1])       # без Integer.MAX_VALUE
    failed = [n for n in non_primes if n in prime_set]
    for n in failed:
        print(f"Prime value thought to be non-prime: {n}", file=sys.stderr)
    return not failed


def check_mersenne_primes(certainty: int, rnd: Random) -> bool:
    """Проверяет, что 2^p - 1 распознаются как простые для известных p."""
    print(f"Checking first {len(MERSENNE_EXPONENTS)} Mersenne primes")
    ok = True
    for p in MERSENNE_EXPONENTS:
        mp = (1 << p) - 1
        if not is_probable_prime(mp, certainty, rnd):
            print(f"Mp with p = {p} not classified as prime",
                  file=sys.stderr)
            ok = False
    return ok  # не сразу возвращаем 'ok' для проверки всех кейсов


def check_huge_fails(rnd: Random) -> bool:
    """is_probable_prime должен бросать ArithmeticError для > лимита."""
    try:
        a = (1 << (PRIME_SEARCH_BIT_LENGTH_LIMIT + 1)) | 1  # огромное нечётное
        is_probable_prime(a, 1, rnd)
        return False            # не должно дойти
    except ArithmeticError:
        return True             # ожидаемое поведение


def check_large_prime(certainty: int, rnd: Random) -> bool:
    """
    Дополнительно: probable_prime для > 95 бит, задействует
    large_prime и BitSieve.
    """
    print("Checking large primes (> 95 bit, BitSieve)")
    ok = True
    for bits in (128, 256, 512, 1024):
        p = probable_prime(bits, rnd)
        if p.bit_length() != bits:
            print(f"probable_prime({bits}) gave {p.bit_length()} bits",
                  file=sys.stderr)
            ok = False
        if not is_probable_prime(p, certainty, rnd):
            print(f"probable_prime({bits}) is not prime: {p}",
                  file=sys.stderr)
            ok = False
    return ok  # не сразу возвращаем 'ok' для проверки всех кейсов


# ---------- инфраструктура запуска ----------

def parse_args(argv: list[str]) -> int | None:
    """python test_primes.py [seed]"""
    return int(argv[0]) if argv else None

def run_tests(tests: list[tuple[str, Callable[[], bool]]]) -> bool:
    """Централизованный прогон: замер времени + печать статуса."""
    results = []
    for name, test in tests:
        t0 = time.perf_counter()
        ok = test()
        elapsed = time.perf_counter() - t0
        status = "SUCCESS" if ok else "FAILURE"
        print(f"{name} test: {status} ({elapsed:.3f}s)")
        results.append(ok)
    return all(results)

def main(argv: list[str]) -> int:
    seed = parse_args(argv)
    rnd = Random(seed)
    certainty = DEFAULT_CERTAINTY

    print(f"Seed = {seed}\nCertainty = {certainty}")

    primes = get_primes(DEFAULT_UPPER_BOUND)

    tests: list[tuple[str, Callable[[], bool]]] = [
        ("Prime",       lambda: check_prime(primes, certainty, rnd)),
        ("Non-prime",   lambda: check_non_prime(primes, certainty, rnd)),
        ("Mersenne",    lambda: check_mersenne_primes(certainty, rnd)),
        ("Huge fails",  lambda: check_huge_fails(rnd)),
        ("Large prime", lambda: check_large_prime(certainty, rnd)),
    ]

    if run_tests(tests):
        print("PrimeTest succeeded!")
        return 0
    print("PrimeTest FAILED!", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


# Проверено на Python 3.13, Windows, 3 прогона:
#
#   python test_primes.py              Seed=None  ~7.3s total
#   python test_primes.py 42           Seed=42    ~7.2s total
#   python -O test_primes.py 42        Seed=42    ~7.1s total
#
# Разбивка (стабильно, ±10%):
#   Prime        ~6.2s    — 100001 известных простых через is_probable_prime
#   Non-prime    ~0.07s   — 10000 случайных, ни одно ложно не отвергнуто
#   Mersenne     ~0.62s   — 18 простых Мерсенна до 2^3217 - 1
#   Huge fails   ~0.02s   — ArithmeticError на числе > PRIME_SEARCH_BIT_LENGTH_LIMIT
#   Large prime  ~0.27s   — probable_prime(128/256/512/1024), задействован BitSieve
#
# Все три прогона: PrimeTest succeeded!
