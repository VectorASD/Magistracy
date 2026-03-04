import zipfile
import os
from random import sample

import numpy as np    # pip install numpy
import pydicom        # pip install pydicom
from PIL import Image # pip install pillow

from bitmap_driver import read_bmp, write_bmp



def print_dicom_meta(ds):
    print("=== Основная информация ===")
    print("Формат:", ds.file_meta.get('MediaStorageSOPClassUID', 'нет данных'))
    print("Трансфер синтаксис (сжатие):", ds.file_meta.TransferSyntaxUID)

    print("\n=== Размеры ===")
    print("Rows:", ds.get('Rows'))
    print("Columns:", ds.get('Columns'))

    print("\n=== Пиксельные данные ===")
    print("BitsAllocated:", ds.get('BitsAllocated'))
    print("BitsStored:", ds.get('BitsStored'))
    print("HighBit:", ds.get('HighBit'))
    print("SamplesPerPixel:", ds.get('SamplesPerPixel'))
    print("PhotometricInterpretation:", ds.get('PhotometricInterpretation'))

    print("\n=== Пациент ===")
    print("PatientID:", ds.get('PatientID'))
    print("StudyInstanceUID:", ds.get('StudyInstanceUID'))
    print("SeriesInstanceUID:", ds.get('SeriesInstanceUID'))

    print("\n=== Дополнительно ===")
    print("PixelRepresentation:", ds.get('PixelRepresentation'))
    print("PlanarConfiguration:", ds.get('PlanarConfiguration', 'N/A'))

    ts = ds.file_meta.TransferSyntaxUID
    if ts.is_compressed:
        print("\nPixelData сжато:", ts)
    else:
        print("\nPixelData НЕ сжато:", ts)

"""
def load_dicom(filename, debug=False):
    ds = pydicom.dcmread(filename)

    if debug:
        print_dicom_meta(ds)

    return ds.pixel_array
"""

def load_dicom_from_bytes(data, debug=False):
    ds = pydicom.dcmread(pydicom.filebase.DicomBytesIO(data))

    if debug:
        print_dicom_meta(ds)

    return ds.pixel_array

def to_uint8(arr):
    arr = arr.astype(np.float32)
    min, max = arr.min(), arr.max()
    # if min == max:
    #     return np.zeros_like(arr, dtype=np.uint8)
    assert min != max, "Одноцветная картинка?!"
    arr = (arr - min) / (max - min)
    pix = (arr * 255).astype(np.uint8)
    return pix

def resize_to_512(pix):
    pil = Image.fromarray(pix, mode="L")
    pil = pil.resize((512, 512), Image.BILINEAR)
    return np.array(pil)

# BZIP2 - BWT (Burrows–Wheeler Transform) любит:
# - повторяющиеся структуры
# - короткие паттерны
# - локальные корреляции
# RLE8‑BMP — идеальный кандидат. По этому ZIP_LZMA даёт 10.3 Мб, а ZIP_BZIP2 - всего 9.57 Мб

def convert_dicom_zip_to_bmp_zip(in_zip, out_zip, debug=False):
    # Открываем оба архива одновременно
    with zipfile.ZipFile(in_zip, 'r') as zin, \
         zipfile.ZipFile(out_zip, 'w', compression=zipfile.ZIP_BZIP2) as zout:

        for name in zin.namelist():
            if not name.endswith('.dcm'):
                continue

            data = zin.read(name)

            arr = load_dicom_from_bytes(data, debug=debug)
            if arr is None:
                print(f"[Пропуск] {name} — не DICOM")
                continue

            pix = to_uint8(arr)
            if arr.shape != (512, 512):
                pix = resize_to_512(pix)
                print("    RESIZE", arr.shape, "to", (512, 512))
                # ахах! а таких нет :)
            # 9,57 МБ (10 035 307 байт) До ввода условия 'arr.shape != (512, 512)'
            # 9,57 МБ (10 035 307 байт) Если убрать Image.BILINEAR, ничего не поменяется

            # --- Запись в выходной ZIP ---
            out_name = os.path.splitext(os.path.basename(name))[0] + ".bmp"
            with zout.open(out_name, "w") as file:
                write_bmp(file, pix, mode="gray", use_rle=True)

            print(f"[OK] {name} → {out_name}")

    print(f"\nГотово! Все BMP упакованы в {out_zip} (BZIP2)")



def bossbase_repacker(in_zip, out_zip):
    with zipfile.ZipFile(in_zip, 'r') as zin, \
         zipfile.ZipFile(out_zip, 'w', compression=zipfile.ZIP_BZIP2) as zout:

        names = zin.namelist()
        assert len(names) == 1000

        names = sample(names, 100)
        for name in names:
            assert name.endswith(".bmp")
            print(name)

            with zin.open(name, "r") as file:
                pix = read_bmp(file, debug=False, to_gray=True)

            with zout.open(name, "w") as file:
                # palette из read_bmp можно пропустить, т.к. мой режим 'gray' генерирует тоже самое
                # use_rle (мой rle8) + BZIP2 компрессия хуже, чем сразу BZIP2 на индексной карте...
                write_bmp(file, pix, mode="gray", use_rle=False)



def convert_jpeg_zip_to_bmp_zip(in_zip, out_zip):
    with zipfile.ZipFile(in_zip, 'r') as zin, \
         zipfile.ZipFile(out_zip, 'w', compression=zipfile.ZIP_BZIP2) as zout:

        names = zin.namelist()
        assert len(names) == 5734

        names = sample(names, 100)
        for name in names:
            assert name.startswith("Images/") and name.endswith(".jpg")
            out_name = name[len("Images/"):]
            print(out_name)

            with zin.open(name, "r") as file:
                img = Image.open(file)
                img = img.convert("L") # grayscale
                pix = np.array(img, dtype=np.uint8)
                assert pix.shape == (512, 512) # автор датасета уже сделал это...

            with zout.open(out_name, "w") as file:
                # palette из read_bmp можно пропустить, т.к. мой режим 'gray' генерирует тоже самое
                # use_rle (мой rle8) + BZIP2 компрессия хуже, чем сразу BZIP2 на индексной карте...
                write_bmp(file, pix, mode="gray", use_rle=False)



if __name__ == "__main__":
    #    источник BOSSbase-сцен:
    # https://drive.google.com/drive/folders/1LcvhZe-lhYFMVLq9hexo8HJJa3Y-uUMM
    # bossbase_repacker("pictures.zip", "bossbase_containers.zip")

    #    источник dicom'ок:
    # https://www.kaggle.com/datasets/kmader/siim-medical-images
    # convert_dicom_zip_to_bmp_zip("archive.zip", "medical_containers.zip", debug=False)

    #    источник рисованных портретов:
    # https://www.kaggle.com/datasets/deewakarchakraborty/portrait-paintings
    convert_jpeg_zip_to_bmp_zip("portraits.zip", "portrait_containers.zip")
