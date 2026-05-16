import random
from random import randint



# TSP - Traveling Salesman Problem - задача коммивояжёра

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



def main():
    dist = generate_tsp_instance(16)
    print_matrix(dist)



if __name__ == "__main__":
    main()
