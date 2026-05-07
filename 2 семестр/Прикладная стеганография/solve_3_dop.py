import numpy as np  # pip install numpy

from bitmap_driver import load_bmp, save_bmp

import os



def subsample_all(I: np.ndarray, du: int, dv: int):
    """
    Генерирует все S_k для заданных Δu=du, Δv=dv.
    Полностью векторизовано, без циклов по i,j.
    Так по мне, это обычная нарезка на тайлы (плитку).
    """
    H, W = I.shape
    K = du * dv

    # Размеры субизображений
    h_sub = H // dv
    w_sub = W // du

    # Координатные сетки для i,j
    i = np.arange(h_sub)[:, None]  # shape (h_sub, 1)
    j = np.arange(w_sub)[None, :]  # shape (1, w_sub)

    subs = []
    for k in range(1, K + 1):
        off_v, off_u = divmod(k - 1, du)  # floor((k-1)/Δu), (k-1) mod Δu

        # Векторизованные координаты
        src_i = i * dv + off_v  # shape (h_sub, w_sub)
        src_j = j * du + off_u  # shape (h_sub, w_sub)

        # Берём значения из исходного изображения
        Sk = I[src_i, src_j]
        subs.append(Sk)

    return subs

def choose_reference_index(du: int, dv: int) -> int:
    """
    Вычисляем индекс k_ref для опорного субизображения S_ref.
    Индексация: k = 1..(du*dv)
    """
    a = int(np.round(du / 2 - 1))
    b = int(np.round(dv / 2))
    return a * dv + b  # k_ref

def choose_reference(subs, du, dv):
    """
    subs — список S_k, полученный из subsample_all()
    Возвращаем (S_ref, k_ref)
    """
    k_ref = choose_reference_index(du, dv)
    return subs[k_ref - 1], k_ref

def build_differences(subs, S_ref, k_ref):
    """
    Строим разностные изображения D_k = S_ref - S_k
    для всех k != k_ref.
    Возвращаем список D_k в том же порядке, что и subs.
    """
    diffs = [None if idx == k_ref else S_ref - Sk # для reference разности нет
             for idx, Sk in enumerate(subs, start=1)]
    return diffs

def shift_histograms(subs, diffs, S_ref, k_ref, L):
    new_subs = subs.copy()
    new_diffs = diffs.copy()
    shift = L + 1
 
    for idx, (Sk, Dk) in enumerate(zip(subs, diffs), start=1):
        if idx == k_ref or Dk is None:
            continue
 
        Sk_new = Sk.copy()
        Sk_new[Dk >= shift]  -= shift
        Sk_new[Dk <= -shift] += shift
 
        new_subs[idx - 1]  = Sk_new
        new_diffs[idx - 1] = S_ref - Sk_new
 
    return new_subs, new_diffs
 
def embed_bits(subs, diffs, S_ref, k_ref, data_bits, L):
    """
    Многоуровневое встраивание (L >= 0) без пересечения диапазонов.
    level > 0:
        D = +level, bit 0 → D' = +level      (без изменений)
        D = +level, bit 1 → D' = +(level+L+1) (Sk -= L+1)
        D = -level, bit 0 → D' = -level
        D = -level, bit 1 → D' = -(level+L+1) (Sk += L+1)
    level = 0:
        D = 0, bit 0 → D' = 0
        D = 0, bit 1 → D' = -(L+1)            (Sk += L+1)
    При L=0 поведение совпадает с исходным.
    """
    subs_new = list(subs)
    diffs_new = list(diffs)
    bit_pos = 0
    total_bits = len(data_bits)
    Lp1 = L + 1

    for level in range(L, -1, -1):
        for idx, (Sk, Dk) in enumerate(zip(subs_new, diffs_new), start=1):
            if idx == k_ref or Dk is None:
                continue

            # Маска контейнеров текущего уровня
            if level > 0:
                mask_target = (Dk == level) | (Dk == -level)
            else:
                mask_target = (Dk == 0)

            if not np.any(mask_target):
                continue

            coords = np.argwhere(mask_target)  # row‑major, как исходный обход
            if coords.size == 0:
                continue

            # Фильтруем пиксели, которые могут безопасно принять бит 1
            D_vals = Dk[coords[:, 0], coords[:, 1]]
            valid = np.ones(coords.shape[0], dtype=bool)
            if level > 0:
                pos_mask = D_vals == level
                neg_mask = D_vals == -level
                # Для положительного D: нужно Sk >= L+1 (чтобы не уйти в минус)
                valid[pos_mask] = Sk[coords[pos_mask, 0], coords[pos_mask, 1]] >= Lp1
                # Для отрицательного D: нужно Sk <= 255 - (L+1)
                valid[neg_mask] = Sk[coords[neg_mask, 0], coords[neg_mask, 1]] <= 255 - Lp1
            else:  # level == 0, бит 1 даёт Sk += L+1 (D' отрицательное)
                valid[:] = Sk[coords[:, 0], coords[:, 1]] <= 255 - Lp1

            coords = coords[valid]
            if coords.size == 0:
                continue

            need = min(coords.shape[0], total_bits - bit_pos)
            if need <= 0:
                return subs_new, bit_pos

            coords = coords[:need]
            bits = data_bits[bit_pos:bit_pos + need]
            Sk_new = Sk.copy()
            D_vals = Dk[coords[:, 0], coords[:, 1]]

            if level > 0:
                is_pos = D_vals == level
                is_neg = ~is_pos
                bit1 = (bits == 1)

                pos_idx = coords[is_pos]
                if pos_idx.size > 0:
                    pos_bit1 = bit1[is_pos]
                    if np.any(pos_bit1):
                        Sk_new[pos_idx[pos_bit1, 0], pos_idx[pos_bit1, 1]] -= Lp1

                neg_idx = coords[is_neg]
                if neg_idx.size > 0:
                    neg_bit1 = bit1[is_neg]
                    if np.any(neg_bit1):
                        Sk_new[neg_idx[neg_bit1, 0], neg_idx[neg_bit1, 1]] += Lp1
            else:  # level == 0
                bit1 = (bits == 1)
                if np.any(bit1):
                    Sk_new[coords[bit1, 0], coords[bit1, 1]] += Lp1

            subs_new[idx - 1] = Sk_new
            diffs_new[idx - 1] = S_ref - Sk_new
            bit_pos += need
            if bit_pos >= total_bits:
                return subs_new, bit_pos

    return subs_new, bit_pos

def extract_bits(diffs, k_ref, L, max_bits: int):
    """
    Извлечение, зеркальное к embed_bits.
    level > 0:
        бит 0: D == ±level
        бит 1: D == ±(level + L + 1)
    level = 0:
        бит 0: D == 0
        бит 1: D == -(L+1)
    """
    bits_list = []
    collected = 0
    Lp1 = L + 1

    for level in range(L, -1, -1):
        for idx, Dk in enumerate(diffs, start=1):
            if idx == k_ref or Dk is None:
                continue

            if level > 0:
                mask0 = (Dk == level) | (Dk == -level)
                mask1 = (Dk == level + Lp1) | (Dk == -(level + Lp1))
            else:
                mask0 = (Dk == 0)
                mask1 = (Dk == -Lp1)

            valid = mask0 | mask1
            if not np.any(valid):
                continue

            # mask0[valid] → True для битов 0, False для битов 1
            bits = np.where(mask0[valid], 0, 1).astype(np.uint8)
            bits_list.append(bits)
            collected += bits.size
            if collected >= max_bits:
                all_bits = np.concatenate(bits_list)
                return all_bits[:max_bits]

    if bits_list:
        all_bits = np.concatenate(bits_list)
        return all_bits[:max_bits]
    return np.array([], dtype=np.uint8)

def reconstruct_image(subs, du, dv):
    """
    Обратная субдискретизация.
    Просто складываем плитку назад в картинку.
    """

    # subs[k] имеет размер (H/dv, W/du)
    h_sub, w_sub = subs[0].shape
    H = h_sub * dv
    W = w_sub * du

    Iw = np.zeros((H, W), dtype=subs[0].dtype)

    K = du * dv

    for k in range(1, K + 1):
        off_v = (k - 1) // du
        off_u = (k - 1) % du

        Sk = subs[k - 1]

        # Вставляем Sk обратно в Iw
        Iw[off_v:H:dv, off_u:W:du] = Sk

    return Iw



def preprocess_for_embed(I, L):
    I = I.astype(np.int16)
    low = L + 1
    high = 255 - (L + 1)
    I[I < low] = low
    I[I > high] = high
    return I

def embed_data(I: np.ndarray, data: bytes, du: int, dv: int, L: int):
    I = preprocess_for_embed(I, L)
    I = I.astype(np.int16)  # без этого сломаются разности

    data_bits = np.unpackbits(np.frombuffer(data, dtype=np.uint8)).astype(np.uint8)

    #   Step.1: субдискретизация
    subs = subsample_all(I, du, dv)  # список S_k

    #   Step.2: выбор reference
    S_ref, k_ref = choose_reference(subs, du, dv)

    #   Step.3: разностные изображения
    diffs = build_differences(subs, S_ref, k_ref)

    #   Step.4: сдвиг гистограмм разностей
    subs_shifted, diffs_shifted = shift_histograms(subs, diffs, S_ref, k_ref, L)

    #   Step.5: встраивание битов
    subs_emb, used_bits = embed_bits(subs_shifted, diffs_shifted, S_ref, k_ref, data_bits, L)

    #   Step.6: обратный Step.1
    Iw = reconstruct_image(subs_emb, du, dv)

    Iw = np.clip(Iw, 0, 255).astype(np.uint8)
    return Iw, used_bits

def extract_data(Iw: np.ndarray, du: int, dv: int, L: int, used_bits: int):
    Iw = Iw.astype(np.int16)  # без этого сломаются разности

    #   Step.1: скопировать сигнатуру для этой функции из embed_data :)
    # Вместо I и data, очевидно, будет Iw. Авторы du, dv и L назвали ключём
    # На деле, ключём ещё считается функция choose_reference_index, т.к. она решает, какой тайл будет ведущим

    #   Step.2: и так очевидный шаг: сделать плитку
    subs = subsample_all(Iw, du, dv)

    #   Step.3: снова очевидный шаг: тот же самый эталонный тайл
    S_ref, k_ref = choose_reference(subs, du, dv)

    #   Step.4: менее очевидный шаг из-за наличия встроенных данных, но допустим
    diffs = build_differences(subs, S_ref, k_ref)

    #   Step.5: извлечение битов
    target = used_bits // 8 * 8
    bits = extract_bits(diffs, k_ref, L, max_bits=target)

    return np.packbits(bits).tobytes()



def main():
    pix_path = os.path.join("assets", "origin.bmp")
    data_path = os.path.join("assets", "Harry Potter and the Philosopher's Stone.txt")

    pix = load_bmp(pix_path, to_gray=True)
    with open(data_path, "rb") as file:
        data = file.read()

    du, dv, L = 2, 2, 0

    stego, used_bits = embed_data(pix, data, du, dv, L)

    stego_path = os.path.join("assets", "original_Kim.bmp")
    save_bmp(stego_path, stego, mode="gray")

    unstego = extract_data(stego, du, dv, L, used_bits)

    print(unstego.decode("windows-1251", errors="replace"))
    print("\nused bits:", used_bits)
    print("MATCH:", unstego == data[:len(unstego)])



from solve_1 import bmp_sampler_from_zip
from utils import confidence_interval
from gui import plot_ci

def PSNR():
    """
    сразу же 15 графиков располагать в одной картинке ну такое себе
    по этому будет 3 картинки по 5 графиков (различные варианты du, dv)
    по оси X: L
    по оси Y: PSNR и ДИ
    """

    data_path = os.path.join("assets", "Harry Potter and the Philosopher's Stone.txt")
    with open(data_path, "rb") as file:
        data = file.read()

    MAX_I = 255.0
    alpha = 0.05

    for base in ("BOSSbase", "medical", "portrait"):
        match base:
            case "BOSSbase": base_name = "bossbase_containers.zip"
            case "medical":  base_name = "medical_containers.zip"
            case "portrait": base_name = "portrait_containers.zip"
        path = os.path.join("assets", base_name)

        print(f"Анализирую {base}...")
        pixs, filenames = bmp_sampler_from_zip(path, filter=False)
        assert len(pixs) == 100

        results = []
        for du, dv in ((2, 2), (3, 3), (4, 4), (2, 3), (3, 2)):
            for L in range(10):
                psnrs = []
                capacities = []
                for i, orig in enumerate(pixs):
                  # print(f"  {i+1}/100")

                    stego, used_bits = embed_data(orig, data, du, dv, L)

                    diff = orig.astype(np.float32)[:stego.shape[0], :stego.shape[1]] - stego.astype(np.float32)
                    mse = (diff * diff).mean()
                    psnr = float(10.0 * np.log10((MAX_I * MAX_I) / mse) if mse else "inf")
                    psnrs.append(psnr)
                    capacities.append(used_bits)

                arr = np.array(psnrs)
                avg = float(arr.mean())
                std = float(arr.std(ddof=1))
                low, high = confidence_interval(avg, std, len(arr), alpha)
                results.append(((du, dv), L, std, low, avg, high, np.mean(capacities)))
                print("key:", du, dv, L, "| avg capacity:", np.mean(capacities), "bits.")

        import csv
        with open(f"solve_3_Kim_{base}_psnr_ci_table.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(("(du, dv)", "L", "std", "low", "avg", "high", "avg_capacity"))
            writer.writerows(results)
        print(f"CSV сохранён: solve_3_Kim_{base}_psnr_ci_table.csv")

        plot_ci(results, title=f"Доверительные интервалы PSNR для гистограмм Кима ({base})", filename=f"solve_3_Kim_{base}_psnr_ci_graph.png", xlabel="L")



if __name__ == "__main__":
  # main()
    PSNR()
