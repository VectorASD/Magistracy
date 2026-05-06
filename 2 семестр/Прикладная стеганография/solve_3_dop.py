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
    Схема встраивания на уровне level (level идёт от L до 0):
        D == +level, bit=0  →  Sk -= level      →  новый D =  0
        D == +level, bit=1  →  Sk -= (level+1)  →  новый D = -(level+1)
        D == -level, bit=0  →  Sk += level      →  новый D =  0
        D == -level, bit=1  →  Sk += (level+1)  →  новый D = +(level+1)
    """
    subs_new  = subs.copy()
    diffs_new = diffs.copy()
 
    bit_pos    = 0
    total_bits = len(data_bits)
 
    for level in range(L, -1, -1):
        for idx, (Sk, Dk) in enumerate(zip(subs_new, diffs_new), start=1):
            if idx == k_ref or Dk is None:
                continue
 
            coords = np.argwhere((Dk == level) | (Dk == -level))
            if coords.size == 0:
                continue
 
            need = min(coords.shape[0], total_bits - bit_pos)
            if need <= 0:
                return subs_new, bit_pos
 
            coords = coords[:need]
            bits   = data_bits[bit_pos : bit_pos + need]
            Sk_new = Sk.copy()
 
            D_vals = Dk[coords[:, 0], coords[:, 1]]
            is_pos = (D_vals == level)
            is_neg = ~is_pos
            bit1   = (bits == 1)
            bit0   = ~bit1
 
            pos_idx = coords[is_pos]
            if pos_idx.size > 0:
                Sk_new[pos_idx[bit1[is_pos]][:, 0], pos_idx[bit1[is_pos]][:, 1]] -= (level + 1)
                Sk_new[pos_idx[bit0[is_pos]][:, 0], pos_idx[bit0[is_pos]][:, 1]] -= level
 
            neg_idx = coords[is_neg]
            if neg_idx.size > 0:
                Sk_new[neg_idx[bit1[is_neg]][:, 0], neg_idx[bit1[is_neg]][:, 1]] += (level + 1)
                Sk_new[neg_idx[bit0[is_neg]][:, 0], neg_idx[bit0[is_neg]][:, 1]] += level
 
            subs_new[idx - 1]  = Sk_new
            diffs_new[idx - 1] = S_ref - Sk_new
 
            bit_pos += need
            if bit_pos >= total_bits:
                return subs_new, bit_pos
 
    return subs_new, bit_pos

def extract_bits(diffs, k_ref, L, max_bits: int):
    bits_list = []
    collected = 0
    for level in range(L, -1, -1):
        sentinel = level + 1          # D = ±sentinel кодирует бит 1
        for idx, Dk in enumerate(diffs, start=1):
            if idx == k_ref or Dk is None:
                continue

            # Маски для пикселей, несущих данные на этом уровне
            mask0 = (Dk == 0)                              # бит 0
            mask1 = (Dk == sentinel) | (Dk == -sentinel)   # бит 1
            valid = mask0 | mask1
            if not np.any(valid):
                continue

            # Извлекаем биты в row-major порядке (как это делал np.argwhere)
            # mask0[valid] даёт True для битов 0 и False для битов 1
            bits = np.where(mask0[valid], 0, 1).astype(np.uint8)

            bits_list.append(bits)
            collected += bits.size
            if collected >= max_bits:
                # Склеиваем и обрезаем до нужной длины
                all_bits = np.concatenate(bits_list)
                return all_bits[:max_bits]

    # Если прошли все уровни, но набрали меньше max_bits
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



def embed_data(I: np.ndarray, data: bytes, du: int, dv: int, L: int):
    I[I == 255] = 254
    I[I == 0]   = 1
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



if __name__ == "__main__":
    main()
