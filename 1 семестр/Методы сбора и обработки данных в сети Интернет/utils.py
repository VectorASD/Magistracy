import os
import pickle
from datetime import datetime, timezone, timedelta
import re



NBSP  = '\xa0'   # chr(160)
NNBSP = '\u202f' # chr(8239)
LRM   = '\u200e' # chr(8206)
space_cleaner = re.compile(f"[{NBSP}{NNBSP}{LRM}]").sub



class EastAsianWidth:
    def __init__(self):
        self.txt_path = os.path.join("assets", "EastAsianWidth.txt")
        self.asd_path = os.path.join("assets", "EastAsianWidth.asd")

        try: self.load_cache() # примерно в 20 раз быстрее, но после первого запуска
        except FileNotFoundError: self.load()
        self.apply_ranges()

    def load(self):
        # https://www.unicode.org/Public/UCD/latest/ucd/EastAsianWidth.txt
        """
        N = Neutral (обычно ширина 1)
        Na = Narrow (ширина 1, как латиница, цифры, пробел)
        W = Wide (ширина 2, как CJK иероглифы)
        F = Fullwidth (ширина 2, специальные формы)
        A = Ambiguous (может быть 1 или 2 в зависимости от окружения)
            Забавно, что символ '◯' как раз таки попадает под этот Ambiguous!
            А, поскольку и в Notepad++ и в github это рендерится, как широкий символ, то здесь и так всё понятно ;'-}
            Но вот только русские символы тоже туда попадают... Будет исправлять уже сам файл, вручную
        H = Halfwidth (ширина 1, специальные формы)
        """
        self.ranges = ranges = []
        with open(self.txt_path, "r") as file:
            for line in file:
                line = line.split("#", 1)[0]
                arr = line.split(";", 1)
                if len(arr) < 2: continue

                a, b = arr
                arr = a.split("..", 1)
                if b.strip() not in ("W", "F"): continue # Wide & Fullwidth, please ;'-}

                ranges.append((int(arr[0], 16),) if len(arr) == 1 else range(int(arr[0], 16), int(arr[1], 16)+1))
        with open(self.asd_path, "wb") as file:
            pickle.dump(ranges, file, protocol=4)

    def load_cache(self):
        with open(self.asd_path, "rb") as file:
            self.ranges = pickle.load(file)

    def apply_ranges(self):
        wide_chars = set()
        for range in self.ranges:
            wide_chars.update(range)
        print("|wide_chars|:", len(wide_chars)) # 182876 символов...\
        self.wide_chars = wide_chars

    def char_width(self, ch: str) -> int:
        """Возвращает ширину символа (1 или 2)"""
        return 2 if ord(ch) in self.wide_chars else 1

    def str_width(self, s: str) -> int:
        """Считает реальную ширину строки"""
        wide_chars = self.wide_chars
        return sum(2 if ord(ch) in wide_chars else 1 for ch in s)

wide_chars = EastAsianWidth()
str_width  = wide_chars.str_width

def test_it():
    print(str_width("◯◯◯"))          # 6
    print(str_width("Русские букавки")) # 15
    print(str_width("Мяу! ◯"))         # 7
    exit()
# test_it()

def ljust(s, target_width: int, fill: str = " ") -> str:
    """Правый паддинг до target_width визуальных колонок."""
    s = str(s)
    w = str_width(s)
    pad = max(0, target_width - w)
    return s + (fill * pad)

def rjust(s, target_width: int, fill: str = " ") -> str:
    """Левый паддинг до target_width визуальных колонок."""
    s = str(s)
    w = str_width(s)
    pad = max(0, target_width - w)
    return (fill * pad) + s



def print_table(table: tuple[tuple, ...], stream, middle_sep = True):
    """
    Печатает таблицу с одинаковой шириной колонок и рамками +---+.
    table: кортеж из кортежей, где первый кортеж — заголовки.
    """
    # вычисляем ширину каждой колонки
    col_widths = tuple(max(str_width(str(row[i])) for row in table) for i in range(len(table[0])))

    line_separator = "".join(("+", *("-" * (w + 2) + "+" for w in col_widths), "\n"))

    # определяем, числовая ли колонка
    def skip_header():
        it = iter(table)
        next(it)
        return it
    types = (int, float, complex, type(None))
    numeric_cols = tuple(
        all(isinstance(v, types) for v in (row[i] for row in skip_header()))
        for i in range(len(table[0]))
    )

    # печать таблицы
    stream.write(line_separator)
    it = iter(table)
    header = "".join(("|", *(" " + ljust(cell, width) + " |" for cell, width in zip(next(it), col_widths)), "\n"))
    stream.write(header)
    stream.write(line_separator)
    for row in it:
        line = "".join(("|", *(" " + (rjust(cell, width) if is_num else ljust(cell, width)) + " |" for cell, width, is_num in zip(row, col_widths, numeric_cols)), "\n"))
        stream.write(line)
        if middle_sep: stream.write(line_separator)
    if not middle_sep: stream.write(line_separator)



def href_to_url_wrap(base_url):
    def href_to_url(href):
        if type(href) is list:
            if not href: return None
            href = href[0]
        if href.startswith("/"): href = base_url + href
        return href
    return href_to_url



nsk_tz = timezone(timedelta(hours=7))

months = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}

def iso_to_human(date_iso):
    dt = datetime.fromisoformat(date_iso)
    dt_nsk = dt.astimezone(nsk_tz)
    formatted = f"{dt_nsk:%H:%M}, {dt_nsk.day} {months[dt_nsk.month]} {dt_nsk.year}"
    return formatted
