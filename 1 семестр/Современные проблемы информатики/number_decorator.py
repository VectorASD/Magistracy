from math import gcd, pi
from itertools import chain
from bisect import bisect

from misc import EPS, float_eq

class NumDecorator:
    def __init__(self):
        without_0 = tuple(chain(range(-32, 0), range(1, 33)))
        primes = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131)
        nums = (
            *((i, repr(i)) for i in range(-128, 129)),

            *((i / j, f"{i}/{j}") for i in without_0 for j in range(2, 33) if gcd(i, j) == 1),

            *((i / j ** 0.5, f"{i}/√{j}") for i in without_0 for j in primes),

            *((-i ** 0.5, f"-√{i}") for i in primes),
            *((i ** 0.5, f"√{i}") for i in primes),
            *((-i ** 0.5 / j, f"-√{i}/{j}") for i in primes for j in range(2, 33)),
            *((i ** 0.5 / j, f"√{i}/{j}") for i in primes for j in range(2, 33)),

            *((i * pi, f"{i}π") for i in without_0),
            *((i * pi / j, f"{i}π/{j}") for i in without_0 for j in range(2, 33) if gcd(i, j) == 1),

            *((i / (j * pi), f"{i}/{j}π") for i in without_0 for j in range(2, 33) if gcd(i, j) == 1),
        )

        # print(len(nums)) # 6826
        # print(len(set(i[0] for i in nums))) # 6819

        counter = {}
        for num, _str in nums:
            try: counter[num].append(_str)
            except KeyError: counter[num] = [_str]

        self.counter = counter
        self.nums = tuple(sorted(counter))
        self.strs = tuple(min(counter[num]) for num in self.nums)

    def repeats(self):
        for num, strs in self.counter.items():
            if len(strs) > 1: print(f"{num}: {strs}")
        """
        -4.123105625617661: ['-17/√17', '-√17']
        -3.3166247903554: ['-11/√11', '-√11']
        -2.23606797749979: ['-5/√5', '-√5']
        -0.30151134457776363: ['-1/√11', '-√11/11']
        -0.2773500981126146: ['-1/√13', '-√13/13']
        -0.24253562503633297: ['-1/√17', '-√17/17']
        -0.18569533817705186: ['-1/√29', '-√29/29']
        0.30151134457776363: ['1/√11', '√11/11']
        0.2773500981126146: ['1/√13', '√13/13']
        0.24253562503633297: ['1/√17', '√17/17']
        0.18569533817705186: ['1/√29', '√29/29']
        2.23606797749979: ['5/√5', '√5']
        3.3166247903554: ['11/√11', '√11']
        4.123105625617661: ['17/√17', '√17']
        """

    def get_idx(self, num):
        if type(num) not in (int, float): return

        num_arr = self.nums
        # for i in num_arr[:4]:
        #     print(i, bisect(num_arr, i - 0.01), bisect(num_arr, i), bisect(num_arr, i + 0.01))
        idx = bisect(num_arr, num)
        if idx == 0:
            if float_eq(num, num_arr[0]): return 0
        elif idx == len(num_arr):
            if float_eq(num, num_arr[-1]): return -1
        else:
            a = abs(num - num_arr[idx - 1])
            b = abs(num - num_arr[idx])
            if min(a, b) < EPS:
                if a < b: return idx - 1
                return idx

    def check(self, num):
        idx = self.get_idx(num)
        if idx is not None: return self.strs[idx]
        return str(num)

    def exists(self, *nums):
        return all(self.get_idx(num) is not None for num in nums)

    def test(self):
        for i in decorator.nums[:4]:
            print(self.check(i - EPS/2), self.check(i), self.check(i + EPS/2))
        for i in decorator.nums[-4:]:
            print(self.check(i - EPS/2), self.check(i), self.check(i + EPS/2))
        print(decorate_num(1/2**0.5)) # 1/√2
        print(exists_decor(1/2**0.5)) # True
        print(exists_decor(12345))    # False

decorator = NumDecorator()
decorate_num = decorator.check
exists_decor = decorator.exists

if __name__ == "__main__":
    decorator.repeats()
    decorator.test()

