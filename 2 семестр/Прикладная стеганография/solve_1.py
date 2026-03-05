import numpy as np

from bitmap_driver import read_bmp, load_bmp, save_bmp

import zipfile
import os
import random



def get_k_layer(pix, k):
    shifted = pix >> (k - 1)
    if k != 8: shifted &= 1
    return shifted

def insert_k_layer(pix, k, message):
    W, H = pix.shape
    capacity = W * H - 32
    need = len(message) * 8
    if capacity < need:
        raise ValueError(f"Capacity is {capacity}, but required is {need}") 

    bits = np.unpackbits(np.frombuffer(message, dtype=np.uint8))
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

def read_k_layer(pix, k):
    bits = get_k_layer(pix, k)
    W, H = pix.shape
    bits = bits.reshape(W * H)
    need = 0
    for i in range(32):
        need |= int(bits[-1-i]) << i
    # print(need, len(bits)) # 262112 262144
    if need > len(bits) - 32:
        raise ValueError("Corrupted container: message length is invalid")
    message = np.packbits(bits[:need]).tobytes()
    return message



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



def bmp_sampler_from_zip(path, count):
    pixs = []
    with zipfile.ZipFile(path, "r") as zip:
        file_list = zip.namelist()
        assert len(file_list) >= count
        sample = random.sample(file_list, count)

        for name in sample:
            with zip.open(name, "r") as file:
                pix = read_bmp(file, debug=False, to_gray=True)
            pixs.append(pix)
    return pixs

def main2(path, count):
    pixs = bmp_sampler_from_zip(path, count)
    print(pixs)



if __name__ == "__main__":
    path     = "bossbase_containers.zip"
    msg_path = "Harry Potter and the Philosopher's Stone.txt"
    count    = 8

    # main(path, msg_path)
    main2(path, count)
