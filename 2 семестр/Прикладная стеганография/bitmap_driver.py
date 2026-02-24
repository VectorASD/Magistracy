import struct
import numpy as np
from io import BytesIO
from pprint import pprint

# --- low-level helpers ---

def read_u16(f): return struct.unpack("<H", f.read(2))[0]
def read_u32(f): return struct.unpack("<I", f.read(4))[0]
def read_i32(f): return struct.unpack("<i", f.read(4))[0]

def write_u16(f, v): f.write(struct.pack("<H", v))
def write_u32(f, v): f.write(struct.pack("<I", v))
def write_i32(f, v): f.write(struct.pack("<i", v))



# --- pixel core ---

from bitmap_coders import decode_bmp_pixels, encode_bmp_pixels, BMP_COMPRESSION_to_str



def _make_cga16_palette(): # как в паскальном терминале :) он же PascalGUI под android или TurboPascal
    pal = np.zeros((16, 3), dtype=np.uint8)
    # hex(255 / 3)     -> 0x55   яркость          (0b01010101)
    # hex(255 / 3 * 2) -> 0xAA   активация канала (0b10101010)
    for i in range(16):
        I = 0x55 * ((i & 8) >> 3) # intensity
        R = 0xAA * ((i & 4) >> 2) | I
        G = 0xAA * ((i & 2) >> 1) | I
        B = 0xAA * (i & 1) | I
        if i == 6: G = 0x55 # CGA brown fix (color 6)
        pal[i] = (R, G, B)
    return pal

CGA16 = _make_cga16_palette()

def _build_palette_and_indices(arr, palette=None, palette_size=None, mode=None):
    def quantization(flat, palette):
        # advanced indexing (None и ':' в индексах) - создаёт лишь виртуальные ndarray, как если бы это был memref.subview в MLIR
        # broadcasting - растяжение осей, снова меняются только shape и strides, уже не близкий аналог memref.subview, но тоже не трогает сами данные!
        # вычитание и argmin - единственные операции, что создают новые массивы прямо на ходу, с SIMD-ускорением!
        # иными словами, этот код на python быстрее, чем наивный код на Си, но без SIMD!
        flat    = flat.astype(np.int32)
        palette = palette.astype(np.int32)
        # простое квантование
        deltas = flat[:, None, :] - palette[None, :, :]
        d2 = (deltas ** 2).sum(axis=2)
        return d2.argmin(axis=1).reshape(h, w).astype(np.uint8)
    h, w = arr.shape[:2]

    ok = False

    if mode == "mono":
        pal  = np.array(((0, 0, 0), (255, 255, 255)), dtype=np.uint8)
        gray = (0.299*arr[...,0] + 0.587*arr[...,1] + 0.114*arr[...,2]).astype(np.uint8)
        idx  = (gray > 127).astype(np.uint8)
        return pal, idx

    if mode == "cga16":
        pal  = CGA16
        flat = arr.reshape(-1, 3) # (512, 512, 3) -> (262144, 3)
        idx  = quantization(flat, pal)
        return pal, idx

    if mode == "gray16":
        vals = np.linspace(0, 255, 16, dtype=np.uint8)
        pal  = np.stack((vals, vals, vals), axis=1)
        flat = arr.reshape(-1, 3)
        idx  = quantization(flat, pal)
        return pal, idx

    if mode == "gray":
        pal  = np.arange(256, dtype=np.uint8)[:, None].repeat(3, axis=1)
        gray = (0.299*arr[...,0] + 0.587*arr[...,1] + 0.114*arr[...,2]).astype(np.uint8)
        return pal, gray

    if mode == "random":
        if palette_size is None: palette_size = 256
        ok = True
    elif mode == "random2":
        if palette_size is None: palette_size = 256
        palette = np.random.randint(0, 256, size=(palette_size, 3), dtype=np.uint8)
        ok = True

    if not ok:
        assert not mode, f"unknown palette mode: {mode}"

    # BMP‑палитры никогда не используют альфу для квантования
    if arr.shape[2] == 4:
        arr = arr[:, :, :3]

    if palette is None:
        if palette_size is None:
            raise ValueError("palette or palette_size must be provided for indexed mode")
        pal_size  = max(1, min(palette_size, 256))
        flat      = arr.reshape(-1, arr.shape[2]).astype(np.uint8)
        uniq, inv = np.unique(flat, axis=0, return_inverse=True)
        if uniq.shape[0] <= pal_size:
            pal_rgb = uniq
            idx = inv.reshape(h, w).astype(np.uint8)
        else:
            # берём первые pal_size цветов и мапим по ближайшему
            pal_rgb = uniq[:pal_size]
            idx     = quantization(flat, pal_rgb)
        alpha = np.full((pal_rgb.shape[0], 1), 255, dtype=np.uint8)
        pal = np.concatenate([pal_rgb, alpha], axis=1)
    else:
        if   palette.shape[1] == 4: palette = palette[:, :3]
        elif palette.shape[1] != 3: raise ValueError(f"Palette must have 3 or 4 channels, not {pal.shape[1]}")
        palette_size = palette.shape[0]

        # palette given explicitly
        pal = np.asarray(palette, dtype=np.uint8)
        if pal.shape[1] == 3:
            alpha = np.full((pal.shape[0], 1), 255, dtype=np.uint8)
            pal = np.concatenate([pal, alpha], axis=1)

        flat    = arr.reshape(-1, arr.shape[2])
        palette = pal[:, :arr.shape[2]]
        idx     = quantization(flat, palette)

    if mode == "random":
        pal = np.random.randint(0, 256, size=(palette_size, 3), dtype=np.uint8)

    return pal, idx



# --- headers-handler ---

def read_bmp(f, debug=False):
    # FILE HEADER (14 bytes)
    magic = f.read(2)
    if magic != b"BM":
        raise ValueError("Not a BMP file")
    bfSize     = read_u32(f)
    bfReserved = read_u32(f)
    bfOffBits  = read_u32(f)

    # DIB HEADER (BITMAPCOREHEADER, BITMAPINFOHEADER, BITMAPV<2-5>INFOHEADER)
    dib_size = read_u32(f) # 0-4
    dib = BytesIO(f.read(dib_size - 4)) # 4-end

    assert dib_size in (12, 40, 52, 56, 108, 124), f"unknown dib_size: {dib_size}"

    if dib_size == 12:
        # OS/2 CORE
        width  = read_u16(dib) #  4- 6
        height = read_u16(dib) #  6- 8
        planes = read_u16(dib) #  8-10
        bpp    = read_u16(dib) # 10-12
        comp = 0
        img_size = 0
        colors_used = 0
        rmask = gmask = bmask = amask = None
    else:
        # BITMAPINFOHEADER
        width       = read_i32(dib) #  4- 8
        height      = read_i32(dib) #  8-12
        planes      = read_u16(dib) # 12-14
        bpp         = read_u16(dib) # 14-16
        comp        = read_u32(dib) # 16-20
        img_size    = read_u32(dib) # 20-24
        xppm        = read_i32(dib) # 24-28
        yppm        = read_i32(dib) # 28-32
        colors_used = read_u32(dib) # 32-36
        important   = read_u32(dib) # 36-40

        if debug:
            print("size:", width, height, "  DPI:", xppm, yppm)
        assert width >= 0,  "большинство bmp-read'еров не понимают переворот по оси ширины"
        assert planes == 1, f"неподдерживаемое число планов: {planes}"

        # MASKS
        rmask = gmask = bmask = amask = None
        if dib_size >= 52: # V2
            rmask = read_u32(dib) # 40-44
            gmask = read_u32(dib) # 44-48
            bmask = read_u32(dib) # 48-52
            if dib_size >= 56: # V3
                amask = read_u32(dib) # 52-56
            print("masks:", hex(rmask), hex(gmask), hex(bmask), "x" if amask is None else hex(amask))

    if debug:
        comp_name = BMP_COMPRESSION_to_str.get(comp, f"unknown ({comp})")
        print(f"compression: {comp_name}")

    if dib_size >= 108: # V4
        color_space = read_u32(dib) # 56–60
        ciexyz_r = read_s32(dib), read_s32(dib), read_s32(dib) # 60-72
        ciexyz_g = read_s32(dib), read_s32(dib), read_s32(dib) # 72-84
        ciexyz_b = read_s32(dib), read_s32(dib), read_s32(dib) # 84-96
        ciexyz   = ciexyz_r, ciexyz_g, ciexyz_b
        gamma_r = read_u32(dib) #  96–100
        gamma_g = read_u32(dib) # 100–104
        gamma_b = read_u32(dib) # 104–108
        gamma   = gamma_r, gamma_g, gamma_b
        if debug:
            print("color space:",  color_space)
            print("CIEXYZTRIPLE:", ciexyz)
            print("GAMMA:", gamma)

    if dib_size == 124: # V5
        intent       = read_u32(dib) # 108–112 (bV5Intent)
        profile_data = read_u32(dib) # 112–116 (bV5ProfileData)
        profile_size = read_u32(dib) # 116–120 (bV5ProfileSize)
        reserved     = read_u32(dib) # 120–124 (bV5Reserved)
        # всё это метаданные, на пиксели не влияет

    top_down = height >= 0
    height   = abs(height)

    # PALETTE
    palette = None
    if bpp <= 8:
        ncolors = 1 << bpp
        if colors_used:
            if colors_used > ncolors:
                if debug: print(f"Corrupted colors_used: {colors_used} > {ncolors}")
                colors_used = ncolors
            ncolors = colors_used

        palette = np.frombuffer(f.read(4 * ncolors), dtype=np.uint8).reshape((ncolors, 4))

        # Палитра BMP почти всегда BGRA, но альфа используется ТОЛЬКО в V4/V5
        # В обычных BMP (BITMAPINFOHEADER) альфа = 0 и игнорируется
        if dib_size in (108, 124):
            palette = palette[:, (2, 1, 0, 3)] # BGRA → RGBA
        else:
            palette = palette[:, :3] # отбрасываем альфу
            palette = palette[:, (2, 1, 0)] # BGR → RGB

        if debug:
            print(f"palette (bpp={bpp}):")
            for color in palette:
                print("  ", tuple(map(int, color)))

    # PIXELS
    if debug:
        print("tell:", f.tell())  # 1078
        print("seek:", bfOffBits) # 1078

    f.seek(bfOffBits)
    if img_size: raw = f.read(img_size)
    else:        raw = f.read(bfSize - bfOffBits)

    pix = decode_bmp_pixels(
        raw=raw,
        width=width,
        height=height,
        bpp=bpp,
        comp=comp,
        palette=palette,
        colors_used=colors_used,
        masks=(rmask, gmask, bmask, amask),
        top_down=top_down,
    )
    return pix, palette



def write_bmp(f, pix, *,
              palette      =None,
              palette_size =None,
              use_rle      =False,
              mode         =None,
              gray         =False,
              bitfields_565=False,
              top_down     =False):
    arr = np.asarray(pix)
    if arr.ndim == 2:
        arr = np.stack((arr, arr, arr), axis=-1)
    h, w, c = arr.shape

    # decide mode
    masks = (None, None, None, None)
    colors_used = 0

    if mode or palette is not None or palette_size:
        pal, idx = _build_palette_and_indices(arr, palette, palette_size, mode)
        colors_used = pal.shape[0]
        if colors_used <= 2:
            bpp = 1
            comp = 0 # plain 1bpp
        elif colors_used <= 16:
            bpp = 4
            comp = 2 # BI_RLE4
        else:
            bpp = 8
            comp = 1 if use_rle else 0 # BI_RLE8 or plain 8bpp
        pixels_raw = encode_bmp_pixels(idx.astype(np.uint8), comp=comp, bpp=bpp)
        if colors_used == 16:
            print(pixels_raw[:32].hex())

    elif bitfields_565:
        # highcolor
        bpp = 16
        comp = 3 # BI_BITFIELDS
        rmask, gmask, bmask, amask = 0xF800, 0x07E0, 0x001F, None
        masks = (rmask, gmask, bmask, amask)
        # TODO: предполагаем, что encode_bmp_pixels умеет 16bpp через BI_RGB
        pixels_raw = encode_bmp_pixels(arr, comp=0, bpp=16)

    else:
        # truecolor
        if c == 3:
            bpp = 24
        elif c == 4:
            bpp = 32
        else:
            raise ValueError("Unsupported channel count for truecolor BMP")
        comp = 0  # BI_RGB
        pixels_raw = encode_bmp_pixels(arr, comp=0, bpp=bpp)

    img_size = len(pixels_raw)

    # DIB header (BITMAPINFOHEADER)
    dib_size = 40
    hdr = BytesIO()
    write_u32(hdr, dib_size)
    write_i32(hdr, w)
    write_i32(hdr, h if top_down else -h)
    write_u16(hdr, 1)    # planes
    write_u16(hdr, bpp)
    write_u32(hdr, comp)
    write_u32(hdr, img_size)
    write_i32(hdr, 2834) # x ppm
    write_i32(hdr, 2834) # y ppm
    write_u32(hdr, colors_used)
    write_u32(hdr, 0)    # important colors
    dib_bytes = hdr.getvalue()

    # masks
    masks_bytes = b""
    if comp in (3, 6):
        rmask, gmask, bmask, amask = masks
        buf = BytesIO()
        write_u32(buf, rmask)
        write_u32(buf, gmask)
        write_u32(buf, bmask)
        if comp == 6 and amask is not None:
            write_u32(buf, amask)
        masks_bytes = buf.getvalue()

    # palette
    palette_bytes = b""
    if colors_used:
        buf = BytesIO()
        if pal.shape[1] == 4:
            for r, g, b, a in pal:
                buf.write(bytes((b, g, r, a)))
        else:
            for r, g, b in pal:
                buf.write(bytes((b, g, r, 0)))
        palette_bytes = buf.getvalue()

    bfOffBits = 14 + len(dib_bytes) + len(masks_bytes) + len(palette_bytes)
    bfSize    = bfOffBits + img_size

    # FILE HEADER
    write_bmp_header = BytesIO()
    write_bmp_header.write(b"BM")
    write_u32(write_bmp_header, bfSize)
    write_u32(write_bmp_header, 0)
    write_u32(write_bmp_header, bfOffBits)
    file_hdr = write_bmp_header.getvalue()

    # write all
    f.write(file_hdr)
    f.write(dib_bytes)
    f.write(masks_bytes)
    f.write(palette_bytes)
    f.write(pixels_raw)



# --- main ---

def load_bmp(path, debug=False):
    print(f"Reading {path}...")
    with open(path, "rb") as file:
        return read_bmp(file, debug)

def save_bmp(path, pix, **kw):
    print(f"Saving {path}...")
    with open(path, "wb") as file:
        write_bmp(file, pix, **kw)



if __name__ == "__main__":
    pix, palette = load_bmp("origin.bmp", debug=False)
    print(pix)
    save_bmp("saved_rgb.bmp", pix)

    save_bmp("saved_gray.bmp",    pix, mode="gray")
    save_bmp("saved_cga16.bmp",   pix, mode="cga16")
    save_bmp("saved_mono.bmp",    pix, mode="mono")
    save_bmp("saved_random.bmp",  pix, mode="random",  use_rle=True)
    save_bmp("saved_random2.bmp", pix, mode="random2", use_rle=True)
