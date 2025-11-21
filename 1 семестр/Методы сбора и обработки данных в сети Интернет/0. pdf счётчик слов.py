import os, sys

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "CMAP fixer")
)
sys.path.append(BASE_DIR)



from decoder import xref_viewer, pymupdf
from pprint import pprint
from collections import Counter



def content_reader(index): # не работает, т.к. в Алисе используются <([0-9A-F]+)> Tj (и [<...> ...] TJ)
    import re

    number = r"\s*-?\d*\.?\d*"
    text_capturer = r"\((.*?)\)"
    loop = rf"\s*{text_capturer}(?:{number}\s*{text_capturer})+"
    arr_pattern = rf"\[{loop}\s*\]TJ"
    single_pattern = text_capturer + r"\s*Tj"
    pattern = f"({arr_pattern})|({single_pattern})"
    compiled = re.compile(pattern.encode(), re.DOTALL)

    def recoder(match):
        text = match.group(1).decode("windows-1251", errors="replace")
        print(text)

    inner = re.compile(rb"\((.*?)\)", re.DOTALL)
    def matcher(bin):
        for match in compiled.finditer(bin):
            print("match:", match)
            inner.sub(recoder, match.group(0))

    pages = (items for items in index if items.get("Type", None) == "Page")
    for page_n, items in enumerate(pages, start=1):
        print(f"xref (page №{page_n:3}):", items["_xref"])
        ref = items["Contents"]

        bin = ref.to_bin() #; pprint(bin.split(b"\n"))
        print(bin)
        matcher(bin)

# Таблица символов, конкретно под "Алиса в Стране чудес.pdf":
def cmap():
    table = {}
    table[  3] = ' '
  # table[  4] = '!'
  # table[ 11] = '('
  # table[ 12] = ')'
  # table[ 13] = '*'
  # table[ 15] = ','
  # table[ 16] = '-'
  # table[ 17] = '.'
    for i in range( 19,   29): table[i] = chr(i + 29) # '0'..'9'
  # table[ 29] = ':'
  # table[ 30] = ';'
  # table[ 34] = '?'
    for i in range( 36,   62): table[i] = chr(i + 29) # 'A'..'Z'
    for i in range( 68,   94): table[i] = chr(i + 29) # 'a'..'z'
  # table[108] = '«'
  # table[123] = '»'
    for i in range(958,  990): table[i] = chr(i + 82) # 'А'..'Я' (без 'Ё')
    for i in range(990, 1022): table[i] = chr(i + 82) # 'а'..'я' (без 'ё')
  # table[2010] = '—'
  # table[2024] = '…'
    return table
# всего 15 небуквенных и нециферных символов на целую книгу!

table = cmap()

def content_reader_Tj(index):
    import re

    hex_re = re.compile(rb"<([0-9A-F]+)> Tj")
    td_re  = re.compile(rb"(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+Td")
    all_re = re.compile(rb"<([0-9A-F]+)> Tj|(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+Td")

    # no_symbols = set()
    dictionary = Counter()

    def line_handler(line):
        dictionary.update(line.lower().split())

    def matcher(bin):
        text = []
        append = text.append
        for token in all_re.finditer(bin):
            Tj, tx, ty = token.groups()
            if Tj: # hex string
                glyph = int(Tj, 16)
                # sym = table.get(glyph, f'<{glyph}>')
                # print("glyph:", sym)
                # if len(sym) > 1: no_symbols.add(glyph)
                try: append(table[glyph])
                except KeyError: continue

            elif tx or ty: # Td shift
                tx = float(tx)
                ty = float(ty)
                if ty:
                    # print("shift:", tx, ty)
                    line_handler("".join(text))
                    text.clear()

        if text:
            line_handler("".join(text))

    pages = (items for items in index if items.get("Type", None) == "Page")
    for page_n, items in enumerate(pages, start=1):
        print(f"xref (page №{page_n:3}):", items["_xref"])
        ref = items["Contents"]

        bin = ref.to_bin() #; pprint(bin.split(b"\n"))
        # print(bin)
        matcher(bin)

    # print(sorted(no_symbols))
    with open("stdout0.txt", "w", encoding="utf-8") as file:
        for string, count in sorted(dictionary.items(), key=lambda x: (-x[1], x[0])): # dictionary.most_common():
            print(f"{string!r:20} {count} шт.", file=file)
    # бало лень приписывать reversed=True внутри sorted, по этому минус к x[1] дописал
    # потом понял, что reversed=True первернул бы и x[0], будто я и там "минус" дописал... повезло ;'-}



doc = pymupdf.open("Алиса в Стране чудес.pdf")
pdf = pymupdf._as_pdf_document(doc)
fonts, index = xref_viewer(pdf)

content_reader_Tj(index)
