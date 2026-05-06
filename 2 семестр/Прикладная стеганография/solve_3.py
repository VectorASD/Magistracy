import numpy as np  # pip install numpy

from bitmap_driver import read_bmp, load_bmp, save_bmp
from gui import ImageGridGUI
from solve_1 import bmp_sampler_from_zip
from solve_2 import save_it, save_binary

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
        self.pairs = {}
        self.stego = None
        self.bits_per_pair = None

    def __init__(self, *, debug=True):
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

    def load_data(self, path, *, is_data=False):
        if is_data:
            assert isinstance(path, bytes)
            self.data = path
        else:
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

    def Ni_et_al_2006(self, *, seed=0, probs=64):
        probs = max(1, probs)
        key = seed, probs
        try: return self.pairs[key]
        except KeyError: pass

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
                pairs = self.Ni_et_al_2004(seed=rng)
            capacity = int(sum(hist[peak] for peak, zero in pairs))
            pairs_arr.append((capacity, pairs))
          # print(capacity, pairs)

        capacity, pairs = max(pairs_arr)
        if self.debug:
            for pick, zero in pairs:
                print(f"(p={pick}, b={zero})")
            print("capacity:", capacity // 8, "b.")
        self.pairs[key] = pairs
        return pairs

    def Ni_et_al_2004(self, *, seed=0):
        key = seed if isinstance(seed, int) else None
        try:
            # если Ni_et_al_2006 дал не пустой self.pairs, тогда мы просто выйдем этим путём :)
            return self.pairs[key]
        except KeyError: pass

        rng = np.random.default_rng(seed) if isinstance(seed, int) else seed

        hist = self.get_hist()
        peak = int(stable_argmax(hist, rng))  # cast np.int64 to int
        zero = find_nearest_zero(hist, peak, rng)
        pairs = (peak, zero),
        if key is not None:
            self.pairs[key] = pairs
        return pairs

    def get_capacity(self, *, seed=0, probs=64):
        hist = self.get_hist()
        pairs = self.Ni_et_al_2006(seed=seed, probs=probs)
        return int(sum(hist[peak] for peak, zero in pairs))

    @staticmethod
    def embed_one_pair(work, peak, zero, payload_bits):
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
        flat = work.ravel()  # shape 2D -> 1D
        is_peak = (flat == peak)
        peak_idx = np.nonzero(is_peak)[0]  # np.nonzero - синоним на np.where(is_peak != 0)[0]

        used = min(total, peak_idx.size)
        if used > 0:
            sel = peak_idx[:used]
            bits = payload_bits[:used]
            # меняем только там, где бит = 1
            flat[sel[bits == 1]] += delta

        return work, used

    @staticmethod
    def extract_one_pair(peak, zero, work, total_bits):
        h, w = work.shape
        flat = work.ravel()
        delta = -1 if zero < peak else +1

        # 1. READ bits
        is_peak      = (flat == peak)
        is_peak_d    = (flat == peak + delta)
        candidates   = np.nonzero(is_peak | is_peak_d)[0]

        count = min(total_bits, candidates.size)
        extracted = np.zeros(total_bits, dtype=np.uint8)

        if count > 0:
            sel = candidates[:count]
            extracted[:count] = (flat[sel] == peak + delta).astype(np.uint8)

        # 2. UNDO embed
        flat[flat == peak + delta] = peak

        # 3. UNDO shift
        if zero < peak:
            mask = (work > zero) & (work < peak)
            work[mask] += 1
        else:
            mask = (work < zero) & (work > peak)
            work[mask] -= 1

        return extracted, work

    @staticmethod
    def _embedder(pix, data, pairs, capacity_bytes):
        if len(data) < capacity_bytes:
            payload = data + b'\0' * (capacity_bytes - len(data))
        else:
            payload = data[:capacity_bytes]
        payload_bits = np.unpackbits(np.frombuffer(payload, dtype=np.uint8)).astype(np.uint8)
        assert payload_bits.shape == (capacity_bytes * 8,)

        work = pix.astype(np.int16, copy=True)

        bit_pos = 0
        total_bits = payload_bits.size
        bits_per_pair = []

        for peak, zero in pairs:
            if bit_pos >= total_bits:
                break

            chunk = payload_bits[bit_pos:]
            work, used = HistogramShifting.embed_one_pair(work, peak, zero, chunk)

            bits_per_pair.append(used)
            bit_pos += used

        return work.astype(np.uint8), bits_per_pair

    @staticmethod
    def _extractor(pairs, stego, bits_per_pair):
        total_bits = sum(bits_per_pair)

        extracted_bits = np.empty(total_bits, dtype=np.uint8)
        work = stego.astype(np.int16, copy=True)

        bit_pos = total_bits

        for (peak, zero), n_bits in zip(reversed(pairs), reversed(bits_per_pair)):
            start = bit_pos - n_bits
            bits, work = HistogramShifting.extract_one_pair(peak, zero, work, n_bits)
            extracted_bits[start:bit_pos] = bits
            bit_pos -= n_bits

        data = np.packbits(extracted_bits).tobytes()
        return data, work.astype(np.uint8)

    def embedder(self, *, seed=0, probs=64):
        if self.stego is not None:
            return self.stego

        if self.pix is None:
            raise RuntimeError("Сначала загрузите изображение")
        if self.data is None:
            raise RuntimeError("Сначала загрузите данные")

        pairs = self.Ni_et_al_2006(seed=seed, probs=probs)
        capacity_bits = self.get_capacity(seed=seed, probs=probs)
        capacity_bytes = capacity_bits // 8

        self.stego, self.bits_per_pair = self._embedder(self.pix, self.data, pairs, capacity_bytes)
        return self.stego

    def extractor(self, *, seed=0, probs=64):
        if self.stego is None or self.bits_per_pair is None:
            raise RuntimeError("Сначала выполните embedder или load_gray_from_*(..., stego=...) с указанием HS.bits_per_pair = ...")

        pairs = self.Ni_et_al_2006(seed=seed, probs=probs)
        data, unstego = self._extractor(pairs, self.stego, self.bits_per_pair)
        return data, unstego

    def save_stego(self, path):
        stego = self.embedder()
        save_bmp(path, stego, mode="gray")
        return self



def debug():
    np.random.seed(42)
    pix = np.random.randint(0, 253, size=(512,512), dtype=np.uint8)
    data_path = os.path.join("assets", "Harry Potter and the Philosopher's Stone.txt")
    HS = HistogramShifting().load_gray_from_pix(pix).load_data(data_path)
    HS.embedder()
    data, restored = HS.extractor()
    print(data.decode("windows-1251"))
    print((restored == HS.pix).sum(), "/", HS.pix.size)
    exit()
# debug()



def try_int(text: str):
    text = "".join(let for let in text if let.isdigit())
    return int(text) if text else 0

def ranges_intersect(r1, r2):
    return not (r1[1] < r2[0] or r2[1] < r1[0])


def is_reversible(hist, pairs):
    ranges = []
    errors = set()
    dense_ranges = []

    # 1. Построить диапазоны
    for p, z in pairs:
        if p == z:
            errors.add("peak == zero")
            return ", ".join(errors)

        if z < p:
            r = (z+1, p)
        else:
            r = (p+1, z)

        ranges.append((p, z, r))

    # 2. Пересечения диапазонов
    only_ranges = [r for (_, _, r) in ranges]
    for i in range(len(only_ranges)):
        for j in range(i+1, len(only_ranges)):
            if ranges_intersect(only_ranges[i], only_ranges[j]):
                errors.add("Пересечение диапазонов")

    # 3. Опасные границы
    for p, z, r in ranges:
        if z < p and r[1] == 255:   # сдвиг вверх в 255
            errors.add("Сдвиг к 255")
        if z > p and r[0] == 0:     # сдвиг вниз в 0
            errors.add("Сдвиг к 0")

    # 4. Каскады (мягкая версия)
    sorted_ranges = sorted(ranges, key=lambda x: x[2][0])
    for i in range(len(sorted_ranges)-1):
        (_, _, r1) = sorted_ranges[i]
        (_, _, r2) = sorted_ranges[i+1]

        # каскад только если диапазоны почти соприкасаются И оба широкие
        if (r1[1] + 1 == r2[0]) and ((r1[1]-r1[0] > 20) or (r2[1]-r2[0] > 20)):
            errors.add("Каскадный эффект")

    # 5. Плотность (мягкая версия)
    total = sum(hist)
    for p, z, r in ranges:
        width = r[1] - r[0] + 1
        if width <= 20:
            continue

        count = sum(hist[i] for i in range(r[0], r[1]+1))
        if count > total * 0.20:  # 20% вместо 10%
            dense_ranges.append(r)

    if dense_ranges:
        errors.add("Слишком плотный интервал: " + ", ".join(str(r) for r in dense_ranges))

    if not errors:
        return "OK"

    return ", ".join(errors)



def simulate_full(hist, pairs):
    """
    Полная симуляция embed->extract поверх гистограммы.
    Возвращает (True, "OK") или (False, "причина").
    """

    # 1. Разворачиваем гистограмму в массив пикселей
    values = []
    ids = []
    for v in range(256):
        count = hist[v]
        if count > 0:
            values.extend([v] * count)
            ids.extend([f"{v}_{i}" for i in range(count)])

    values = np.array(values, dtype=np.int16)
    ids = np.array(ids, dtype=object)

    # 2. Создаём payload, который гарантированно содержит и 0, и 1
    # Делаем payload длиной в 2 * количество пикселей
    payload_bits = np.tile([0, 1], len(values))

    # 3. EMBED
    bit_pos = 0
    for peak, zero in pairs:
        if bit_pos >= len(payload_bits):
            break

        values, ids, used = embed_one_pair_sim(values, ids, peak, zero, payload_bits[bit_pos:])
        bit_pos += used

    stego_values = values.copy()
    stego_ids = ids.copy()

    # 4. EXTRACT (в обратном порядке)
    for peak, zero in reversed(pairs):
        stego_values, stego_ids = extract_one_pair_sim(stego_values, stego_ids, peak, zero)

    # 5. Проверяем восстановление
    if np.array_equal(ids, stego_ids):
        return True, "OK"
    else:
        return False, "IDs mismatch"

def embed_one_pair_sim(values, ids, peak, zero, payload_bits):
    """
    Полная симуляция embed_one_pair с учётом ID.
    """

    total = len(payload_bits)

    # SHIFT
    if zero < peak:
        mask = (values > zero) & (values < peak)
        delta = -1
    else:
        mask = (values < zero) & (values > peak)
        delta = +1

    values[mask] += delta

    # EMBED
    is_peak = (values == peak)
    peak_idx = np.nonzero(is_peak)[0]

    used = min(total, peak_idx.size)
    if used > 0:
        sel = peak_idx[:used]
        bits = payload_bits[:used]

        # меняем только там, где бит = 1
        values[sel[bits == 1]] += delta

    return values, ids, used

def extract_one_pair_sim(values, ids, peak, zero):
    """
    Полная симуляция extract_one_pair с учётом ID.
    """

    # Определяем delta
    if zero < peak:
        delta = -1
    else:
        delta = +1

    # EMBED-UNDO:
    # пиксели, которые равны zero, могли быть:
    #   - исходный zero
    #   - peak + delta (бит 1)
    # но extractor НЕ знает, кто есть кто → он ВСЕ zero считает битом 1
    # и ВСЕ peak — битом 0
    #
    # Поэтому:
    #   - все zero -> peak (если delta < 0)
    #   - все zero -> peak (если delta > 0)
    #
    # То есть zero всегда превращается обратно в peak.
    #
    # Это и есть причина необратимости, если в zero были чужие пиксели.

    if delta == -1:
        # zero = peak - 1
        values[values == zero] = peak
    else:
        # zero = peak + 1
        values[values == zero] = peak

    # SHIFT-UNDO
    if delta == -1:
        # shift was values > zero & < peak
        mask = (values > zero) & (values < peak)
        values[mask] += 1
    else:
        mask = (values < zero) & (values > peak)
        values[mask] -= 1

    return values, ids



class MainGUI:
    def FDDSCS(self):
        # Гибкая декларативная система конфигурации источников данных :)
        # Flexible declarative data source configuration system (FDDSCS)

        self.opts = (
            ("file_original (bmp)",          self.choose_original),
            ("file_stego (any)",             self.choose_stego),
            ("unstego mode", "unstego mode", self.choose_mode),
            ("input_seed",                   self.enter_seed, {"default": 0}),
            ("input_probs",                  self.enter_probs, {"default": 64}),
            ("input_bits_per_pair",          self.input_bits_per_pair),
            "newline",
            ("utf-8", "windows-1251",        self.encoding_cb),
            "newline",
            "textarea_unstego",
            "newline",
            ("save stego image",  self.save_stego_image),
            ("save unstego text", self.save_unstego_text),
            "newline",
            ("PSNR",              self.PSNR_async),
        )

    def choose_original(self, path):
        self.original = load_bmp(path, to_gray=True)
        self.app.set_image(0, self.original)
        self.update()

    def choose_stego(self, path):
        self.stego_text_path = path
        self.update()

    def choose_mode(self, mode):
        self.unstego_mode = mode
        self.update()

    def enter_seed(self, seed):
        self.seed = try_int(seed)
        self.update()

    def enter_probs(self, probs):
        self.probs = try_int(probs)
        self.update()

    def input_bits_per_pair(self, bits_per_pair):
        self.bits_per_pair = tuple(map(try_int, bits_per_pair.split(",")))
        self.update()

    def encoding_cb(self, encoding):
        self.encoding = encoding
        if self.unstego_text is not None:
            self.app.panel.set_textarea_text(0, self.unstego_text.decode(self.encoding, errors="replace"))

    def update(self):
        if self.original is not None and self.stego_text_path:
            HS = HistogramShifting().load_gray_from_pix(self.original)

            if self.unstego_mode:
                try: self.stego = load_bmp(self.stego_text_path, to_gray=True)
                except ValueError:
                    return
                HS.load_gray_from_pix(self.stego, stego=True)
                HS.bits_per_pair = self.bits_per_pair
            else:
                HS.load_data(self.stego_text_path)
                self.stego = HS.embedder(seed=self.seed, probs=self.probs)
                self.bits_per_pair = HS.bits_per_pair
            self.app.set_image(1, self.stego)

            self.unstego_text, self.unstego = HS.extractor(seed=self.seed, probs=self.probs)
            self.app.set_image(2, self.unstego)
            self.app.panel.set_textarea_text(0, self.unstego_text.decode(self.encoding, errors="replace"))
            self.app.panel.set_input_text(2, ", ".join(map(str, HS.bits_per_pair)))

            delta = ((self.original != self.unstego) * 255).astype(np.uint8)
            self.app.set_image(3, delta)

    def save_stego_image(self):
        save_it(self.stego, "Сначала выберите оригинал и внедряемые данные", "Сохранить стегоконтейнер")

    def save_unstego_text(self):
        save_binary(self.unstego_text, "Сначала получите текстовый unstego", "Сохранить извлечённые данные")

    def PSNR_async(self):
        from multiprocessing import Process
        ci_process = Process(target=MainGUI.PSNR, args=())
        ci_process.start()

    @staticmethod
    def PSNR():
        data_path = os.path.join("assets", "Harry Potter and the Philosopher's Stone.txt")
        with open(data_path, "rb") as file:
            data = file.read()

        MAX_I = 255.0
        psnrs = []
        for base in ("BOSSbase", "medical", "portrait"):
            match base:
                case "BOSSbase": path = "assets/bossbase_containers.zip"
                case "medical":  path = "assets/medical_containers.zip"
                case "portrait": path = "assets/portrait_containers.zip"

            print(f"Анализирую {base}...")
            pixs, filenames = bmp_sampler_from_zip(path, filter=False)
            assert len(pixs) == 100

            mses       = []
            capacities = []
            equals     = 0
            for i, orig in enumerate(pixs):
              # print(f"  {i+1}/100")
                HS = HistogramShifting(debug=False).load_gray_from_pix(orig).load_data(data, is_data=True)
                stego = HS.embedder()
                unstego_text, unstego = HS.extractor()

                pix_eqials = (orig == unstego).sum()
                capacity   = sum(HS.bits_per_pair)
                pairs      = HS.pairs[(0, 64)]
                hist       = HS.get_hist()
                print(pix_eqials, "/", orig.size, pix_eqials == orig.size, pairs, HS.bits_per_pair, len(unstego_text), filenames[i])
              # print("   ", is_reversible(hist, pairs))
              # print("   ", simulate_full(hist, pairs))

                diff = orig.astype(np.float32) - stego.astype(np.float32)
                mse = (diff * diff).mean()

                mses.append(mse)
                capacities.append(capacity)
                equals += (pix_eqials == orig.size)

            print("capacities:", capacities, "bits.")
            print("capacities_avg:", np.mean(capacities), "bits.")
            print("equals:", equals, "%")

            mean_mse = np.mean(mses)
            psnr = float(10.0 * np.log10((MAX_I * MAX_I) / mean_mse) if mean_mse else "inf")
            psnrs.append(psnr)
        print("PSNRs:", psnrs)  # [51.52054214477539, 54.005733489990234, 51.46250915527344]

    def __init__(self):
        self.original        = None
        self.stego_text_path = None
        self.stego           = None
        self.unstego_mode    = False
        self.unstego         = None
        self.unstego_text    = None
        self.encoding        = None
        self.seed          = 0
        self.probs         = 64
        self.bits_per_pair = None
        self.FDDSCS()

        self.app = ImageGridGUI(1, 4, opts=self.opts, texts=("original", "stego", "unstego", "delta"))

    def mainloop(self):
        self.app.mainloop()



def main():
    zip_path = os.path.join("assets", "bossbase_containers.zip")
    data_path = os.path.join("assets", "Harry Potter and the Philosopher's Stone.txt")
    HS = HistogramShifting().load_gray_from_zip(zip_path, "205.bmp").load_data(data_path)
  # HS.Ni_et_al_2004()
  # HS.Ni_et_al_2006()
  # HS.get_capacity()
  # HS.embedder()
    data, restored = HS.save_stego("205_HS.bmp").extractor()
    print(data.decode("windows-1251"))
    print((restored == HS.pix).sum(), "/", HS.pix.size)



if __name__ == "__main__":
  # main()
    MainGUI().mainloop()
