# Этот датасет на tensorflow: https://www.tensorflow.org/datasets/catalog/celeb_a
#   Первая зацепка, которую я нашёл, где скачать ВЕСЬ датасет!
#   Здесь описание всех типов данных (т.е, кроме int64 и bool ничего не применяется, но некоторые данные неоправданно занимают целые 8 байтов)
#   Например, всё, что касается положения на картинке, ну прямо самый потолок - это uint16, но точно не int64
# Домашнаяя страница CelebA:  https://mmlab.ie.cuhk.edu.hk/projects/CelebA.html
# Ссылка на самое вкусное:    https://drive.google.com/drive/folders/0B7EVK8r0v71pQ3NzdzRhVUhSams?resourcekey=0-Kpdd6Vctf-AdJYfS55VULA&usp=sharing

from pathlib import Path

from collections import Counter


data_path = Path(__file__).resolve().parent / "data_celeba"
url = "https://drive.google.com/drive/folders/0B7EVK8r0v71pQ3NzdzRhVUhSams?resourcekey=0-Kpdd6Vctf-AdJYfS55VULA&usp=sharing"

BASE_SIZE     = 202_599
IDENTITY_SIZE =  10_177

record_size = 1
# Identity_No (счёт от 0)
pool = tuple([None] * record_size for i in range(202_599))

def identity_reader():
    path = data_path / "identity_CelebA.txt"
    if not path.exists():
        raise FileExistsError(f"Загрузите по пути {path} файл из {url}")

    identity_arr = []
    append = identity_arr.append
    with path.open() as file:
        for idx, line in enumerate(file, start=1):
            name, identity_no = line.split()
            assert name == f"{idx:06d}.jpg"
            append(int(identity_no) - 1)

    # Число картинок и число личностей соответствует данным с домашней страницы CelebA!
    assert len(identity_arr)      == BASE_SIZE
    assert len(set(identity_arr)) == IDENTITY_SIZE
    assert min(identity_arr) == 0 and max(identity_arr) == IDENTITY_SIZE-1  # проверка, что нет пропусков, и счёт начинается с нуля

    for idx, identity_no in enumerate(identity_arr):
        pool[idx][0] = identity_no

    counter = Counter(identity_arr)
    count_counter = Counter(counter.values())
    print(dict(sorted(count_counter.items())))
    # { 1: 44,   2: 324,  3: 245,  4: 221,  5: 221,  6: 207,  7: 183,  8: 176,  9: 187, 10: 202,
    #  11: 199, 12: 165, 13: 176, 14: 210, 15: 172, 16: 219, 17: 173, 18: 217, 19: 288, 20: 1044,
    #  21: 565, 22: 419, 23: 369, 24: 290, 25: 361, 26: 106, 27: 125, 28: 216, 29: 493, 30: 2343,
    #  31: 9,   32: 3,   34: 2, 35: 3}


if __name__ == "__main__":
    identity_reader()
