import numpy as np # pip install numpy
from PIL import Image # pip install pillow

from bitmap_driver import save_bmp, load_bmp
from solve_1 import bmp_sampler_from_zip, insert_k_layer, read_k_layer
from utils import gradient_from_name
from gui import ImageGridGUI

from functools import lru_cache
import os
from hashlib import pbkdf2_hmac



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

    # Логотип и так помещается
    if orig_bits <= capacity_bits:
        return np.array(img).tobytes()

    target_pixels = capacity_bits // (3 * 8) # Требуемая площадь
    side = int(target_pixels ** 0.5)         # Новая сторона (квадрат)
    side = max(1, side)                      # Минимум 1×1

    # Pillow рекомендует: Image.LANCZOS — лучший для уменьшения (высокое качество + антиалиасинг)
    logo = img.resize((side, side), Image.LANCZOS)

    # Превращаем в байты
    watermark = np.array(logo, dtype=np.uint8)
    if reshape:
        watermark = watermark.reshape(-1) # arr.reshape(-1) <-> arr.reshape(arr.size)
    print("Допустимо: ", capacity_bits,        "bits") # 262112 bits
    print("Получилось:", watermark.nbytes * 8, "bits") # 259584 bits
    assert watermark.nbytes * 8 <= capacity_bits
    return logo, watermark

def check_resizer():
    logo_path = "my_logo.png"
    pixs = bmp_sampler_from_zip("assets/bossbase_containers.zip", count=1)
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

def embed_logo_lsb_with_key(pix: np.ndarray, key: str, logo_path: str) -> np.ndarray:
    """
    Метод 1: LSB‑встраивание с секретным ключом.
    Логотип автоматически уменьшается до максимально допустимого размера.
    """
    assert pix.ndim == 2

    _, watermark = load_logo_with_fit(logo_path, pix.shape)
    random = make_random_from_str(key)

    idxs = np.arange(watermark.size)
    random.shuffle(idxs)
    # print(idxs) # [ 52107 229168 135349 ...   6164 246636  33432]
    shuffled = watermark[idxs]
    # side = round((shuffled.size // 3) ** 0.5)
    # img = shuffled.reshape((side, side, 3))
    # Image.fromarray(img).save("шум.png")

    stego = insert_k_layer(pix, k=1, message=shuffled)
    return stego

def extract_logo_lsb_with_key(pix: np.ndarray, key: str):
    "Извлекает логотип, встроенный методом 1 (LSB + перестановка индексов)."

    assert pix.ndim == 2

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
    pix = bmp_sampler_from_zip("assets/bossbase_containers.zip", count=1)[0]
    stego = embed_logo_lsb_with_key(pix, "meowl", "my_logo.png")
    save_bmp("watermarked.bmp", stego, mode="gray")

def check_extractor():
    stego = load_bmp("watermarked.bmp", to_gray=True)
    extracted = extract_logo_lsb_with_key(stego, "meowl")
    # Image.fromarray(extracted).save("unwatermarked.png")
    compare_logos("my_logo.png", stego, extracted)



def overlay_gradient(pix, grad):
    # Нормализация градиента
    g = grad - grad.min()
    g = g / (g.max() + 1e-9) # защита от деления на 0

    # Растянуть до размера исходного изображения
    H, W = pix.shape
    h, w = g.shape
    pad_y = (H - h) // 2
    pad_x = (W - w) // 2

    mask = np.zeros(pix.shape, dtype=np.float32)
    mask[pad_y:pad_y+h, pad_x:pad_x+w] = g

    # Наложение
    return (pix.astype(np.float32) * mask).clip(0, 255).astype(np.uint8)

def check_gradient():
    pix = bmp_sampler_from_zip("assets/bossbase_containers.zip", count=1)[0]
    grad = gradient_from_name(pix, "diff")
    out = overlay_gradient(pix, grad)

    ImageGridGUI(1, 3, (pix, grad, out)).mainloop()



if __name__ == "__main__":
    # check_resizer()
    # print(make_random_from_str("meowl").random()) # 0.4981653345863766
    # check_embedder()
    # check_extractor()
    check_gradient()
