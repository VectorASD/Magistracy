# Точка отправления: https://telegra.ph/30-samyh-krupnyh-datasetov-dlya-mashinnogo-obucheniya-v-TensorFlow-11-25
# Этот датасет на tensorflow: https://www.tensorflow.org/datasets/catalog/celeb_a
#   Первая зацепка, которую я нашёл, где скачать ВЕСЬ датасет!
#   Здесь описание всех типов данных (т.е, кроме int64 и bool ничего не применяется, но некоторые данные неоправданно занимают целые 8 байтов)
#   Например, всё, что касается положения на картинке, ну прямо самый потолок - это uint16, но точно не int64
# Домашнаяя страница CelebA:  https://mmlab.ie.cuhk.edu.hk/projects/CelebA.html
# Ссылка на самое вкусное:    https://drive.google.com/drive/folders/0B7EVK8r0v71pQ3NzdzRhVUhSams?resourcekey=0-Kpdd6Vctf-AdJYfS55VULA&usp=sharing



import matplotlib.pyplot as plt  # pip install matplotlib
from PIL import Image            # pip install Pillow

from pathlib import Path
from collections import Counter
from functools import lru_cache

@lru_cache(maxsize=1)
def load_TF():
    import os
    os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
    #   иначе будет ошибка вида:
    # oneDNN custom operations are on. You may see slightly different numerical results due to floating-point round-off
    # errors from different computation orders. To turn them off, set the environment variable `TF_ENABLE_ONEDNN_OPTS=0`.

    print("Загрузка TF... ", end="", flush=True)
    import tensorflow as tf          # pip install tensorflow==2.20
    print("DONE")
    return tf



base_path = Path(__file__).resolve().parent
data_path = base_path / "data_celeba"
img_path  = base_path / "img_celeba"

url  = "https://drive.google.com/drive/folders/0B7EVK8r0v71pQ3NzdzRhVUhSams?resourcekey=0-Kpdd6Vctf-AdJYfS55VULA&usp=sharing"
url2 = "https://storage.googleapis.com/tensorflow/keras-applications/mobilenet_v3/weights_mobilenet_v3_large_224_1.0_float.h5"

base_model_path = base_path / "weights_mobilenet_v3_large_224_1.0_float.h5"

BASE_SIZE     = 202_599
IDENTITY_SIZE =  10_177

# 0: name
# 1: Identity_No (счёт от 0)
pool = tuple([f"{idx:06d}.jpg", None] for idx in range(1, BASE_SIZE+1))
id2pools = tuple([] for i in range(IDENTITY_SIZE))

def check_exists(path):
    if not path.exists():
        raise FileExistsError(f"Загрузите файл сюда '{path}' по ссылке {url}")


def identity_reader():
    path = data_path / "identity_CelebA.txt"
    check_exists(path)

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
        pool[idx][1] = identity_no
        id2pools[identity_no].append(pool[idx])

    identity_arr_analyzer(identity_arr)



best_ids = None

def identity_arr_analyzer(identity_arr):
    global best_ids
    counter = Counter(identity_arr)
    count_counter = Counter(counter.values())
  # print(dict(sorted(count_counter.items())))
    # { 1: 44,   2: 324,  3: 245,  4: 221,  5: 221,  6: 207,  7: 183,  8: 176,  9: 187, 10: 202,
    #  11: 199, 12: 165, 13: 176, 14: 210, 15: 172, 16: 219, 17: 173, 18: 217, 19: 288, 20: 1044,
    #  21: 565, 22: 419, 23: 369, 24: 290, 25: 361, 26: 106, 27: 125, 28: 216, 29: 493, 30: 2343,
    #  31: 9,   32: 3,   34: 2, 35: 3}
    count_per_id, id_count = max(count_counter.items(), key=lambda pair: pair[1])
    assert count_per_id == 30
    assert id_count     == 2343
    best_ids = sorted(id_no for id_no, count in counter.items() if count == count_per_id)
    assert len(best_ids) == id_count

def show_persone(index: int):
    plt.figure(figsize=(12, 8))
    for index, pool in enumerate(id2pools[best_ids[index]], start=1):
        plt.subplot(5, 6, index)
        image = read_image(pool[0])
        print(pool[0], image.size)
        plt.imshow(image)
        plt.axis('off')
        plt.title(f'Image {pool[0]}')

    plt.tight_layout()
    plt.show()



def read_image(name: str):
    path = img_path / name
    check_exists(path)

    image = Image.open(path)
    assert image.mode == "RGB" and len(image.size) == 2
    return image



def load_mode():
    tf = load_TF()  # lazy loader
    print("applications:", tf.keras.applications.__file__)  # Выяснилось, что ещё есть MobileNetV3Small и MobileNetV3Large, что ЕЩЁ лучше и быстрее обучается!!!

    if not base_model_path.exists():
        raise FileExistsError(f"Загрузите файл сюда '{base_model_path}' по ссылке {url2}")

    # 1. Создаём архитектуру без весов
    print("Выделение модели... ", end="", flush=True)
    model = tf.keras.applications.MobileNetV3Large(
        weights=None,               # не загружаем предобученные веса сразу
        input_shape=(224, 224, 3),  # размер входного изображения (ширина, высота, каналы RGB)
        include_top=True,           # оставить полносвязный классификатор (1000 классов ImageNet)
        alpha=1.0                   # множитель ширины: 1.0 = полная модель
    )
    print("DONE")

    # 2. Загружаем скачанные веса
    print("Загрузка весов... ", end="", flush=True)
    model.load_weights(base_model_path)
    print("DONE")



if __name__ == "__main__":
    identity_reader()
    show_persone(3)
    load_mode()



"""
Оценка времени обучения на RTX 5050 (Blackwell) в сравнении с RTX 3050 (Ampere)
Основано на FP32 производительности: RTX 3050 ~9.1 TFLOPS, RTX 5050 ~13.1 TFLOPS
и реальных тестах AI-приложений, где RTX 5050 быстрее RTX 3050 в 1.6–1.8 раза

Вот сравнение популярных вариантов:

   Модель       | Размер (параметров) | RTX 3050 (1 эпоха) | RTX 5050 (1 эпоха) | Ускорение
MobileNetV2     |               3.5M  |         ~8-10 сек  |         ~4- 6 сек  |    ~1.8x
EfficientNetB0  |               5.3M  |         15-25 сек  |          8-14 сек  |    ~1.8x
ResNet-18       |              11.7M  |         20-30 сек  |         11-17 сек  |    ~1.8x

MobileNetV2: Чемпион по эффективности.

Семейство нейросетей MobileNet было создано в Google специально для того, чтобы эффективно
работать на устройствах с ограниченными ресурсами. Вторая версия, MobileNetV2, стала
серьёзным шагом вперёд: инженеры предложили архитектуру с «инвертированными остаточными
блоками и линейными узкими местами» (inverted residuals and linear bottlenecks).

Этот подход позволил значительно снизить требования к памяти и при этом сделать вычисления в
2 раза быстрее, а саму модель — на 30-40% быстрее на смартфонах вроде Google Pixel по
сравнению с предшественником. Именно благодаря таким характеристикам, как малое
количество параметров и высокое быстродействие, MobileNetV2 идеально подходит для нашей
задачи по обучению на RTX 3050.
"""



"""
Полная таблица совместимости TensorFlow, Python, CUDA, cuDNN и архитектур GPU
(данные основаны на официальной документации TensorFlow, NVIDIA, 
а также проверены через https://www.tensorflow.org/install/source#gpu 
и https://developer.nvidia.com/cuda-gpus)

Версия TF   | Python     | CUDA   | cuDNN   | Поддерживаемые GPU (архитектура)
2.21        | 3.9–3.13   | 12.5   | 9.3     | Ampere (8.x), Ada Lovelace (8.9), Hopper (9.x), Blackwell (12.x)
2.20        | 3.9–3.13   | 12.5   | 9.3     | Ampere (8.x), Ada Lovelace (8.9), Hopper (9.x), Blackwell (12.x)
2.19        | 3.9–3.12   | 12.5   | 9.3     | Ampere (8.x), Ada Lovelace (8.9), Hopper (9.x), Blackwell (12.x)
2.18        | 3.9–3.12   | 12.6   | 9.3–9.6 | Ampere (8.x), Ada Lovelace (8.9), Hopper (9.x)
2.17        | 3.9–3.12   | 12.6   | 9.3–9.6 | Ampere (8.x), Ada Lovelace (8.9), Hopper (9.x)
2.16        | 3.9–3.12   | 12.6   | 9.3–9.6 | Ampere (8.x), Ada Lovelace (8.9), Hopper (9.x)
2.15        | 3.9–3.11   | 12.2   | 8.9     | Ampere (8.x), Ada Lovelace (8.9), Turing (7.5)
2.14        | 3.9–3.11   | 11.8   | 8.6     | Ampere (8.x), Turing (7.5), Pascal (6.x)
2.13        | 3.8–3.11   | 11.8   | 8.6     | Ampere (8.x), Turing (7.5), Pascal (6.x)
2.12        | 3.8–3.11   | 11.8   | 8.6     | Ampere (8.x), Turing (7.5), Pascal (6.x)
2.11        | 3.7–3.11   | 11.2   | 8.1     | Ampere (8.x), Turing (7.5), Pascal (6.x)
2.10        | 3.7–3.10   | 11.2   | 8.1     | Ampere (8.x), Turing (7.5), Pascal (6.x)
2.9         | 3.7–3.10   | 11.2   | 8.1     | Ampere (8.x), Turing (7.5), Pascal (6.x)
2.8         | 3.7–3.10   | 11.2   | 8.1     | Ampere (8.x), Turing (7.5), Pascal (6.x)
2.7         | 3.7–3.10   | 11.2   | 8.1     | Ampere (8.x), Turing (7.5), Pascal (6.x)
2.6         | 3.6–3.9    | 11.2   | 8.1     | Ampere (8.x), Turing (7.5), Pascal (6.x)
2.5         | 3.6–3.9    | 11.2   | 8.1     | Ampere (8.x), Turing (7.5), Pascal (6.x)
2.4         | 3.5–3.8    | 11.0   | 8.0     | Turing (7.5), Pascal (6.x), Maxwell (5.x)
2.3         | 3.5–3.8    | 10.1   | 7.6     | Pascal (6.x), Maxwell (5.x)
2.2         | 3.5–3.8    | 10.1   | 7.6     | Pascal (6.x), Maxwell (5.x)
2.1         | 3.5–3.8    | 10.1   | 7.6     | Pascal (6.x), Maxwell (5.x)
2.0         | 3.5–3.8    | 10.0   | 7.4     | Pascal (6.x), Maxwell (5.x)
1.15        | 3.5–3.8    | 10.0   | 7.4     | Pascal (6.x), Maxwell (5.x)
1.14        | 3.5–3.8    | 10.0   | 7.4     | Pascal (6.x), Maxwell (5.x)
1.13        | 3.5–3.7    | 10.0   | 7.4     | Pascal (6.x), Maxwell (5.x)
1.12        | 3.5–3.7    |  9.0   | 7.3     | Volta (7.0), Pascal (6.x), Maxwell (5.x)
1.11        | 3.5–3.7    |  9.0   | 7.3     | Volta (7.0), Pascal (6.x), Maxwell (5.x)
1.10        | 3.5–3.7    |  9.0   | 7.1     | Volta (7.0), Pascal (6.x), Maxwell (5.x)
1.9         | 3.5–3.7    |  9.0   | 7.1     | Volta (7.0), Pascal (6.x), Maxwell (5.x)
1.8         | 3.5–3.7    |  9.0   | 7.0     | Volta (7.0), Pascal (6.x), Maxwell (5.x)
1.7         | 3.5–3.7    |  9.0   | 7.0     | Volta (7.0), Pascal (6.x), Maxwell (5.x)
1.6         | 3.5–3.7    |  8.0   | 6.0     | Pascal (6.x), Maxwell (5.x)
1.5         | 3.5–3.7    |  8.0   | 6.0     | Pascal (6.x), Maxwell (5.x)
1.4         | 3.5–3.7    |  8.0   | 6.0     | Pascal (6.x), Maxwell (5.x)
1.3         | 3.5–3.6    |  8.0   | 6.0     | Pascal (6.x), Maxwell (5.x)
1.2         | 3.5–3.6    |  8.0   | 5.1     | Maxwell (5.x), Kepler (3.x)
1.1         | 3.5–3.6    |  8.0   | 5.1     | Maxwell (5.x), Kepler (3.x)
1.0         | 3.5        |  8.0   | 5.1     | Maxwell (5.x), Kepler (3.x)

Примечания:
- Для версий 2.21+ ожидается поддержка Python 3.13.
- Начиная с TF 2.15, пакет tensorflow-gpu объединён с tensorflow.
- Для Windows Native GPU поддержка ограничена TF <= 2.10.
- Версии 2.6–2.10 могут работать с CUDA 11.2/cuDNN 8.1.
- Архитектуры GPU: Maxwell (5.x), Pascal (6.x), Volta (7.0), Turing (7.5), Ampere (8.x), Ada Lovelace (8.9), Hopper (9.x), Blackwell (12.x).

Таблица соответствия видеокарт NVIDIA архитектурам GPU и Compute Capability
Источники:
- https://developer.nvidia.com/cuda-gpus
- https://github.com/ollama/ollama/blob/main/docs/gpu.md
- https://gist.github.com/standaloneSA/99788f30466516dbcc00338b36ad5acf
- https://arnon.dk/matching-sm-architectures-arch-and-gencode-for-various-nvidia-cards/

Compute Capability | Архитектура  | Год  | Примеры видеокарт
12.1               | Blackwell    | 2025 | NVIDIA GB10 (DGX Spark)
12.0               | Blackwell    | 2025 | GeForce RTX 5090, RTX 5080, RTX 5070 Ti, RTX 5070, RTX 5060 Ti, RTX 5060, RTX 5050
11.0               | Blackwell    | 2025 | Jetson T5000, Jetson T4000
10.3               | Blackwell    | 2025 | NVIDIA GB300, NVIDIA B300
10.0               | Blackwell    | 2024 | NVIDIA GB200, NVIDIA B200
 9.0               | Hopper       | 2022 | NVIDIA H100, H200, GH200
 8.9               | Ada Lovelace | 2022 | GeForce RTX 4090, RTX 4080, RTX 4070 Ti, RTX 4070, RTX 4060 Ti, RTX 4060, RTX 4050
 8.7               | Ampere       | 2020 | Jetson AGX Orin, Jetson Orin NX, Jetson Orin Nano
 8.6               | Ampere       | 2020 | GeForce RTX 3090 Ti, RTX 3090, RTX 3080 Ti, RTX 3080, RTX 3070 Ti, RTX 3070, RTX 3060 Ti, RTX 3060, RTX 3050 Ti, RTX 3050
 8.0               | Ampere       | 2020 | NVIDIA A100, A30
 7.5               | Turing       | 2018 | GeForce GTX 1650 Ti, TITAN RTX, RTX 2080 Ti, RTX 2080, RTX 2070, RTX 2060
 7.0               | Volta        | 2017 | NVIDIA TITAN V, Tesla V100
 6.1               | Pascal       | 2016 | GeForce GTX 1080 Ti, GTX 1080, GTX 1070 Ti, GTX 1070, GTX 1060, GTX 1050 Ti, GTX 1050
 6.0               | Pascal       | 2016 | Tesla P100, Quadro GP100
 5.2               | Maxwell      | 2014 | GeForce GTX 980 Ti, GTX 980, GTX 970, GTX 960, GTX 950
 5.0               | Maxwell      | 2014 | GeForce GTX 750 Ti, GTX 750

Примечания:
- Compute Capability определяет поддерживаемые инструкции CUDA.
- Для TensorFlow 2.20+ требуется Compute Capability >= 3.5 (практически все карты).
- Для FP8-операций требуется Compute Capability >= 8.9 (RTX 40xx и новее).
- Архитектура Blackwell представлена в вариантах 10.0, 10.3, 11.0, 12.0, 12.1.
- RTX 3050-3090                           относится к Ampere    (Compute Capability 8.6).
- RTX 5050-5090 (ноутбучная и настольная) относится к Blackwell (Compute Capability 12.0).
"""
