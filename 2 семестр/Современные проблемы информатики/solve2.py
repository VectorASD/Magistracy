import numpy as np # pip install numpy
import matplotlib.pyplot as plt  # pip install matplotlib

import random
from random import randint
import itertools
import time



# TSP - Traveling Salesman Problem - задача коммивояжёра (задача путешествующего торговца)

def generate_tsp_instance(n, max_dist=100, seed=None):
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    dist = np.random.randint(1, max_dist + 1, size=(n, n), dtype=np.int32)
    dist = (dist + dist.T) // 2
    np.fill_diagonal(dist, 0)

    return dist

def print_matrix(dist):
    sizes = tuple(
        max(len(str(i)) for i in col)
        for col in zip(*dist))
    for row in dist:
        row = ' '.join(f"{col:{size}d}" for col, size in zip(row, sizes))
        print(f"| {row} |")



# Простой перебор всех перестановок, что гарантирует
# идеальный результат, но имеет сложность: O(n!)
def tsp_bruteforce(dist, start_city=0):
    n = len(dist)
    cities = list(range(n))
    cities.remove(start_city)
    best_len = float("inf")
    best_path = None

    path = np.empty(n + 1, dtype=np.int32)
    path[0] = path[-1] = start_city

    for perm in itertools.permutations(cities):  # генерирует все возможные перестановки
        path[1:-1] = perm
        length = dist[path[:-1], path[1:]].sum()  # векторизовано
        if length < best_len:
            best_len = length
            best_path = path.copy()

    return best_len, best_path


# Метод динамического программирования (Хелда–Карпа)
# Сложность алгоритма O(n^2 * 2^n), что уже лучше, чем O(n!)
def tsp_dynamic_programming(dist, start=0):
    n = len(dist)
    INF = 10**9
    # dp[mask][i] – длина кратчайшего пути, начинающегося в start,
    # проходящего через города маски (биты, кроме start) и заканчивающегося в i
    dp = np.full((1 << n, n), INF, dtype=np.int64)
    dp[1 << start][start] = 0

    # Заполняем DP
    for mask in range(1 << n):
        # работаем только с масками, где start уже есть
        if not (mask & (1 << start)):
            continue
        for last in range(n):
            if dp[mask][last] == INF:
                continue
            # пытаемся добавить город nxt, не входящий в mask
            for nxt in range(n):
                if mask & (1 << nxt):
                    continue
                new_mask = mask | (1 << nxt)
                new_len = dp[mask][last] + dist[last][nxt]
                if new_len < dp[new_mask][nxt]:
                    dp[new_mask][nxt] = new_len

    # Замыкаем цикл: добавляем возврат в start
    full_mask = (1 << n) - 1
    best_len = INF
    best_last = -1
    for last in range(n):
        if last == start:
            continue
        total = dp[full_mask][last] + dist[last][start]
        if total < best_len:
            best_len = total
            best_last = last

    # Восстанавливаем оптимальный путь (обратный ход)
    path = [start]  # end
    mask = full_mask
    last = best_last
    while mask != (1 << start):
        path.append(last)
        # ищем, из какого города мы пришли в last
        prev_mask = mask ^ (1 << last)
        prev = -1
        for cand in range(n):
            if dp[prev_mask][cand] + dist[cand][last] == dp[mask][last]:
                prev = cand
                break
        mask = prev_mask
        last = prev
    path.append(start)
  # path.reverse()   # имело бы смысл, если бы был другой конец, отличный от start

    return best_len, np.array(path)



"""
1. Что используется в реальных навигационных системах?

Чистый TSP с обязательным возвращением в точку старта нужен не всегда. Например:
    В такси/каршеринге пассажир сам задаёт порядок точек, поэтому задача сводится к построению кратчайшего
        пути по фиксированной последовательности (алгоритм Дейкстры/А*). TSP там не нужен.
    В курьерских приложениях (например, доставка нескольких заказов) курьеру нужно посетить все адреса,
        но возврат в исходную точку (склад/ресторан) часто не требуется в конце маршрута — это задача поиска
        кратчайшего гамильтонова пути (без замыкания цикла). Она чуть проще TSP, но всё равно NP-трудна.

Когда же точек действительно много (десятки или сотни) и порядок не задан, используют эвристические и
метаэвристические алгоритмы, которые находят близкое к оптимальному решение за приемлемое время.
Среди них:
    Муравьиный алгоритм (Ant Colony Optimization) — да, я угадал, он очень популярен, потому что
        хорошо масштабируется и может работать в реальном времени, особенно для динамических задач (пробки, новые заказы).
    Генетический алгоритм — тоже часто применяется.
    Метод имитации отжига (Simulated Annealing).
    Локальный поиск с техниками 2-opt, 3-opt, Lin–Kernighan (алгоритм LKH — один из лучших на практике).

Для точного решения больших TSP (вплоть до десятков тысяч городов) существуют мощные исследовательские пакеты вроде Concorde,
основанные на продвинутых методах ветвей и границ, но они не встроены в обычные навигаторы.

В реальных GPS-навигаторах (Google Maps, OsmAnd) построение оптимального маршрута с несколькими остановками
обычно реализовано через приближённые алгоритмы, часто с применением жадных конструктивных эвристик
(например, «к ближайшему» с последующей оптимизацией 2-opt), так как время ответа критично.


2. Где в жизни встречается задача коммивояжёра?
Несмотря на кажущуюся академичность, прикладных областей масса:
    Логистика и транспорт: планирование маршрутов развозных фургонов, почтовых машин,
        инкассаторов, школьных автобусов. Здесь часто нужно вернуться на базу — чистый TSP.
    Складская логистика: сбор заказов (order picking) — работник склада должен обойти ячейки со всеми
        товарами заказа и вернуться в зону упаковки. Это в точности задача коммивояжёра в помещении.
    Производство электроники: сверление отверстий в печатных платах, пайка компонентов — порядок обработки
        точек (отверстий/мест пайки) должен минимизировать холостой ход станка.
    Роботизированная сварка: робот должен произвести сварные швы в разных
        точках кузова автомобиля и вернуться в исходное положение.
    Биоинформатика: секвенирование ДНК (сборка генома) использует вариации TSP.
    Туризм: приложения для планирования путешествий (все достопримечательности за минимальное время).
    Астрономия: планирование наблюдений телескопов (посетить нужные участки неба с наименьшим перемещением).

В большинстве реальных случаев решается обобщённая задача коммивояжёра (с ограничениями по времени,
вместимости, окнам доставки — Vehicle Routing Problem), но ядром остаётся TSP.
"""



def main():
    for _ in range(100):
        dist = generate_tsp_instance(4)
        print(dist)

        best_len, best_path = tsp_bruteforce(dist)
        print("best length:", best_len)
        print("path:", best_path)

        best_len, best_path = tsp_dynamic_programming(dist)
        print("best length:", best_len)
        print("path:", best_path)

        print()

def benchmark():
    ns_brute = tuple(range(4, 11))
    ns_dp    = tuple(range(4, 17))
    times_brute = []
    times_dp = []
    ratios = []

    for n in ns_dp:
        dist = generate_tsp_instance(n)

        t0 = time.perf_counter()
        tsp_dynamic_programming(dist)
        t1 = time.perf_counter()
        t_dp = t1 - t0
        times_dp.append(t_dp)

        if n in ns_brute:
            t0 = time.perf_counter()
            tsp_bruteforce(dist)
            t1 = time.perf_counter()
            t_brute = t1 - t0

            times_brute.append(t_brute)
            ratios.append(t_brute / t_dp if t_dp > 0 else 0)

            print(f"n={n:2d} | brute={t_brute:.4f}s | dp={t_dp:.4f}s | ratio={ratios[-1]:.1f}")
        else:
            print(f"n={n:2d} | dp={t_dp:.4f}s ")

    plt.figure(figsize=(6*2, 4*2))

    for i in range(2):
        # График 1-2: время выполнения
        plt.subplot(2, 2, 1+i)
        plt.plot(ns_brute, times_brute, 'o-', label='Полный перебор')
        plt.plot(ns_dp,    times_dp,    's-', label='Дин. программирование')
        if i:
            plt.yscale('log')
        plt.xlabel('Число городов')
        plt.ylabel('Время, с (лог. шкала)' if i else 'Время, с')
        plt.title('Время выполнения')
        plt.legend()
        plt.grid(True)

    # График 3: отношение времён
    plt.subplot(2, 2, 3)
    plt.plot(ns_brute, ratios, 'D-', color='green')
    plt.xlabel('Число городов')
    plt.ylabel('T_brute / T_dp')
    plt.title('Отношение времени')
    plt.grid(True)

    plt.tight_layout()
    plt.savefig('tsp_benchmark.png', dpi=200)   # сохраняем для отчёта
    plt.show()

"""
Маркеры:
    o — круг, s — квадрат, D — ромб, d — тонкий ромб
    ^ v < > — треугольники (вверх/вниз/влево/вправо)
    * — звезда, p — пятиугольник, h — шестиугольник
    + — плюс, x — крест, X — жирный крест
    . — точка, , — пиксель (совсем маленькая точка)
    1 2 3 4 — трезубцы в разные стороны
Линии:
    -  — сплошная
    -- — пунктирная
    -. — штрих-пунктир
    :  — точечная
Цвет (опционально, третьим символом):
    r g b c m y k w   ('b'=blue уже занят, по тому black='k')

time.perf_counter — высокоточный монотонный счётчик (наносекунды), не привязан
    к системному времени, не может прыгнуть назад или вперёд из-за NTP/DST.
    Используется для измерения коротких интервалов выполнения кода.
time.time — системные часы (секунды с Unix epoch), может скакнуть при синхронизации
    времени. Используется когда нужна реальная дата/время, а не просто интервал.
Для бенчмарков — всегда perf_counter.
"""



if __name__ == "__main__":
  # main()
    benchmark()
