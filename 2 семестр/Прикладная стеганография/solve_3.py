import numpy as np  # pip install numpy

from bitmap_driver import read_bmp, save_bmp

import zipfile
import os



def safe_argmax_interval(hist, left, right, rng):
    "Используется в шаге 3, т.к. в шаге 2 могут появиться нули друг за дружкой, что сделают интервалы пустыми"
    if right - left <= 1:
        return None
    segment = hist[left+1:right]
    assert segment.size >= 1, "Где-то выход за пределы массива?"
    local_idx = stable_argmax(segment, rng)
    return (left + 1) + local_idx

def top2_in_interval(hist, left, right, rng):
    "Тот же самый safe_argmax_interval, но уже 2 элемента вместо одного"
    if right - left <= 2:
        return None, None
    segment = hist[left+1:right]
    assert segment.size >= 2, "Где-то выход за пределы массива?"
    top1, top2 = sorted(stable_argsort(segment, 2, rng, min=False))  # два индекса максимальных значений справа
    return (left + 1 + top1, left + 1 + top2)  # индексы сегмента в индексы гистограммы

def pick_best(hist, x, y):
    "Для шага 5, учитывающий, что safe_argmax_interval и top2_in_interval могут выдать None"
    arr = tuple(i for i in (x, y) if i is not None)
    if not arr:  # оба = None
        return None
    return max(arr, key=lambda i: hist[i])

def refine_peak(hist, peak, zero, rng):
    "Для шага 6: уточнение пика внутри пары (peak, zero)"
    if peak is None:
        return  # нечего уточнять
    assert zero is not None

    left  = min(peak, zero)
    right = max(peak, zero)

    # Step.3 внутри пары
    a_local = safe_argmax_interval(hist, left, right, rng)

    # Step.4 внутри пары
    aL, aR = top2_in_interval(hist, left, right, rng)

    # Step.5 внутри пары
    b = pick_best(hist, a_local, pick_best(hist, aL, aR))
    if b is not None and not hist[b]:
        b = None  # чтобы peak не встал на нулевое значение
    return b



def find_nearest_zero(hist, peak, rng):
    zeros = np.where(hist == 0)[0]
    zeros = zeros[zeros != peak]  # исключаем сам peak, если вдруг hist[peak] == 0

    if zeros.size:
        # выбираем zero с минимальной дистанцией до peak
        idx = stable_argmin(np.abs(zeros - peak), rng)
        return int(zeros[idx])

    raise RuntimeError(f"Плохая гистограмма: {hist}, peak={peak}")



def stable_argsort(arr, count, rng, min=True):
    assert count <= arr.size
    indexes = np.argsort(arr)
    assert indexes.shape == (arr.size,)

    base = indexes[:count] if min else indexes[-count:]
    vals = arr[base]                # Все минимумы, что подходят в кандидаты
    mask = np.isin(arr, vals)       # Набор нулей и единиц по нужным индексам
    candidates = np.where(mask)[0]  # Превращается в сами индексы

    # rng.shuffle(candidates)
    # return candidates[:count]  # после shuffle не важно, что мы выберем
    return rng.choice(candidates, size=count, replace=False)

def stable_argmax(arr, rng):
    max_val = arr.max()
    candidates = np.where(arr == max_val)[0]
    return rng.choice(candidates)  # size=1, replace не имеет смысла

def stable_argmin(arr, rng):
    max_val = arr.min()
    candidates = np.where(arr == max_val)[0]
    return rng.choice(candidates)  # size=1, replace не имеет смысла



class HistogramShifting:
    def clear(self):
        self.pix = None
        self.hist = None
        self.pairs = None
        self.stego = None
        self.bits_per_pair = None

    def __init__(self, *, debug=False):
        self.clear()
        self.data = None
        self.debug = debug

    def load_gray_from_pix(self, pix, *, stego=False):
        if stego:
            self.stego = pix.copy()
        else:
            self.clear()
            self.pix = pix.copy()
        return self

    def load_gray_from_io(self, file, *, stego=False):
        if stego:
            self.stego = read_bmp(file, to_gray=True)
        else:
            self.clear()
            self.pix = read_bmp(file, to_gray=True)
        return self

    def load_gray_from_file(self, name, *, stego=False):
        with open(name, "rb") as file:
            self.load_gray_from_io(file, stego=stego)
        return self

    def load_gray_from_zip(self, zip_name, name, *, stego=False):
        with zipfile.ZipFile(zip_name, "r") as zip:
            with zip.open(name, "r") as file:
                self.load_gray_from_io(file, stego=stego)
        return self

    def load_data(self, path):
        with open(path, "rb") as file:
            self.data = file.read()
        self.stego = None
        self.bits_per_pair = None
        return self

    def get_hist(self):
        # hist, bin_edges = np.histogram(self.pix, bins=256, range=(0, 255))  # Тормозной вариант из-за вычислений bin_edges, что нам не нужно,
                                                                              # потому что RDH‑методы работают строго с целыми значениями яркости
        if self.hist is None:
            self.hist = hist = np.bincount(self.pix.flatten(), minlength=256) # Прямой способ получить hist (сколько какой пиксель встречается раз)
            assert hist.shape == (256,)
            return hist
        return self.hist

    def Ni_et_al_2006(self, seed=0, probs=64):
        if self.pairs:
            return self.pairs
        rng = np.random.default_rng(seed) if isinstance(seed, int) else seed
        pairs_arr = []

        for i in range(probs):  # допустим, при 64-ёх пробах получим почти наилучшую ёмкость
            #   Step.1
            hist = self.get_hist()

            #   Step.2
            argsorted = stable_argsort(hist, 3, rng)
            b1, b2, b3 = sorted(argsorted)  # для гарантии порядка b1 < b2 < b3
          # print(b1, b2, b3)  # 2 4 11

            #   Step.3
            a1 = safe_argmax_interval(hist, 0, b1, rng)
            a3 = safe_argmax_interval(hist, b2, b3, rng)
          # print(a1, a3)  # 1 10

            #   Step.4
            a12, a21 = top2_in_interval(hist, b1, b2, rng)
            a23, a32 = top2_in_interval(hist, b2, b3, rng)
          # print(a12, a21, "|", a23, a32)  # None None | 7 10

            #   Step.5
            p1 = pick_best(hist, a1, a12)
            p2 = pick_best(hist, a21, a23)
            p3 = pick_best(hist, a32, a3)
          # print("picks:", p1, p2, p3)  # 1 7 10

            #   Step.6
            p1 = refine_peak(hist, p1, b1, rng)
            p2 = refine_peak(hist, p2, b2, rng)
            p3 = refine_peak(hist, p3, b3, rng)
          # print(p1, p2, p3)  # None 6 None

            # В статье прямо указано:
            #    All of these three pairs are treated as cases of peak and zero points pairs.
            # Но не сказано, что все три пары обязаны иметь пики.
            # Если пара не содержит пика → она просто не участвует в embedding.

            #   Step.7 в учебнике хоть и нет такого пункта, т.к. не уточняются детали, но получать здесь None - нормально
            pairs = tuple((int(pick), int(zero)) for pick, zero in ((p1, b1), (p2, b2), (p3, b3))
                            if pick is not None and hist[zero] == 0)
            #   Тем более, мы можем получить сразу из всех трёх refine_peak значения None,
            #   тогда делаем fallback на однопиковый HS 2004 года.
            if not pairs:
                pairs = self.Ni_et_al_2004(rng, use_cache=False)
            capacity = int(sum(hist[peak] for peak, zero in pairs))
            pairs_arr.append((capacity, pairs))
          # print(capacity, pairs)

        capacity, self.pairs = max(pairs_arr)
        for pick, zero in pairs:
            print(f"(p={pick}, b={zero})")
        print("capacity:", capacity // 8, "b.")

        return pairs

    def Ni_et_al_2004(self, seed=0, *, use_cache=True):
        if use_cache and self.pairs:
            # если Ni_et_al_2006 дал не пустой self.pairs, тогда мы просто выйдем этим путём :)
            return self.pairs        
        rng = np.random.default_rng(seed) if isinstance(seed, int) else seed

        hist = self.get_hist()
        peak = int(stable_argmax(hist, rng))  # cast np.int64 to int
        zero = find_nearest_zero(hist, peak, rng)
        self.pairs = pairs = (peak, zero),
        return pairs

    def get_capacity(self):
        hist = self.get_hist()
        pairs = self.Ni_et_al_2006()
        return int(sum(hist[peak] for peak, zero in pairs))

    def embed_one_pair(self, work, peak, zero, payload_bits):
        h, w = work.shape
        total = payload_bits.size

        # 1. SHIFT interval
        if zero < peak:
            mask = (work > zero) & (work < peak)
            work[mask] -= 1
            delta = -1
        else:
            mask = (work < zero) & (work > peak)
            work[mask] += 1
            delta = +1

        # 2. EMBED bits
        used = 0
        flat = work.flat

        for i in range(h * w):
            if used >= total:
                break

            if flat[i] == peak:
                if payload_bits[used] == 1:
                    flat[i] = peak + delta
                used += 1

        return work, used

    def extract_one_pair(self, peak, zero, work, total_bits):
        h, w = work.shape
        extracted = np.empty(total_bits, dtype=np.uint8)
        bit_pos = 0

        delta = -1 if zero < peak else +1
        flat = work.flat

        # 1. READ bits
        for i in range(h * w):
            if bit_pos >= total_bits:
                break

            v = flat[i]
            if v == peak:
                extracted[bit_pos] = 0
                bit_pos += 1
            elif v == peak + delta:
                extracted[bit_pos] = 1
                bit_pos += 1

        # 2. UNDO embed
        for i in range(h * w):
            if flat[i] == peak + delta:
                flat[i] = peak

        # 3. UNDO shift
        if zero < peak:
            mask = (work > zero) & (work < peak)
            work[mask] += 1
        else:
            mask = (work < zero) & (work > peak)
            work[mask] -= 1

        return extracted, work

    def embedder(self):
        if self.stego is not None:
            return self.stego

        if self.pix is None:
            raise RuntimeError("Сначала загрузите изображение")
        if self.data is None:
            raise RuntimeError("Сначала загрузите данные")

        capacity_bits = self.get_capacity()
        capacity_bytes = capacity_bits // 8

        if len(self.data) < capacity_bytes:
            raise RuntimeError("Недостаточно данных")

        payload = self.data[:capacity_bytes]
        payload_bits = np.unpackbits(np.frombuffer(payload, dtype=np.uint8)).astype(np.uint8)

        work = self.pix.astype(np.int16, copy=True)

        bit_pos = 0
        total_bits = payload_bits.size
        self.bits_per_pair = bits_per_pair = []

        for peak, zero in self.Ni_et_al_2006():
            if bit_pos >= total_bits:
                break

            chunk = payload_bits[bit_pos:]
            work, used = self.embed_one_pair(work, peak, zero, chunk)

            bits_per_pair.append(used)
            bit_pos += used

        self.stego = work.astype(np.uint8)
        return self.stego

    def save_stego(self, path):
        stego = self.embedder()
        save_bmp(path, stego, mode="gray")
        return self

    def extractor(self):
        if self.stego is None or self.bits_per_pair is None:
            raise RuntimeError("Сначала выполните embedder")

        total_bits = sum(self.bits_per_pair)

        extracted_bits = np.empty(total_bits, dtype=np.uint8)
        work = self.stego.astype(np.int16, copy=True)

        bit_pos = total_bits

        for (peak, zero), n_bits in zip(reversed(self.Ni_et_al_2006()), reversed(self.bits_per_pair)):
            start = bit_pos - n_bits
            bits, work = self.extract_one_pair(peak, zero, work, n_bits)
            extracted_bits[start:bit_pos] = bits
            bit_pos -= n_bits

        data = np.packbits(extracted_bits).tobytes()
        return data, work.astype(np.uint8)



def debug():
    np.random.seed(42)
    pix = np.random.randint(0, 253, size=(512,512), dtype=np.uint8)
    data_path = os.path.join("assets", "Harry Potter and the Philosopher's Stone.txt")
    HS = HistogramShifting().load_gray_from_pix(pix).load_data(data_path)
    HS.embedder()
    data, restored = HS.extractor()
    print(data.decode("windows-1251"))
    print(sum(sum(restored == HS.pix)), "/", HS.pix.size)
    exit()
# debug()



if __name__ == "__main__":
    zip_path = os.path.join("assets", "bossbase_containers.zip")
    data_path = os.path.join("assets", "Harry Potter and the Philosopher's Stone.txt")
    HS = HistogramShifting().load_gray_from_zip(zip_path, "205.bmp").load_data(data_path)
  # HS.Ni_et_al_2004()
  # HS.Ni_et_al_2006()
  # HS.get_capacity()
  # HS.embedder()
    data, restored = HS.save_stego("205_HS.bmp").extractor()
    print(data.decode("windows-1251"))
    print(sum(sum(restored == HS.pix)), "/", HS.pix.size)
