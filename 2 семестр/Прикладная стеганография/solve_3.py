import numpy as np  # pip install numpy

from bitmap_driver import read_bmp, save_bmp

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
    top1, top2 = sorted(np.argsort(segment, kind="heap")[-2:])  # два индекса максимальных значений справа
    assert top1 < top2
    return (left + 1 + top1, left + 1 + top2)  # индексы сегмента в индексы гистограммы

def pick_best(hist, x, y):
    "Для шага 5, учитывающий, что safe_argmax_interval и top2_in_interval могут выдать None"
    arr = tuple(i for i in (x, y) if i is not None)
    if not arr:  # оба = None
        return None
    return max(arr, key=lambda i: hist[i])

def refine_peak(hist, peak, zero):
    "Для шага 6: уточнение пика внутри пары (peak, zero)"
    if peak is None:
        return  # нечего уточнять
    assert zero is not None

    left  = min(peak, zero)
    right = max(peak, zero)

    # Step.3 внутри пары
    a_local = safe_argmax_interval(hist, left, right)

    # Step.4 внутри пары
    aL, aR = top2_in_interval(hist, left, right)

    # Step.5 внутри пары
    return pick_best(hist, a_local, pick_best(hist, aL, aR))



def find_nearest_zero(hist, peak):
    zeros = np.where(hist == 0)[0]
    zeros = zeros[zeros != peak]  # исключаем сам peak, если вдруг hist[peak] == 0

    if zeros.size:
        # выбираем zero с минимальной дистанцией до peak
        idx = np.argmin(np.abs(zeros - peak))
        return int(zeros[idx])

    raise RuntimeError(f"Плохая гистограмма: {hist}, peak={peak}")



class HistogramShifting:
    def clear(self):
        self.pix = None
        self.hist = None
        self.pairs = None
        self.stego = None

    def __init__(self):
        self.clear()
        self.data = None

    def load_gray_from_io(self, file):
        self.clear()
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

    def load_data(self, path):
        with open(path, "rb") as file:
            self.data = file.read()
        self.stego = None
        return self

    def get_hist(self):
        # hist, bin_edges = np.histogram(self.pix, bins=256, range=(0, 255))  # Тормозной вариант из-за вычислений bin_edges, что нам не нужно,
                                                                              # потому что RDH‑методы работают строго с целыми значениями яркости
        if self.hist is None:
            self.hist = hist = np.bincount(self.pix.flatten(), minlength=256) # Прямой способ получить hist (сколько какой пиксель встречается раз)
            assert hist.shape == (256,)
            return hist
        return self.hist

    def Ni_et_al_2006(self):
        if self.pairs:
            return self.pairs

        #   Step.1
        hist = self.get_hist()

        #   Step.2
        argsorted = np.argsort(hist, kind="heap")  # argsort - та же самая сортировка, но выдаёт индексы значений вместо самих значений
        assert argsorted.shape == (256,)
        b1, b2, b3 = sorted(argsorted[:3])  # np.argsort(hist, kind="quicksort"), т.е. порядок не гарантируется b1 < b2 < b3, по этому и сортируем
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

        #   Step.6
        p1 = refine_peak(hist, p1, b1)
        p2 = refine_peak(hist, p2, b2)
        p3 = refine_peak(hist, p3, b3)
      # print(p1, p2, p3)  # None 6 None

        # В статье прямо указано:
        #    All of these three pairs are treated as cases of peak and zero points pairs.
        # Но не сказано, что все три пары обязаны иметь пики.
        # Если пара не содержит пика → она просто не участвует в embedding.

        #   Step.7 в учебнике хоть и нет такого пункта, т.к. не уточняются детали, но получать здесь None - нормально
        self.pairs = tuple((int(pick), int(zero)) for pick, zero in ((p1, b1), (p2, b2), (p3, b3)) if pick is not None)
        #   Тем более, мы можем получить сразу из всех трёх refine_peak значения None,
        #   тогда делаем fallback на однопиковый HS 2004 года.
        pairs = self.Ni_et_al_2004()

        for pick, zero in pairs:
            print(f"(p={pick}, b={zero})")

        return pairs

    def Ni_et_al_2004(self):
        if self.pairs:
            # если Ni_et_al_2006 дал не пустой self.pairs, тогда мы просто выйдем этим путём :)
            return self.pairs
        hist = self.get_hist()
        peak = int(np.argmax(hist))  # cast np.int64 to int
        zero = find_nearest_zero(hist, peak)
        self.pairs = pairs = (peak, zero),
        return pairs

    def get_capacity(self):
        hist = self.get_hist()
        pairs = self.Ni_et_al_2006()
        return sum(hist[peak] for peak, zero in pairs)

    def embedder(self):
        if self.stego is not None:
            return self.stego

        if self.pix is None:
            raise RuntimeError("Сначала загрузите изображение посредством любого метода load_gray_from_*")
        if self.data is None:
            raise RuntimeError("Сначала загрузите данные для встраивания посредством load_data")

        capacity_bits = self.get_capacity()  # триггерит фактическое выссчитывание self.hist и self.pairs
        capacity_bytes = capacity_bits // 8

      # print("capacity:", capacity_bytes, "b.") # 1197 b.
      # print("data:", len(self.data), "b.")     # 453541 b. (весь Философский Камень Гарри Поттера в кодировке windows-1251, т.е. все русские и английский буквы по байту)

        if len(self.data) < capacity_bytes:
            raise RuntimeError(f"Недостаточно данных: нужно минимум {capacity_bytes} байт, а загружено только {len(self.data)}")

        payload = self.data[:capacity_bytes]
        payload_bits = np.unpackbits(np.frombuffer(payload, dtype=np.uint8)).astype(np.uint8)
      # print(len(payload_bits), capacity_bits) # 9576 9576, шанс 1/8 увидеть одинаковые числа, а выпал :)

        bit_pos = 0
        total_bits = len(payload_bits)

        # Рабочая область, чтобы не было переполнений из-за np.uint8...
        work = self.pix.astype(np.int16, copy=True)

        for peak, zero in self.Ni_et_al_2006():
            if bit_pos >= total_bits:
                break

            # --- Сдвиг интервала ---
            if zero < peak:
                mask_shift = (work > zero) & (work < peak)
                work[mask_shift] -= 1
            else:
                mask_shift = (work < zero) & (work > peak)
                work[mask_shift] += 1

            # --- Встраивание битов в пиксели == peak ---
            mask_peak = (work == peak)
            idx = np.flatnonzero(mask_peak)
            n_avail = len(idx)
            if n_avail == 0:
                continue

            n_need = min(n_avail, total_bits - bit_pos)
            bits_chunk = payload_bits[bit_pos:bit_pos + n_need]

            ones_mask = bits_chunk == 1

            if zero < peak:
                work.flat[idx[ones_mask]] -= 1
            else:
                work.flat[idx[ones_mask]] += 1
            # work.flat - это вид (subview) на плоское представлением того же ndarray, только в 1D форме: (len(work),)

            bit_pos += n_need

        # Сохраняем stego-картинку под Lazy.
        # Иными словами, повторные вызовы метода embedder дадут уже self.stego напрямую,
        # пока не будет вызваны методы с side-эффектом на этот метод: load_gray_from_* или load_data
        self.stego = stego = work.astype(np.uint8)
        return stego

    def save_stego(self, path):
        stego = self.embedder()
        save_bmp(path, stego, mode="gray")
        return self



if __name__ == "__main__":
    zip_path = os.path.join("assets", "bossbase_containers.zip")
    data_path = os.path.join("assets", "Harry Potter and the Philosopher's Stone.txt")
    HS = HistogramShifting().load_gray_from_zip(zip_path, "205.bmp").load_data(data_path)
  # HS.Ni_et_al_2004()
  # HS.Ni_et_al_2006()
  # HS.get_capacity()
  # HS.embedder()
    HS.save_stego("205_HS.bmp")
