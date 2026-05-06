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
    diffs = []
    for idx, Sk in enumerate(subs, start=1):
        if idx == k_ref:
            diffs.append(None)  # для reference разности нет
        else:
            diffs.append(S_ref - Sk)
    return diffs

def shift_histograms(subs, diffs, S_ref, k_ref, L):
    """
    Освобождаем диапазона [-L, L] в разностях.
    Меняем только destination subimages (subs[k]), reference не трогаем.
    Возвращаем:
        new_subs  — модифицированные S_des
        new_diffs — новые разности D'
    """
    new_subs = subs.copy()
    new_diffs = diffs.copy()

    shift = L + 1

    for idx, (Sk, Dk) in enumerate(zip(subs, diffs), start=1):
        if idx == k_ref:
            continue  # reference не трогаем

        if Dk is None:
            continue

        # маски
        mask_pos = Dk >= shift      # H >= L+1
        mask_neg = Dk <= -shift     # H <= -L-1

        # создаём копию Sk
        Sk_new = Sk.copy()

        # модифицируем только destination subimage
        Sk_new[mask_pos] -= shift
        Sk_new[mask_neg] += shift

        # сохраняем
        new_subs[idx - 1] = Sk_new
        new_diffs[idx - 1] = S_ref - Sk_new

    return new_subs, new_diffs

def embed_bits(subs, diffs, S_ref, k_ref, data_bits, L):
    """
    subs, diffs — после шага 4 (shift_histograms)
    data_bits — массив 0/1
    L — максимальный embedding level
    """

    subs_new = subs.copy()
    diffs_new = diffs.copy()

    bit_pos = 0
    total_bits = len(data_bits)

    for level in range(L, -1, -1):

        shift_big = level + 1
        shift_small = level

        for idx, (Sk, Dk) in enumerate(zip(subs_new, diffs_new), start=1):
            if idx == k_ref or Dk is None:
                continue

            # маски для разностей = ±level
            mask_pos = (Dk == level)
            mask_neg = (Dk == -level)

            # объединяем координаты
            coords = np.argwhere(mask_pos | mask_neg)
            if coords.size == 0:
                continue

            # сколько можем встроить
            need = min(coords.shape[0], total_bits - bit_pos)
            if need <= 0:
                return subs_new, diffs_new, bit_pos

            coords = coords[:need]
            bits = data_bits[bit_pos:bit_pos + need]
            Sk_new = Sk.copy()

            # разности для выбранных координат
            D_vals = Dk[coords[:, 0], coords[:, 1]]

            # маски внутри выбранных координат
            is_pos = (D_vals == level)
            is_neg = ~is_pos

            bit1 = (bits == 1)
            bit0 = ~bit1

            # +level
            # bit=1 → -(level+1)
            # bit=0 → -level
            pos_idx = coords[is_pos]
            if pos_idx.size > 0:
                # bit=1
                idx1 = pos_idx[bit1[is_pos]]
                Sk_new[idx1[:, 0], idx1[:, 1]] -= shift_big
                # bit=0
                idx0 = pos_idx[bit0[is_pos]]
                Sk_new[idx0[:, 0], idx0[:, 1]] -= shift_small

            # -level
            # bit=1 → +(level+1)
            # bit=0 → +level
            neg_idx = coords[is_neg]
            if neg_idx.size > 0:
                # bit=1
                idx1 = neg_idx[bit1[is_neg]]
                Sk_new[idx1[:, 0], idx1[:, 1]] += shift_big
                # bit=0
                idx0 = neg_idx[bit0[is_neg]]
                Sk_new[idx0[:, 0], idx0[:, 1]] += shift_small

            # обновляем
            subs_new[idx - 1] = Sk_new
            diffs_new[idx - 1] = S_ref - Sk_new

            bit_pos += need
            if bit_pos >= total_bits:
                return subs_new, diffs_new, bit_pos

    return subs_new, diffs_new, bit_pos

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
    subs_emb, diffs_emb, used_bits = embed_bits(subs_shifted, diffs_shifted, S_ref, k_ref, data_bits, L)

    #   Step.6: обратный Step.1
    Iw = reconstruct_image(subs_emb, du, dv)

    return Iw, diffs_emb, used_bits



def main():
    pix_path = os.path.join("assets", "origin.bmp")
    data_path = os.path.join("assets", "Harry Potter and the Philosopher's Stone.txt")

    pix = load_bmp(pix_path, to_gray=True)
    with open(data_path, "rb") as file:
        data = file.read()

    stego, diffs_emb, used_bits = embed_data(pix, data, 2, 2, 0)
    print("used bits:", used_bits)
    for item in diffs_emb:
        print("d:", item.shape if item is not None else None)
    """
d: None
d: (256, 256)
d: (256, 256)
d: (256, 256)
Слишком огромный ключ для извлечения исходного контейнера
Значит не применимо для реальных условий
Да и задание не требует извлечения оригинального контейнера
    """

    stego_path = os.path.join("assets", "original_Kim.bmp")
    save_bmp(stego_path, stego, mode="gray")



if __name__ == "__main__":
    main()
