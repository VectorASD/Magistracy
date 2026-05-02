import numpy as np  # pip install numpy

from bitmap_driver import read_bmp

import zipfile
import os



def safe_argmax_interval(hist, left, right):
    "Используется в шаге 3, т.к. в шаге 2 могут появиться нули друг за дружкой, что сделают интервалы пустыми"
    if right - left <= 1:
        return None
    segment = hist[left+1:right]
    assert len(segment) >= 1, "Где-то выход за пределы массива?"
    local_idx = np.argmax(segment)
    return (left + 1) + local_idx

def top2_in_interval(hist, left, right):
    "Тот же самый safe_argmax_interval, но уже 2 элемента вместо одного"
    if right - left <= 2:
        return None, None
    segment = hist[left+1:right]
    assert len(segment) >= 2, "Где-то выход за пределы массива?"
    top1, top2 = np.argsort(segment)[-2:]  # два индекса максимальных значений справа
    assert top1 < top2
    return (left + 1 + top1, left + 1 + top2)  # индексы сегмента в индексы гистограммы

def pick_best(hist, x, y):
    "Для шага 5, учитывающий, что safe_argmax_interval и top2_in_interval могут выдать None"
    arr = tuple(i for i in (x, y) if i is not None)
    if not arr:  # оба = None
        return None
    return max(arr, key=lambda i: hist[i])



class HistogramShifting:
    def __init__(self):
        self.pix = None

    def load_gray_from_io(self, file):
        self.pix = read_bmp(file, to_gray=True)
        return self

    def load_gray_from_file(self, name):
        with open(name, "rb") as file:
            self.load_gray_from_io(file)
        return self

    def load_gray_from_zip(self, zip_name, name):
        with zipfile.ZipFile(zip_name, "r") as zip:
            with zip.open(name, "r") as file:
                self.load_gray_from_io(file)
        return self

    def insert(self):
        #   Step.1
        # hist, bin_edges = np.histogram(self.pix, bins=256, range=(0, 255)) # Тормозной варианта из-за вычислений bin_edges, что нам не нужен,
                                                                             # потому что RDH‑методы работают строго с целыми значениями яркости.
        hist = np.bincount(self.pix.flatten(), minlength=256)                # Прямой способ получить hist (сколько какой пиксель встречается раз).
        assert hist.shape == (256,)

        #   Step.2
        argsorted = np.argsort(hist)  # argsort - та же самая сортировка, но выдаёт индексы значений вместо самих значений
        assert argsorted.shape == (256,)
        b1, b2, b3 = argsorted[:3]
      # print(b1, b2, b3)  # 2 4 11

        #   Step.3
        a1 = safe_argmax_interval(hist, 0, b1)
        a3 = safe_argmax_interval(hist, b2, b3)
      # print(a1, a3)  # 1 10

        #   Step.4
        a12, a21 = top2_in_interval(hist, b1, b2)
        a23, a32 = top2_in_interval(hist, b2, b3)
      # print(a12, a21, "|", a23, a32)  # None None | 7 10

        #   Step.5
        p1 = pick_best(hist, a1, a12)
        p2 = pick_best(hist, a21, a23)
        p3 = pick_best(hist, a32, a3)
      # print("picks:", p1, p2, p3)  # 1 7 10



if __name__ == "__main__":
    HS = HistogramShifting().load_gray_from_zip(os.path.join("assets", "bossbase_containers.zip"), "205.bmp")
    HS.insert()
