import numpy as np # pip install numpy

from bitmap_driver import read_bmp, load_bmp, save_bmp
from gui import BitPlaneGUI, HistogramGUI, plot_ci
from utils import confidence_interval

import zipfile
import os
import random



def get_k_layer(pix, k):
    shifted = pix >> (k - 1)
    if k != 8: shifted &= 1
    return shifted

def insert_k_layer(pix, k, message, *, slice=False):
    W, H = pix.shape
    capacity = W * H - 32
    is_buffer = isinstance(message, np.ndarray)
    if is_buffer:
        assert message.dtype == np.uint8
        assert len(message.shape) == 1

    need = len(message) * 8
    if capacity < need:
        if slice:
            message = message[:capacity // 8]
            need = len(message) * 8
        else:
            raise ValueError(f"Capacity is {capacity}, but required is {need}") 

    buffer = message if is_buffer else np.frombuffer(message, dtype=np.uint8)
    bits = np.unpackbits(buffer)
    assert bits.shape == (need,)

    bits = np.pad(bits, (0, capacity+32-need))
    for i in range(32):
        bits[-1-i] = need >> i & 1
    bits = bits.reshape(W, H)
    assert bits.shape == (W, H)

    shift = k-1
    mask = ~(1 << shift) & 255
    return pix & mask | bits << shift

# print(bits.reshape((1,) * 100 + (32,)))
# ValueError: maximum supported dimension for an ndarray is currently 64, found 101
# интересно было узнать максимальный ранг формы

def read_k_layer(pix, k, tobytes=True):
    bits = get_k_layer(pix, k)
    W, H = pix.shape
    bits = bits.reshape(W * H)
    need = 0
    for i in range(32):
        need |= int(bits[-1-i]) << i
    # print(need, len(bits)) # 262112 262144
    if need > len(bits) - 32:
        raise ValueError("Corrupted container: message length is invalid")
    buffer = np.packbits(bits[:need])
    if tobytes:
        return buffer.tobytes()
    return buffer



def make_dirs(path):
    dir = os.path.dirname(path)
    os.makedirs(dir, exist_ok=True)

def save_layer(path, pix, k):
    make_dirs(path)
    new_pix = get_k_layer(pix, k) * 255
    save_bmp(path, new_pix, mode="mono")

def save_with_message(path, pix, k, message):
    make_dirs(path)
    new_pix = insert_k_layer(pix, k, message)
    save_bmp(path, new_pix, mode="gray")

def load_message(path, k):
    pix = load_bmp(path, to_gray=True)
    return read_k_layer(pix, k)



def read_bmp_from_zip(path):
    with zipfile.ZipFile(path, "r") as zip:
        file_list = zip.namelist()
        print("Файлы в архиве:", file_list)

        first_name = file_list[0]
        print("Имя первого файла:", first_name)

        with zip.open(first_name, "r") as file:
            pix = read_bmp(file, debug=False, to_gray=True)
    return pix

def main(path, msg_path):
    pix = read_bmp_from_zip(path)

    for k in range(1, 9):
        save_layer(f"result/layer_k{k}.bmp", pix, k)

    W, H = pix.shape
    max_bits = W * H - 32
    with open(msg_path, "rb") as file:
        message = file.read(max_bits // 8)

    for k in range(1, 9):
        save_with_message(f"result/stego_k{k}.bmp", pix, k, message)

    orig_message = message
    for k in range(1, 9):
        print("~" * 77)
        message = load_message(f"result/stego_k{k}.bmp", k)
        print("EQUALS?", message == orig_message)
        print()
        print(message[:256].decode("windows-1251"))



"""
Что именно измеряют MSE, PSNR и SSIM?

Эти три метрики появились в задачах:
    сжатия изображений (JPEG, JPEG2000),
    восстановления после шума,
    суперразрешения,
    денойзинга,
    реконструкции после передачи по каналу.

Их смысл:
    MSE — насколько сильно отличаются два изображения по пикселям.
    PSNR — насколько «громкий» сигнал по сравнению с ошибкой, меряется в децибелах.
    SSIM — насколько похожи структуры, контраст и яркость.

То есть они отвечают на вопрос:
    «Насколько хорошо 𝐼^ (искажённое изображение) похоже на оригинал 𝐼?»
"""

# np.mean = lambda x: x.astype(np.float32).sum() / x.size                      AVG
# np.var  = lambda x: ((mean(x) - x.astype(np.float32)) ** 2).sum() / x.size   дисперсия

def mean_squared_error(orig: np.ndarray, stego: np.ndarray) -> float: # MSE
    """MSE — Mean Squared Error"""
    diff = orig.astype(np.float32) - stego.astype(np.float32)
    return float((diff * diff).mean())

def peak_signal_to_noise_ratio(orig: np.ndarray, stego: np.ndarray) -> float:
    """PSNR — Peak Signal-to-Noise Ratio"""
    mse = mean_squared_error(orig, stego)
    if mse == 0:
        return float("inf")
    MAX_I = 255
    return float(10 * np.log10((MAX_I * MAX_I) / mse))

def structural_similarity_index(orig: np.ndarray, stego: np.ndarray) -> float:
    """SSIM — Structural Similarity Index""" # на деле SIM - это первые 3 буквы Similarity :)
    orig = orig.astype(np.float32)
    stego = stego.astype(np.float32)

    mu_x  = orig.mean()
    mu_y  = stego.mean()

    sigma_x2 = orig.var()
    sigma_y2 = stego.var()
    sigma_xy = ((orig - mu_x) * (stego - mu_y)).mean() # ковариация
    # Дисперсия измеряет, насколько значения одной величины отклоняются от своего среднего.
    # Ковариация измеряет, насколько две величины отклоняются от своих средних одновременно.
    # Дисперсия — это частный случай ковариации, когда сравнивают величину саму с собой.

    MAX_I = 255
    C1 = (0.01 * MAX_I) ** 2 #  6.5025
    C2 = (0.03 * MAX_I) ** 2 # 58.5225

    num = (2 * mu_x * mu_y + C1) * (2 * sigma_xy + C2)
    den = (mu_x**2 + mu_y**2 + C1) * (sigma_x2 + sigma_y2 + C2)

    return float(num / den)



def bmp_sampler_from_zip(path, count=None, filter=True):
    pixs = []
    with zipfile.ZipFile(path, "r") as zip:
        file_list = zip.namelist()
        if count:
            assert len(file_list) >= count
        if filter:
            file_list = tuple(name for name in file_list if not name.startswith("ernst-ludwig-kirchner"))

        sample = random.sample(file_list, count) if count else file_list

        for name in sample:
            with zip.open(name, "r") as file:
                pix = read_bmp(file, debug=False, to_gray=True)
            pixs.append(pix)
    return pixs

class MainGUI:
    def analyze_sample(self):
        stats = {k: {"mse": [], "ssim": []} for k in range(1, 9)}

        for orig in self.pixs:
            for k in range(1, 9):
                pix = orig
                if self.plane:
                    pix = get_k_layer(pix, k) * 255
                if self.stego:
                    pix = insert_k_layer(pix, k, self.message, slice=True)

                if self.mse:
                    stats[k]["mse"].append(mean_squared_error(orig, pix))
                if self.ssim:
                    stats[k]["ssim"].append(structural_similarity_index(orig, pix))

        base = f"base: {self.base}"
        branch = "I^ = I"
        if self.plane: branch += " + to_plane(k)"
        if self.stego: branch += " + to_stego(k)"

        lines = [base, branch]

        # алгоритмы усреднения
        for k in range(1, 9):
            parts = [f"k={k}"]
            if self.mse:
                mse_avg = np.mean(stats[k]["mse"])
                parts.append(f"mse={mse_avg:.4f}")
                MAX_I = 255
                psnr_avg = float(10 * np.log10((MAX_I * MAX_I) / mse_avg) if mse_avg else "inf")
                parts.append(f"psnr={psnr_avg:.4f}")
            if self.ssim:
                ssim_avg = np.mean(stats[k]["ssim"])
                parts.append(f"ssim={ssim_avg:.4f}")
            lines.append(", ".join(parts))

        text = "\n".join(lines)
        print(text)

        self.app.clipboard_clear()
        self.app.clipboard_append(text)
        self.app.update()

    def show_histograms(self):
        pixs    = self.app.pixs
        planes  = self.app.planes
        current = self.app.prev_idx

        HistogramGUI(self.app, pixs + planes, current)

    @staticmethod
    def confidence_interval_async():
        from multiprocessing import Process
        ci_process = Process(target=MainGUI.confidence_interval)
        ci_process.start()

    @staticmethod
    def confidence_interval():
        psnr_rows = []
        var_rows = []

        for base in ("BOSSbase", "medical", "portrait"):
            match base:
                case "BOSSbase": path = "assets/bossbase_containers.zip"
                case "medical":  path = "assets/medical_containers.zip"
                case "portrait": path = "assets/portrait_containers.zip"

            print(f"Анализирую {base}...")
            pixs = bmp_sampler_from_zip(path, filter=False)
            assert len(pixs) == 100

            for k in range(1, 9):
                psnrs = []
                for orig in pixs:
                    pix = get_k_layer(orig, k) * 255
                    mse = mean_squared_error(orig, pix)
                    psnr = 10 * np.log10((255 * 255) / mse) if mse else float("inf")
                    psnrs.append(psnr)
                arr = np.array(psnrs)

                avg = arr.mean()
                std = arr.std(ddof=1) # по умолчанию, ddof=0
                # std² = (1/(n-ddof)) * Σ (x_i − x̄)²
                # ddof=0 → смещённая дисперсия:   σ² = (1/n)     * Σ (x_i − x̄)²
                # ddof=1 → несмещённая дисперсия: s² = (1/(n−1)) * Σ (x_i − x̄)²
                n = len(arr)
                low, high = confidence_interval(avg, std, n, alpha=0.05)

                psnr_rows.append((base, k, std, low, avg, high))

                variances = []
                for orig in pixs:
                    layer = get_k_layer(orig, k) # без * 255 это просто 0 и 1
                    var = layer.var(ddof=1) # по умолчанию, ddof=0
                    # var = дисперсия выборки: тоже самое, что std, только возвращаем напрямую σ²,s², вместо σ,s
                    variances.append(var)

                arr = np.array(variances)
                avg = arr.mean()
                std = arr.std(ddof=1)
              # n = len(arr)
                low, high = confidence_interval(avg, std, n, alpha=0.05)

                var_rows.append((base, k, std, low, avg, high))

        import csv
        with open("psnr_ci_table.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(("base", "k", "std", "low", "avg", "high"))
            writer.writerows(psnr_rows)
        print("CSV сохранён: psnr_ci_table.csv")

        with open("variance_ci_table.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(("base", "k", "std", "low", "avg", "high"))
            writer.writerows(var_rows)
        print("CSV сохранён: variance_ci_table.csv")

        plot_ci(psnr_rows, title="Доверительные интервалы PSNR для разных контейнеров",                         filename="psnr_ci_graph.png")
        plot_ci(var_rows,  title="Доверительные интервалы дисперсии битовых плоскостей для разных контейнеров", filename="variance_ci_graph.png")
    """
    Для бинарных данных дисперсия имеет простую формулу:
        var=𝑝(1-𝑝)
        где 𝑝 - доля единиц.
    Это максимум:
        0.25 при 𝑝=0.5
    То есть:
        дисперсия битовой плоскости не может быть больше 0.25
        а чаще всего она намного меньше, потому что распределение 0 и 1 неравномерное
    """



    def plane_cb(self, orig, k):
        pix = orig
        if self.plane:
            pix = get_k_layer(pix, k) * 255
        if self.stego:
            # ValueError: Capacity is 262112, but required is 3628328
            pix = insert_k_layer(pix, k, self.message, slice=True)

        label = [f"k={k}"]
        if self.mse:
            mse = mean_squared_error(orig, pix)
            label.append(f"mse={mse:.4f}")
        if self.psnr:
            psnr = peak_signal_to_noise_ratio(orig, pix)
            label.append(f"psnr={psnr:.4f}")
        if self.ssim:
            ssim = structural_similarity_index(orig, pix)
            label.append(f"ssim={ssim:.4f}")

        label = ", ".join(label)
        if k == 1:
            self.labels.clear()
        self.labels.append(label)

        return pix, label

    def recalc(self):
        self.app.show_bit_planes()

    def pixs_cb(self, name):
        match name:
            case "BOSSbase": path = "assets/bossbase_containers.zip"
            case "medical":  path = "assets/medical_containers.zip"
            case "portrait": path = "assets/portrait_containers.zip"
        self.base = name
        self.pixs = pixs = bmp_sampler_from_zip(path, 8)

        self.app.show_original_previews(pixs)
        self.app.on_click_original(0)

    def on_plane(self, on): self.plane = on; self.recalc()
    def on_stego(self, on): self.stego = on; self.recalc()
    def on_mse  (self, on): self.mse   = on; self.recalc()
    def on_psnr (self, on): self.psnr  = on; self.recalc()
    def on_ssim (self, on): self.ssim  = on; self.recalc()

    def copy_to_clipboard(self):
        base = f"base: {self.base}"
        branch = "I^ = I"
        if self.plane: branch += " + to_plane(k)"
        if self.stego: branch += " + to_stego(k)"

        text = "\n".join((base, branch, *self.labels))
        print(text)

        self.app.clipboard_clear()
        self.app.clipboard_append(text)
        self.app.update()

    def FDDSCS(self):
        # Гибкая декларативная система конфигурации источников данных :)
        # Flexible declarative data source configuration system (FDDSCS)

        self.opts = (
            ("BOSSbase", "medical", "portrait", self.pixs_cb),
          # ("is_checkbox", "is_checkbox",      lambda checked: print("checked:", checked)),
          # ("is_button",                       lambda: print("punched!")),
            ("plane", "plane", self.on_plane, {"default": True}),
            ("stego", "stego", self.on_stego),
            ("mse",   "mse",   self.on_mse),
            ("psnr",  "psnr",  self.on_psnr),
            ("ssim",  "ssim",  self.on_ssim),
            ("copy",    self.copy_to_clipboard),
            ("analyze", self.analyze_sample),
            ("hist",    self.show_histograms),
            ("ci_graph", MainGUI.confidence_interval_async),
        )

    def read_message(self):
        with open(self.msg_path, "rb") as file:
            self.message = file.read()

    def __init__(self):
        self.plane = True
        self.stego = False
        self.mse   = False
        self.psnr  = False
        self.ssim  = False
        self.base  = "???"
        self.labels = []
        self.FDDSCS()

        self.msg_path = "assets/Harry Potter and the Philosopher's Stone.txt"
        self.read_message()

        self.app = BitPlaneGUI(self.plane_cb, self.opts)

    def mainloop(self):
        self.app.mainloop()



if __name__ == "__main__":
    path     = "assets/bossbase_containers.zip"
    msg_path = "assets/Harry Potter and the Philosopher's Stone.txt"
    count    = 8

  # main(path, msg_path)
    MainGUI().mainloop()
