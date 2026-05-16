import random
from random import randint
import itertools



# TSP - Traveling Salesman Problem - задача коммивояжёра (задача путешествующего торговца)

def generate_tsp_instance(n, max_dist=100, seed=None):
    if seed is not None:
        random.seed(seed)
    dist = [[0]*n for _ in range(n)]
    for i in range(n):
        for j in range(i+1, n):
            d = randint(1, max_dist)
            dist[i][j] = d
            dist[j][i] = d
    return dist

def print_matrix(dist):
    sizes = tuple(
        max(len(str(i)) for i in col)
        for col in zip(*dist))
    for row in dist:
        row = ' '.join(f"{col:{size}d}" for col, size in zip(row, sizes))
        print(f"| {row} |")



def tsp_bruteforce(dist, start_city=0):
    n = len(dist)
    cities = list(range(n))
    cities.remove(start_city)
    best_len = float("inf")
    best_path = None

    for perm in itertools.permutations(cities):  # генерирует все возможные перестановки
        path = (start_city, *perm, start_city)
        length = sum(dist[path[i]][path[i+1]] for i in range(n))
        if length < best_len:
            best_len = length
            best_path = path

    return best_len, best_path



def main():
    dist = generate_tsp_instance(8)
    print_matrix(dist)

    best_len, best_path = tsp_bruteforce(dist)
    print("best length:", best_len)
    print("path:", best_path)



if __name__ == "__main__":
    main()
