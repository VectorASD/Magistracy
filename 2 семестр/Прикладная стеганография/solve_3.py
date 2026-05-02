import numpy as np  # pip install numpy

from bitmap_driver import read_bmp

import zipfile
import os



class HistogramShifting:
    def __init__(self):
        self.pix = None

    def load_gray_from_io(self, file):
        self.pix = read_bmp(file, to_gray=True)
        return self

    def load_gray_from_file(self, name):
        with open(name, "rb") as file:
            self.load_gray_from_io(file)
        return self

    def load_gray_from_zip(self, zip_name, name):
        with zipfile.ZipFile(zip_name, "r") as zip:
            with zip.open(name, "r") as file:
                self.load_gray_from_io(file)
        return self

    def insert(self):
        #   Step.1
        # hist, bin_edges = np.histogram(self.pix, bins=256, range=(0, 255)) # Тормозной варианта из-за вычислений bin_edges, что нам не нужен,
                                                                             # потому что RDH‑методы работают строго с целыми значениями яркости.
        hist = np.bincount(self.pix.flatten(), minlength=256)                # Прямой способ получить hist (сколько какой пиксель встречается раз).
        assert hist.shape == (256,)
        print(hist)



if __name__ == "__main__":
    HS = HistogramShifting().load_gray_from_zip(os.path.join("assets", "bossbase_containers.zip"), "205.bmp")
    HS.insert()
