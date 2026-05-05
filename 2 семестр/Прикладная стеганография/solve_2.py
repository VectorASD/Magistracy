import numpy as np # pip install numpy
from PIL import Image # pip install pillow

from bitmap_driver import save_bmp, load_bmp
from solve_1 import bmp_sampler_from_zip, insert_k_layer, read_k_layer
from utils import gradient_from_name, GRADIENT_KERNELS
from gui import ImageGridGUI, plot_ci
from utils import confidence_interval

from functools import lru_cache
import os
from hashlib import pbkdf2_hmac

from tkinter import messagebox, filedialog



# Благодаря @lru_cache функция автоматически кэширует результат уменьшения логотипа.
# Это позволяет вызывать её прямо внутри методов встраивания, не вынося расчёт
# capacity_bits и загрузку логотипа в отдельный блок.
# Вся логика остаётся локальной, а повторные вызовы становятся мгновенными.
@lru_cache
def load_logo_with_fit(logo_path: str, target_shape: tuple[int, int], *, layers=1, reshape=True) -> bytes:
    """
    Загружает RGB-логотип, уменьшает его так, чтобы его битовый поток
    умещался в capacity_bits, и возвращает байтовую строку.
    layers добавил чисто на будущее, но может и не понадобиться многослойное внедрение...
    """

    W, H = target_shape
    capacity_bits = W * H * layers - 32      # 32 бита резервируется на указание размера полезной нагрузки (payload'а)

    img = Image.open(logo_path).convert("RGB")
    W0, H0 = img.size
    assert W0 == H0, "Логотип желательно делать квадратным"

    orig_bits = W0 * H0 * 3 * 8              # Сколько бит нужно на исходный логотип

    # --- логотип слишком маленький ---
    if orig_bits < capacity_bits:
        raise ValueError(
            f"Логотип слишком маленький: {orig_bits} бит, "
            f"а контейнер позволяет {capacity_bits} бит. "
            f"Используйте логотип большего размера."
        )

    target_pixels = capacity_bits // (3 * 8) # Требуемая площадь
    side = int(target_pixels ** 0.5)         # Новая сторона (квадрат)
    side = max(1, side)                      # Минимум 1×1

    # Pillow рекомендует: Image.LANCZOS — лучший для уменьшения (высокое качество + антиалиасинг)
    logo = img.resize((side, side), Image.LANCZOS)

    # Превращаем в байты
    watermark = np.array(logo, dtype=np.uint8)
    if reshape:
        watermark = watermark.reshape(-1) # arr.reshape(-1) <-> arr.reshape(arr.size)
  # print("Допустимо: ", capacity_bits,        "bits") # 262112 bits
  # print("Получилось:", watermark.nbytes * 8, "bits") # 259584 bits
    assert watermark.nbytes * 8 <= capacity_bits
    return logo, watermark

@lru_cache
def get_logo_size_with_fit(target_shape: tuple[int, int], layers=1):
    "Просто реализована та же логика, что и в load_logo_with_fit, но только для размеров"
    W, H = target_shape
    capacity_bits = W * H * layers - 32
    target_pixels = capacity_bits // (3 * 8) # Требуемая площадь
    side = int(target_pixels ** 0.5)         # Новая сторона (квадрат)
    side = max(1, side)                      # Минимум 1×1
    return (side, side, 3)



def check_resizer():
    logo_path = "my_logo.png"
    pixs, _ = bmp_sampler_from_zip("assets/bossbase_containers.zip", count=1)
    target = pixs[0]
    logo, watermark = load_logo_with_fit(logo_path, target.shape)
    os.makedirs("result", exist_ok=True)
    logo.save("result/logo_small.png")
    print(watermark)



def make_random_from_str(password: str, salt="stego-salt", rounds=1024):
    "Генератор по ключу (PBKDF2 → uint64 tuple → PCG64)"
    digest = pbkdf2_hmac(
        hash_name ="sha256",
        password  =password.encode("utf-8"),
        salt      =salt.encode("utf-8"),
        iterations=rounds,
      # dklen     =32 # default: sha256 -> 256 / 8 = 32 bytes
    )
    assert len(digest) == 32
    # np.random.default_rng(digest) -> SeedSequence expects int or sequence of ints for entropy not b'123'
    # default_rng выдаёт генератор вида PCG64, а SeedSequence - это просто кортеж из int'ов ЛЮБОЙ длины
    # внутренее состояние PCG64 состоит из 128-битного числа, так что подобрать seed будет нереально
    arr = np.frombuffer(digest, dtype=np.uint64)
    seed = tuple(map(int, arr))
    return np.random.default_rng(seed)

# prev_order = None

def make_indices_adaptive(pix: np.ndarray, key: str, num_bits: int, kernel_name: str) -> np.ndarray:
    """
    Индексы для адаптивного метода:
    сортировка по градиенту + перемешивание по ключу.
    """
    H, W = pix.shape
    total = H * W

    grad = gradient_from_name(pix, kernel_name, mode="same") # 2D карта
    flat = grad.reshape(total)                               # 1D
  # print("SIZE:", W, "x", H)
  # print("key:", key)
  # print("num_bits:", num_bits)

    order = np.argsort(flat)[::-1]                    # по убыванию градиента
  # print("order:", order, len(order))

    # global prev_order
    # if prev_order is None:
    #     prev_order = order.copy()
    # else:
    #     diff = np.where(prev_order != order)[0]
    #     print("Первое расхождение:", diff[0] if diff.size else "нет")

    make_random_from_str(key + "|idx").shuffle(order) # генератор НЕ должен зависеть от того, что в embed_logo_lsb_with_key

    order = order[:num_bits]
    # print("S order:", order, len(order))
    return order, grad

def embed_logo_lsb_with_key(pix: np.ndarray, key: str, logo_path: str, *, kernel_name=None) -> np.ndarray:
    """
    Метод 1: LSB‑встраивание с секретным ключом.
    Логотип автоматически уменьшается до максимально допустимого размера.
    """
    assert pix.ndim == 2
    random = make_random_from_str(key)
    _, watermark = load_logo_with_fit(logo_path, pix.shape)

    if kernel_name is None:
        idxs = np.arange(watermark.size) # [ 52107 229168 135349 ...   6164 246636  33432]
        random.shuffle(idxs)
        shuffled = watermark[idxs]

        stego = insert_k_layer(pix, k=1, message=shuffled)
        return stego, None

    # адаптивный режим
    wm_bytes = watermark.reshape(-1)
    num_bytes = wm_bytes.size

    idxs_bytes = np.arange(num_bytes)
    random.shuffle(idxs_bytes)

    shuffled_bytes = wm_bytes[idxs_bytes]

    wm_bits = np.unpackbits(shuffled_bytes)
    num_bits = wm_bits.size

    indices, grad = make_indices_adaptive(pix, key, num_bits, kernel_name)

    return insert_k_layer(pix, k=1, message=wm_bits, indices=indices), grad

def extract_logo_lsb_with_key(pix: np.ndarray, key: str, *, kernel_name=None, orig_pix=None):
    "Извлекает логотип, встроенный методом 1 (LSB + перестановка индексов)."
    assert pix.ndim == 2

    if kernel_name is None or orig_pix is None:
        # 1) Читаем байты из LSB-слоя
        wm_arr = read_k_layer(pix, k=1, tobytes=False)
        assert wm_arr.dtype == np.uint8

        # 2) Генерируем ту же перестановку индексов
        random = make_random_from_str(key)
        idxs = np.arange(wm_arr.size)
        random.shuffle(idxs)

        # 3) Обратная перестановка
        unshuffled = np.empty_like(wm_arr) # копирует форму растра, но заполненную нулями
        unshuffled[idxs] = wm_arr          # не нужно инвертировать idxs, если можно так!)

        # 4) Восстанавливаем квадратный RGB
        total = len(unshuffled)
        assert total % 3 == 0, "Повреждённый watermark: длина не кратна 3"

        pixels = total // 3
        side = round(pixels ** 0.5)
        assert side * side * 3 == total, "Повреждённый watermark: не квадрат"

        logo = unshuffled.reshape((side, side, 3))
        return logo

    # адаптивный режим
    # 1) Загружаем watermark, чтобы узнать его размер, но без логики с растром
    W, H, C = get_logo_size_with_fit(pix.shape)
    num_bytes = W * H * C
    num_bits = num_bytes * 8

    # 2) Генерируем адаптивные индексы (как в embed)
    indices, _ = make_indices_adaptive(orig_pix, key, num_bits, kernel_name)

    # 3) Читаем только эти позиции
    wm_arr = read_k_layer(pix, k=1, tobytes=False, indices=indices)
    assert wm_arr.dtype == np.uint8

    # 4) Обратная перестановка watermark (как в embed)
    random = make_random_from_str(key)
    idxs = np.arange(num_bytes)
    random.shuffle(idxs)

    unshuffled = np.empty_like(wm_arr)
    unshuffled[idxs] = wm_arr

    # 5) Восстанавливаем квадратный RGB
    return unshuffled.reshape((W, H, C))



def compare_logos(logo_path: str, stego: np.ndarray, extracted: np.ndarray):
    _, watermark = load_logo_with_fit(logo_path, stego.shape, reshape=False)
    print(watermark)

    diff = watermark.astype(np.float32) - extracted.astype(np.float32)
    mse = float((diff * diff).mean())
    MAX_I = 255
    psnr = float(10 * np.log10((MAX_I * MAX_I) / mse) if mse else "inf")

    print("mse:",  mse)  # 0.0
    print("psnr:", psnr) # inf

def check_embedder():
    pix, _ = bmp_sampler_from_zip("assets/bossbase_containers.zip", count=1)[0]
    stego, _ = embed_logo_lsb_with_key(pix, "meowl", "my_logo.png")
    save_bmp("watermarked.bmp", stego, mode="gray")

def check_extractor():
    stego = load_bmp("watermarked.bmp", to_gray=True)
    extracted = extract_logo_lsb_with_key(stego, "meowl")
    # Image.fromarray(extracted).save("unwatermarked.png")
    compare_logos("my_logo.png", stego, extracted)



def overlay_gradient(pix, grad):
    """
    Просто умножаем исходное изображение на градиент.
    Это лучше выглядело бы на цветных картинках.
    """
    # Растянуть до размера исходного изображения
    H, W = pix.shape
    h, w = grad.shape
    pad_y = (H - h) // 2
    pad_x = (W - w) // 2

    mask = np.zeros(pix.shape, dtype=np.float32)
    mask[pad_y:pad_y+h, pad_x:pad_x+w] = grad

    # Наложение
    return (pix.astype(np.float32) * mask).clip(0, 255).astype(np.uint8)

def check_gradient():
    pix, _ = bmp_sampler_from_zip("assets/bossbase_containers.zip", count=1)[0]
    preset = [pix]
    overlays = [None]
    for kernel_name in GRADIENT_KERNELS:
        print(f"{kernel_name}...")
        grad = gradient_from_name(pix, kernel_name)
        preset.append(grad * 255)
        overlays.append(overlay_gradient(pix, grad))

    gui = ImageGridGUI(2, len(preset), preset = preset + overlays)
    for i, kernel_name in enumerate(GRADIENT_KERNELS):
        gui.set_text((1, 1+i), kernel_name)
    gui.mainloop()

def check_adaptive_embedder():
    pix, _ = bmp_sampler_from_zip("assets/bossbase_containers.zip", count=1)[0]
    stego, _ = embed_logo_lsb_with_key(pix, "meowl", "my_logo.png", kernel_name="sobel7")
    save_bmp("watermarked2.bmp",      stego, mode="gray")
    save_bmp("watermarked2_orig.bmp", pix,   mode="gray")

def check_adaptive_extractor():
    pix   = load_bmp("watermarked2_orig.bmp", to_gray=True)
    stego = load_bmp("watermarked2.bmp", to_gray=True)
    extracted = extract_logo_lsb_with_key(stego, "meowl", kernel_name="sobel7", orig_pix=pix)
    Image.fromarray(extracted).save("unwatermarked.png")
    #compare_logos("my_logo.png", stego, extracted)



def save_it(pix: np.ndarray, error: str, title: str):
    if pix is None:
        messagebox.showerror("Ошибка источника", error)
        return

    path = filedialog.asksaveasfilename(
        title=title,
        defaultextension=".png",
        filetypes=[("BMP", "*.bmp"), ("PNG", "*.png"), ("Все файлы", "*.*")]
    )

    if path:
        try:
            Image.fromarray(pix).convert("L").save(path)
        except Exception as e:
            messagebox.showerror("Ошибка сохранения", e)
    # иначе, пользователь отменил asksaveasfilename

def save_binary(data: bytes, error: str, title: str):
    if data is None:
        messagebox.showerror("Ошибка источника", error)
        return

    path = filedialog.asksaveasfilename(
        title=title,
        defaultextension=".txt",
        filetypes=[
            ("Text", "*.txt"),
            ("Binary", "*.bin"),
            ("All files", "*.*"),
        ]
    )

    if not path:
        return  # пользователь отменил

    try:
        with open(path, "wb") as f:
            f.write(data)
    except Exception as e:
        messagebox.showerror("Ошибка сохранения", str(e))



class MainGUI:
    kernel_names = tuple(key for key in GRADIENT_KERNELS if key not in ("diff", "roberts"))

    def FDDSCS(self):
        # Гибкая декларативная система конфигурации источников данных :)
        # Flexible declarative data source configuration system (FDDSCS)

        self.opts = (
            ("file_stego (bmp)",         self.choose_original),
            ("file_watermark (png)",     self.choose_watermark),
            ("input_password",           self.setter("password"), {"default": "meowl"}),
            ("use kernel", "use kernel", self.setter("is_adaptive")),
            (*MainGUI.kernel_names,      self.setter("kernel"), {"default": "sobel7"}),
            ("save stego",   self.save_stego),
            ("save grad",    self.save_grad),
            ("save unstego", self.save_unstego),
            ("file_grad original (bmp)", self.choose_grad_original),
            ("ci_graph",     self.confidence_interval_async),
        )

    def save_stego(self):
        save_it(self.stego, "Сначала выберите оригинал и водяной знак", "Сохранить стегоконтейнер")
    def save_grad(self):
        save_it(self.grad, "Сначала выберите оригинал, водяной знак и ядро", "Сохранить локальный градиент")
    def save_unstego(self):
        save_it(self.extracted, "Сначала выберите стегоконтер, а если включено ядро, то ещё и оригинал", "Сохранить извлечённый watermark")

    def update(self):
        if self.watermark_path:
            size = (512, 512) if self.original is None else self.original.shape
            self.logo, self.watermark = load_logo_with_fit(self.watermark_path, size)
            self.app.set_image(1, self.logo)

            if self.original is not None:
                kernel_name = self.kernel if self.is_adaptive else None
                self.stego, grad = embed_logo_lsb_with_key(self.original, self.password, self.watermark_path, kernel_name=kernel_name)
                self.app.set_image(2, self.stego)
                if grad is not None:
                    grad *= 255
                self.app.set_image(3, grad)
                self.grad = grad

        if self.original is not None and self.stego is not None:
            delta = ((self.original != self.stego) * 255).astype(np.uint8)
            self.app.set_image(4, delta)

        if self.original is not None:
            try:
                self.extracted = extract_logo_lsb_with_key(self.original, self.password, kernel_name=self.kernel, orig_pix=self.orig_pix)
            except ValueError as e:
                if e.args != ("Corrupted container: message length is invalid",):
                    raise e from None
                self.extracted = None
            self.app.set_image(5, self.extracted)

    def choose_original(self, path):
        self.original = load_bmp(path, to_gray=True)
        self.app.set_image(0, self.original)
        self.update()

    def choose_watermark(self, path):
        self.watermark_path = path
        self.update()

    def choose_grad_original(self, path):
        self.orig_pix = load_bmp(path, to_gray=True)
        self.update()

    def setter(self, name):
        def cb(value):
            setattr(self, name, value)
          # print("SET:", name, value)
            self.update()
        cb(None)
        return cb

    def confidence_interval_async(self):
        if self.watermark_path is None:
            messagebox.showerror("Ошибка", "Необходимо указать логотип перед считание доверительного интервала PSNR")
            return
        from multiprocessing import Process
        ci_process = Process(target=MainGUI.confidence_interval, args=(self.password, self.watermark_path))
        ci_process.start()

    @staticmethod
    def confidence_interval(password, watermark_path):
        MAX_I = 255.0
        alpha = 0.05
        results = []

        for base in ("BOSSbase", "medical", "portrait"):
            match base:
                case "BOSSbase": path = "assets/bossbase_containers.zip"
                case "medical":  path = "assets/medical_containers.zip"
                case "portrait": path = "assets/portrait_containers.zip"

            print(f"Анализирую {base}...")
            pixs, _ = bmp_sampler_from_zip(path, filter=False)
            assert len(pixs) == 100

            for kernel_name in (None, *MainGUI.kernel_names):
                psnrs = []
                for orig in pixs:
                    stego, _ = embed_logo_lsb_with_key(orig, password, watermark_path, kernel_name=kernel_name)
                    diff = orig.astype(np.float32) - stego.astype(np.float32)
                    mse = (diff * diff).mean()
                    psnr = float(10.0 * np.log10((MAX_I * MAX_I) / mse) if mse else "inf")
                    psnrs.append(psnr)

                arr = np.array(psnrs)
                avg = float(arr.mean())
                std = float(arr.std(ddof=1))
                low, high = confidence_interval(avg, std, len(arr), alpha)

                results.append((base, "LSB (not adaptive)" if kernel_name is None else kernel_name, std, low, avg, high))

        import csv
        with open("solve_2_psnr_ci_table.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(("base", "mode", "std", "low", "avg", "high"))
            writer.writerows(results)
        print("CSV сохранён: solve_2_psnr_ci_table.csv")

        plot_ci(results, title="Доверительные интервалы PSNR для разных ядер", filename="solve_2_psnr_ci_graph.png")

    def __init__(self):
        self.original  = None
        self.watermark_path = None
        self.watermark = None
        self.logo      = None
        self.stego     = None
        self.orig_pix  = None
        self.FDDSCS()

        self.app = ImageGridGUI(2, 3, opts=self.opts)

    def mainloop(self):
        self.app.mainloop()



if __name__ == "__main__":
    # check_resizer()
    # print(make_random_from_str("meowl").random()) # 0.4981653345863766
    # check_embedder()
    # check_extractor()
    # check_gradient()
    # check_adaptive_embedder()
    # check_adaptive_extractor()
    MainGUI().mainloop()
