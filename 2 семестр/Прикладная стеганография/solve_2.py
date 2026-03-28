import numpy as np # pip install numpy
from PIL import Image # pip install pillow

from solve_1 import bmp_sampler_from_zip, insert_k_layer, read_k_layer

from functools import lru_cache
import os



# Благодаря @lru_cache функция автоматически кэширует результат уменьшения логотипа.
# Это позволяет вызывать её прямо внутри методов встраивания, не вынося расчёт
# capacity_bits и загрузку логотипа в отдельный блок.
# Вся логика остаётся локальной, а повторные вызовы становятся мгновенными.
@lru_cache
def load_logo_with_fit(logo_path: str, target_shape: tuple[int, int], layers=1) -> bytes:
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



if __name__ == "__main__":
    check_resizer()
