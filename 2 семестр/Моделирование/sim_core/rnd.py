from math import log, sqrt, exp
from random import random
from typing import Callable



# ------------------------------------------------------------
# Базовый равномерный генератор U(0,1)
# ------------------------------------------------------------
def uniform01() -> float:
    """Генерирует U ~ Uniform(0,1)."""
    return random()
# random.random() — генератор псевдослучайных чисел на основе MT19937.
# Это не формула, а алгоритм:
#   • внутреннее состояние — 624 32-битных слова
#   • переходы — линейный рекуррентный генератор над GF(2)
#   • период — 2**19937 − 1 (огромный)
#   • темперирование улучшает равномерность битов
#   • результат — 53-битный float в диапазоне [0.0, 1.0)
#
# То есть random.random() возвращает детерминированную последовательность
# с очень хорошими статистическими свойствами, но не криптостойкую.
#
# Это на порядок лучше простых формул из учебников (типа линейных конгруэнтных),
# и идеально подходит для имитационного моделирования (DES).


# ------------------------------------------------------------
# Равномерное распределение на [a, b]
# ------------------------------------------------------------
def uniform(a: float, b: float) -> float:
    """Генерирует X ~ Uniform(a, b)."""
    u = random()
    return a + (b - a) * u


# ------------------------------------------------------------
# Экспоненциальное распределение Exp(λ)
# ------------------------------------------------------------
def exponential(lmbd: float) -> float:
    """Генерирует τ ~ Exp(λ) по формуле τ = -ln(U)/λ."""
    u = random()
    return -log(u) / lmbd


# ------------------------------------------------------------
# Нормальное распределение N(0,1) — Box–Muller (полярный метод)
# ------------------------------------------------------------
def normal01() -> float:
    """Генерирует Z ~ N(0,1) методом Бокса–Мюллера (полярный)."""
    while True:
        v1 = 2.0 * random() - 1.0
        v2 = 2.0 * random() - 1.0
        s = v1 * v1 + v2 * v2
        if s == 0.0 or s >= 1.0:
            continue
        factor = sqrt(-2.0 * log(s) / s)
        return v1 * factor


# ------------------------------------------------------------
# Нормальное распределение N(μ, σ²)
# ------------------------------------------------------------
def normal(mu: float, sigma: float) -> float:
    """Генерирует X ~ Normal(mu, sigma^2)."""
    return mu + sigma * normal01()


# ------------------------------------------------------------
# Логнормальное распределение LogNormal(μ, σ)
# ------------------------------------------------------------
def lognormal(mu: float, sigma: float) -> float:
    """Генерирует X ~ LogNormal(mu, sigma)."""
    return exp(normal(mu, sigma))


# ------------------------------------------------------------
# CLT-генератор нормального распределения (приближённый)
# ------------------------------------------------------------
def normal01_clt() -> float:
    """
    Генерирует Z ~ N(0,1) через сумму 12 равномерных.
    Z = sum(U_i) - 6
    """
    s = sum(random() for _ in range(12))
    return s - 6.0



if __name__ == "__main__":
    import statistics

    N = 200_000  # число испытаний

    print("Проверяем uniform01()...")
    data = [uniform01() for _ in range(N)]
    print(f"  mean ~ 0.5:  {statistics.mean(data):.5f}")
    print(f"  var  ~ 1/12: {statistics.pvariance(data):.5f}")
    print(f"  min: {min(data):.5f}   max: {max(data):.5f}")
    print()

    print("Проверяем uniform(a,b)...")
    a, b = 5.0, 9.0
    data = [uniform(a, b) for _ in range(N)]
    print(f"  mean ~ (a+b)/2    ~ {(a+b)/2}:   {statistics.mean(data):.5f}")
    print(f"  var  ~ (b-a)^2/12 ~ {(b-a)**2/12:.3f}: {statistics.pvariance(data):.5f}")
    print(f"  min: {min(data):.5f}   max: {max(data):.5f}")
    print()

    print("Проверяем exponential(λ)...")
    lmbd = 2.0
    data = [exponential(lmbd) for _ in range(N)]
    print(f"  mean ~ τ   ~ 1/λ   ~ {lmbd**-1}:  {statistics.mean(data):.5f}")
    print(f"  var  ~ τ^2 ~ 1/λ^2 ~ {lmbd**-2}: {statistics.pvariance(data):.5f}")
    print(f"  min: {min(data):.5f}   max: {max(data):.5f}")
    print()

    print("Проверяем normal01() (Box–Muller)...")
    data = [normal01() for _ in range(N)]
    print(f"  mean ~ 0: {statistics.mean(data):.5f}")
    print(f"  var  ~ 1: {statistics.pvariance(data):.5f}")
    print(f"  min: {min(data):.5f}   max: {max(data):.5f}")
    print()

    print("Проверяем normal(μ, σ)...")
    mu, sigma = 10.0, 3.0
    data = [normal(mu, sigma) for _ in range(N)]
    print(f"  mean ~ μ   ~ {mu}: {statistics.mean(data):.5f}")
    print(f"  var  ~ σ^2 ~  {sigma**2}:  {statistics.pvariance(data):.5f}")
    print(f"  min: {min(data):.5f}   max: {max(data):.5f}")
    print()

    print("Проверяем lognormal(μ, σ)...")
    mu, sigma = 0.0, 0.25
    data = [lognormal(mu, sigma) for _ in range(N)]
    print(f"  mean ~ exp(μ + σ^2/2) ~ {exp(mu + sigma**2/2):.5f}: {statistics.mean(data):.5f}")
    print(f"  min: {min(data):.5f}   max: {max(data):.5f}")
    print()

    print("Проверяем normal01_clt()...")
    data = [normal01_clt() for _ in range(N)]
    print(f"  mean ~ 0: {statistics.mean(data):.5f}")
    print(f"  var  ~ 1: {statistics.pvariance(data):.5f}")
    print(f"  min: {min(data):.5f}   max: {max(data):.5f}")
    print()

    print("OK.")
