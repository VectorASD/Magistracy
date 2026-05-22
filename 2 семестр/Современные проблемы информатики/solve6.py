import matplotlib.pyplot as plt  # pip install matplotlib

from math import sin, pi, sqrt
from random import uniform



def logspace(start, stop, num=50):
    """Возвращает список целых чисел, логарифмически распределённых
       от 10**start до 10**stop включительно, длиной num.
       Чтобы использовать np.logspace(2, 6, num=50, dtype=int) без numpy.
    """
    result = []
    for i in range(num):
        exponent = start + (stop - start) * i / (num - 1)
        value = int(10 ** exponent)
        result.append(value)
    return result

def buffon_trial(a, l):
    """Самый обычный метод отрабовки с двумя 'кси'."""
    phi = uniform(0, pi) # ξ₁
    x   = uniform(0, a)  # ξ₂
    return x <= l * sin(phi)

def buffon_simulation(N, a, l):
    """N бросков, возвращает P_exp и Δ."""
    hits = sum(buffon_trial(a, l) for _ in range(N))
    P_exp = hits / N
    P_theor = 2 * l / (a * pi)
    delta = abs(P_theor - P_exp) / P_theor
    return P_exp, delta

def main():
    # Отношение l/a задаётся преподавателем. Например, как на рисунке 2: l=1, a=2 -> l/a=0.5
    l = 1.0
    a = 2.0
    P_theor = 2 * l / (a * pi)

    # Массив значений N от 100 до 1_000_000 (логарифмическая шкала)
    N_values = logspace(2, 6, num=50)
    print("N space:", N_values)
    deltas = []

    for N in N_values:
        _, delta = buffon_simulation(N, a, l)
        deltas.append(delta)
        print(f"N = {N:7d}  Δ = {delta:.6f}")

    # График
    plt.figure(figsize=(10, 5))
    plt.plot(N_values, deltas, 'o-', markersize=3, label='Эксперимент')

    # Теоретическое убывание ~ 1/sqrt(N) (подгоним коэффициент по первой точке)
    k = deltas[0] * sqrt(N_values[0])
    theory = tuple(k / sqrt(N_values[i]) for i in range(len(N_values)))
    plt.plot(N_values, theory, 'r--', label=r'$\sim 1/\sqrt{N}$')

    plt.xscale('log')
    plt.yscale('log')
    plt.xlabel('Число бросков N')
    plt.ylabel('Нормированное отклонение Δ')
    plt.title(f'Задача Бюффона (l/a = {l/a:.1f}), теоретическая P = {P_theor:.4f}')
    plt.legend()
    plt.grid(True, which='both', ls='--')
    plt.tight_layout()
    plt.savefig('buffon_delta_vs_N.png', dpi=200)
    plt.show()



if __name__ == "__main__":
    main()
