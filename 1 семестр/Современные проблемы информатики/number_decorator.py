from math import gcd, pi
from itertools import chain
from bisect import bisect

from misc import EPS, float_eq

class NumDecorator:
    def __init__(self):
        without_0 = tuple(chain(range(-32, 0), range(1, 33)))
        primes = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131)
        nums = (
            ( 0.5,  "0.5"), (-0.5, "-0.5"), # вместо 1/2 и -1/2

            *((i, repr(i)) for i in range(-128, 129)),

            *((i / j, f"{i}/{j}") for i in without_0 for j in range(2, 33) if gcd(i, j) == 1),

            *((i / j ** 0.5, f"{i}/√{j}") for i in without_0 for j in primes),

            *((-i ** 0.5, f"-√{i}") for i in primes),
            *(( i ** 0.5,  f"√{i}") for i in primes),
            *((-i ** 0.5 / j, f"-√{i}/{j}") for i in primes for j in range(2, 33)),
            *(( i ** 0.5 / j,  f"√{i}/{j}") for i in primes for j in range(2, 33)),

            *((i * pi,     f"{i}π")     for i in without_0),
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
            if len(strs) > 1: print(f"{num:.9f}: {strs}")
        """
        -4.123105626: ['-17/√17', '-√17']
        -3.316624790: ['-11/√11', '-√11']
        -2.236067977: ['-5/√5', '-√5']
        -0.301511345: ['-1/√11', '-√11/11']
        -0.277350098: ['-1/√13', '-√13/13']
        -0.242535625: ['-1/√17', '-√17/17']
        -0.185695338: ['-1/√29', '-√29/29']
        0.301511345: ['1/√11', '√11/11']
        0.277350098: ['1/√13', '√13/13']
        0.242535625: ['1/√17', '√17/17']
        0.185695338: ['1/√29', '√29/29']
        2.236067977: ['5/√5', '√5']
        3.316624790: ['11/√11', '√11']
        4.123105626: ['17/√17', '√17']
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

    def check(self, num, rounding = None):
        if type(num) is complex:
            if float_eq(num.imag, 0): return self.check(num.real, rounding)

            sign = num.imag < 0

            im = abs(num.imag)
            imag = self.check(im, rounding)
            imag = '' if float_eq(im, 1) else f" {imag}"
            if float_eq(num.real, 0): return f"{'-' if sign else ''}i{imag}"

            real = self.check(num.real, rounding)
            return f"{real} {'-' if sign else '+'}i{imag}"

        idx = self.get_idx(num)
        if idx is not None: return self.strs[idx]
        if rounding is not None: return str(round(num, rounding))
        return str(num)

    def exists(self, *nums):
        return all((
            self.get_idx(num)      is not None   if type(num) is not complex else
            # self.get_idx(num.real) is not None   if float_eq(num.imag, 0) else
            # self.get_idx(num.imag) is not None   if float_eq(num.real, 0) else
            self.get_idx(num.real) is not None and self.get_idx(num.imag) is not None
        ) for num in nums)

    def test(self):
        self.repeats()
        print()

        for i in decorator.nums[:4]:
            print(self.check(i - EPS/2), self.check(i), self.check(i + EPS/2))
        for i in decorator.nums[-4:]:
            print(self.check(i - EPS/2), self.check(i), self.check(i + EPS/2))
        print()

        print(decorate_num(1/2**0.5)) # 1/√2
        print(exists_decor(1/2**0.5)) # True
        print(exists_decor(12345))    # False
        print(decorate_num(complex(123,    1/2**0.5))) # 123 +i 1/√2
        print(decorate_num(complex(123,   -1/2**0.5))) # 123 -i 1/√2
        print(decorate_num(complex(EPS/2,  1/2**0.5))) # i 1/√2
        print(decorate_num(complex(EPS/2, -1/2**0.5))) # -i 1/√2
        print(decorate_num(complex( 1/2**0.5, EPS/2))) # 1/√2
        print(decorate_num(complex(-1/2**0.5, EPS/2))) # -1/√2
        print(decorate_num(complex(EPS/2,      1)))    # i
        print(decorate_num(complex(EPS/2,     -1)))    # -i

decorator = NumDecorator()
decorate_num = decorator.check
exists_decor = decorator.exists

if __name__ == "__main__":
    decorator.test()

