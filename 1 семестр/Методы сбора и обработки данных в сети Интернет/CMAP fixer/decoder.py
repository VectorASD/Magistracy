import pymupdf # pip install PyMuPDF
from pprint import pprint



"""
    block["type"]:
0	Text		Текстовый блок: содержит lines, spans, chars
1	Image		Изображение: содержит bbox, image (имя ресурса)
2	Vector		Векторная графика: линии, прямоугольники, кривые
3	Shading		Градиенты и заливки (редко встречается)
4	Form XObject	Встроенные формы (например, шаблоны, повторяющиеся элементы)
5	Unknown		Неопределённый или нестандартный блок (возможно, пустой или повреждённый)
"""



def collect_font_names(doc):
    fonts = set()
    for page in doc:
        page = page.get_text("dict")
        blocks = page["blocks"]
        for block in blocks:
            if block["type"] == 0:
                for line in block.get("lines", ()):
                    for span in line.get("spans", ()):
                        fonts.add(span["font"])
    print("Шрифты, использованные в PDF:")
    for font in sorted(fonts): print("-", font)
"""
Шрифты, использованные в PDF:
- AvantGardeBkBT
- Journal
- Journal-Bold
- Journal-NormalItalic
- MTExtra
- Symbol
- SymbolET
- SymbolPropBT
- Symbol_ET
- TimesET
- TimesET-NormalItalic
- TimesNewRoman
"""



mupdf = pymupdf.mupdf

def xref_viewer(pdf):
    # fonts = set(font for page in doc for font in page.get_fonts())
    # pprint(fonts)
    # print("|xref|:", doc.xref_length())
    # pdf = pymupdf._as_pdf_document(doc)

    # C:\Users\VectorASD\AppData\Local\Programs\Python\Python313\Lib\site-packages\pymupdf\__init__.py (ОХ НИФИГА СЕ ТУТ ВСЕГО!!!)
    # 7896: xref_get_key
    # 7946: xref_get_keys
    # ....: xref_is_*
    # 7996: xref_length
    # 8004: xref_object
    # 8023: xref_set_key
    # 8061: xref_stream
    # 8079: xref_stream_raw
    # 8097: xref_xml_metadata

    class Xref:
        def __init__(self, ref):
            self.ref = ref
            self.num = mupdf.pdf_to_num(ref)
        def __repr__(self):
            return f"xref:{self.num}"
        def to_bin(self):
            stream = self.ref
            assert stream.m_internal
            assert mupdf.pdf_is_stream(stream)

            fz_buffer = mupdf.pdf_load_stream(stream)
            assert isinstance(fz_buffer, mupdf.FzBuffer)

            return mupdf.fz_buffer_extract_copy(fz_buffer)

    class Font:
        fonts = {}
        def __init__(self, ref, name, ext, bin):
            self.ref = ref
            self.name = name
            self.ext = ext
            self.bin = bin
            Font.fonts[name] = self
            # self.to_woff2()
        def __repr__(self):
            return f"font:{self.name}.{self.ext} ({len(self.bin)} b.)"
        def to_woff2(self):
            print(self)
            import os, io
            os.makedirs("fonts", exist_ok=True)
            from fontTools.ttLib import TTFont # pip install fonttools

            try:
                font = TTFont(io.BytesIO(self.bin))
                font.flavor = "woff2"
                font.save(f"fonts/{self.name}.woff2")
                return path
            except Exception as e:
                print(f"⚠️ Не удалось конвертировать {self.name} ({self.ext}) → WOFF2: {e}")
                return None

    def to_pyobj(obj):
        if not obj.m_internal or mupdf.pdf_is_null(obj): return

        if mupdf.pdf_is_indirect(obj): return Xref(obj) 
        if mupdf.pdf_is_int(obj):      return mupdf.pdf_to_int(obj)
        if mupdf.pdf_is_bool(obj):     return mupdf.pdf_to_bool(obj)
        if mupdf.pdf_is_name(obj):     return mupdf.pdf_to_name(obj)
        if mupdf.pdf_is_string(obj):   return mupdf.pdf_to_text_string(obj)
        if mupdf.pdf_is_real(obj):     return mupdf.pdf_to_real(obj) # unchecked

        if mupdf.pdf_is_array(obj):
            count = mupdf.pdf_array_len(obj)
            return tuple(to_pyobj(mupdf.pdf_array_get(obj, i)) for i in range(count))
        if mupdf.pdf_is_dict(obj):     return get_dict(obj)

        return "__unknown"

    def get_dict(obj):
        n = mupdf.pdf_dict_len(obj)
        keys = tuple(mupdf.pdf_to_name(mupdf.pdf_dict_get_key(obj, i)) for i in range(n))
        return {key: to_pyobj(mupdf.pdf_dict_getp(obj, key)) for key in keys}

    def get_font(items):
        stream = None
        obj = items.get("FontFile",  None)
        if obj: ext, stream = "pfa", obj # and obj.obj.m_internal: print(obj, mupdf.pdf_is_stream(obj.obj))
        obj = items.get("FontFile2", None)
        if obj: ext, stream = "ttf", obj
        obj = items.get("FontFile3", None)
        if obj:
            ext = {"Type1C": "cff", "CIDFontType0C": "cid", "OpenType": "otf"}[index[obj.num]["Subtype"]]
            stream = obj

        assert stream
        bin = stream.to_bin()

        items["_font"] = Font(stream, items["FontName"].split('+', 1)[-1], ext, bin)

    def get_obj(xref):
        obj = mupdf.pdf_load_object(pdf, xref) if xref else mupdf.pdf_trailer(pdf)
        items = get_dict(obj)
        items["_xref"] = xref
        return items

    count = mupdf.pdf_xref_len(pdf) if pdf.m_internal else 0 # doc.xref_length()
    # print("|xref|:", count)
    index = tuple(get_obj(xref) for xref in range(count))

    for items in index:
        if items.get("Type", None) == "FontDescriptor": get_font(items)

    if 0:
        for items in index:
            #if "_font" in items:
            print(items["_xref"], end=" ")
            pprint(items)
        input("exit..."); exit()

    return Font.fonts, index



def collect_bbox(doc, selected_page_n):
    html = [
        "<html><head><meta charset='utf-8'><style>",
        "body { position: relative; margin: 0; padding: 0; }",
        ".bbox { position: absolute; font-size: 5px; box-sizing: border-box; <!--overflow: hidden;--> }",
        "</style></head><body>"
    ]
    colors = {
        "block": ("rgba(0, 128, 255, 0.2)", "rgba(0, 128, 255, 0.6)"),
        "line": ("rgba(0, 200, 0, 0.2)", "rgba(0, 200, 0, 0.6)"),
        "span": ("rgba(255, 128, 0, 1)", "rgba(255, 64, 0, 1)"),
        "image": ("rgba(128, 0, 255, 0.2)", "rgba(128, 0, 255, 0.6)")
    }
    def draw_bbox(x0, y0, x1, y1, label, fill, border):
        width  = x1 - x0
        height = y1 - y0
        return (
            f"<div class='bbox' style='left:{x0}px; top:{y0}px; width:{width}px; height:{height}px; "
            f"background:{fill}; border:1px solid {border};'>"
            f"{label}</div>"
        )
    def apply_transform(bbox, transform):
        a, b, c, d, e, f = transform
        x0, y0, x1, y1 = bbox

        x0p = a * x0 + c * y0 + e
        y0p = b * x0 + d * y0 + f
        x1p = a * x1 + c * y1 + e
        y1p = b * x1 + d * y1 + f

        return min(x0p, x1p), min(y0p, y1p), max(x0p, x1p), max(y0p, y1p)

    for page_n, page in enumerate(doc, 1):
        if page_n != selected_page_n: continue

        page = page.get_text("dict")
        blocks = page["blocks"]
        W, H = page["width"], page["height"]
        print(f"{page_n}.)") # {W} x {H}")
        html.append(f"<div style='position:absolute; left:0px; top:0px; width:{W}px; height:{H}px; background:#f9f9f9; border:2px solid #ccc;'>PDF page</div>")

        for block in blocks:
            html.append(draw_bbox(*block["bbox"], "block", *colors["block"]))
            match block["type"]:
                case 0:
                    # print("  text")
                    for line in block.get("lines", ()):
                        html.append(draw_bbox(*line["bbox"], "line", *colors["line"]))
                        for span in line.get("spans", ()):
                            html.append(draw_bbox(*span["bbox"], span["font"], *colors["span"]))
                case 1:
                    # print("  image")
                    bbox = apply_transform(block["bbox"], block["transform"])
                    html.append(draw_bbox(*bbox, "image", *colors["image"]))
                case _:
                    print(" ", block["number"], block["type"], block["bbox"])
                    print(" ", block.keys())

    html.append("</body></html>")
    with open("bbox_full_visualization.html", "w", encoding="utf-8") as f:
        f.write("\n".join(html))



def full_draw(page):
    def rgb_from_int(color_int):
        r = (color_int >> 16) & 255
        g = (color_int >> 8) & 255
        b = color_int & 255
        return f"#{r:02x}{g:02x}{b:02x}"

    page = page.get_text("dict")
    # pprint(page.keys()) # dict_keys(['width', 'height', 'blocks'])
    width  = page["width"]
    height = page["height"]
    blocks = page["blocks"]
    pprint(blocks)

    html = ["<html><body style='position:relative; font-family:Journal;'>"]
    for block in blocks:
        if block["type"] == 0:
            for line in block["lines"]:
                for span in line["spans"]:
                    raw = span["text"]
                    print(raw)
                    text = raw.encode("latin1", errors="replace").decode("windows-1251", errors="replace")
                    x, y = span["bbox"][0], span["bbox"][1]
                    size = span["size"]
                    font = span["font"]
                    color = rgb_from_int(span["color"])

                    html.append(
                        f"<div style='position:absolute; left:{x}px; top:{y}px; "
                        f"font-size:{size}px; font-family:{font}; color:{color};'>"
                        f"{text}</div>"
                    )
    html.append("</body></html>")

    with open("output.html", "w", encoding="utf-8") as f:
        f.write("\n".join(html))



def content_replacer(pdf, index):
    import re

    number = r"\s*-?\d*\.?\d*"
    text_capturer = r"\((.*?)\)"
    loop = rf"\s*{text_capturer}(?:{number}\s*{text_capturer})+"
    arr_pattern = rf"\[{loop}\s*\]TJ"
    single_pattern = text_capturer + r"\s*Tj"
    pattern = f"({arr_pattern})|({single_pattern})"
    compiled = re.compile(pattern.encode(), re.DOTALL)

    def recoder(match):
        return b"(TEXT)"
        text = match.group(1).decode("windows-1251", errors="replace")
        # utf16be = text.encode("utf-16-be")
        # with_bom = b"\xfe\xff" + utf16be # Добавляем BOM
        return b"(" + text.encode("windows-1251") + b")"

    def matcher(bin): # захватывает только первую и последнюю группу ://////////// ПОДСТАВА ВЕКА!!!
        rematched = []
        app = rematched.append

        last_end = 0
        for match in compiled.finditer(bin):
            for i, group in enumerate(match.groups(), 1):
                # assert group == bin[match.start(i) : match.end(i)] проверено целиком на всём search.pdf
                app(bin[last_end : match.start(i)]) # UNMATCH
                app(recoder(group)) # MATCH
                last_end = match.end(i)
        app(bin[last_end:]) # UNMATCH

        return b"".join(rematched)

    inner = re.compile(rb"\((.*?)\)", re.DOTALL)
    def matcher(bin):
        rematched = []
        app = rematched.append

        last_end = 0
        for match in compiled.finditer(bin):
            start, end = match.span()
            app(bin[last_end:start]) # UNMATCH
            app(inner.sub(recoder, match.group(0)))
            last_end = end # MATCH
        app(bin[last_end:]) # UNMATCH

        return b"".join(rematched)

    for items in index:
        if items.get("Type", None) == "Page":
            print(items["_xref"])
            ref = items["Contents"]

            bin = ref.to_bin() #; pprint(bin.split(b"\n"))
            matched = matcher(bin)
            # pprint(matched.split(b"\n"))

            obj = mupdf.pdf_new_indirect(pdf, ref.num, 0)
            assert mupdf.pdf_is_dict(obj)
            res = pymupdf.JM_BufferFromBytes(matched)
            assert res.m_internal
            pymupdf.JM_update_stream(pdf, obj, res, compress=1)

            # print(ref.to_bin())
    pdf.dirty = 1



def generate_to_unicode_cmap(first, last, widths):
    assert last - first + 1 == len(widths)

    from datetime import datetime, timezone, timedelta
    nsk_time = datetime.now(timezone(timedelta(hours=7)))
    timestamp = nsk_time.strftime("%Y-%m-%d %H:%M:%S")

    cmap = []
    cmap.append("/CIDInit /ProcSet findresource begin")
    cmap.append("% CMAP generator powered by VectorASD")
    cmap.append("% vk.ru/vectorasd")
    cmap.append("% t.me/vector_asd")
    cmap.append(f"% Generated on {timestamp} (UTC+7)")
    cmap.append("12 dict begin")
    cmap.append("begincmap")
    cmap.append("/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def")
    cmap.append("/CMapName /Win1251 def")
    cmap.append("/CMapType 2 def")
    cmap.append("1 begincodespacerange")
    cmap.append(f"<{first:02X}> <{last:02X}>")
    cmap.append("endcodespacerange")

    bfchar = []
    for code, width in enumerate(widths, start=first):
        if width == 0: continue # пропускаем неиспользуемые символы
        try:
            char = bytes([code]).decode("windows-1251")
            uni = f"{ord(char):04X}"
        except:
            uni = "FFFD"
        bfchar.append(f"<{code:02X}> <{uni}>")

    cmap.append(f"{len(bfchar)} beginbfchar")
    cmap.extend(bfchar)
    cmap.append("endbfchar")

    cmap.append("endcmap")
    cmap.append(f"% Generated by VectorASD — vk.ru/vectorasd — t.me/vector_asd — {timestamp}")
    cmap.append("CMapName currentdict /CMap defineresource pop")
    cmap.append("end")
    cmap.append("end")

    return "\n".join(cmap).encode("utf-8")



def fix_cmap(index):
    for items in index:
        if items.get("Type", None) == "Font" and "Widths" in items:
            print(items["_xref"])
            print(items)
            cmap = generate_to_unicode_cmap(items["FirstChar"], items["LastChar"], items["Widths"])
            # print(cmap.decode("utf-8")); exit()

            xref_cmap = mupdf.pdf_create_object(pdf)

            mupdf.pdf_update_object(pdf, xref_cmap, mupdf.pdf_new_dict(pdf, 12))

            obj = mupdf.pdf_new_indirect(pdf, xref_cmap, 0)
            assert mupdf.pdf_is_dict(obj)

            buffer = pymupdf.JM_BufferFromBytes(cmap)
            pymupdf.JM_update_stream(pdf, obj, buffer, compress=1)

            xref = items["_xref"]
            doc.xref_set_key(xref, "ToUnicode", f"{xref_cmap} 0 R")
            print(f"✅ ToUnicode добавлен в шрифт xref:{xref} → cmap xref:{xref_cmap}")



def check_cmap():
    doc = pymupdf.open("search_modified_by_VectorASD.pdf")
    pdf = pymupdf._as_pdf_document(doc)
    fonts, index = xref_viewer(pdf)
    for items in index:
        if items.get("Type", None) == "Font" and "Widths" in items:
            print(items["_xref"], items["ToUnicode"])
            print(items["ToUnicode"])
            pprint(items["ToUnicode"].to_bin().decode("utf-8"))
    exit()

try: check_cmap()
except pymupdf.FileNotFoundError: pass



doc = pymupdf.open("search.pdf")
pdf = pymupdf._as_pdf_document(doc)
print(doc, len(doc))

# collect_font_names(doc)
fonts, index = xref_viewer(pdf)
# collect_bbox(doc, 116) # счёт страниц с единицы в отличие от doc[115]...
# collect_bbox(doc, 180); exit()
# full_draw(doc[115])
# content_replacer(pdf, index) текст всех span заменяется на TEXT. Удобно тестировать CMAP-индексацию для поиска и копирования!
fix_cmap(index)

doc.save("search_modified_by_VectorASD.pdf")

input("Press enter to exit...")
