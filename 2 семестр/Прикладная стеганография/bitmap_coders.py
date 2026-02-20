import struct
import numpy as np
from io import BytesIO

def read_u16(f): return struct.unpack("<H", f.read(2))[0]
def read_u32(f): return struct.unpack("<I", f.read(4))[0]

def get_pillow_Image():
    try:
        from PIL import Image
    except ImportError as e:
        raise RuntimeError("Pillow is required for BI_JPEG/BI_PNG") from e
    return Image

# ------------------------------------------------------------
# RLE DECODERS
# ------------------------------------------------------------

def decode_rle8(data, width, height, debug=False):
    out = np.zeros((height, width), dtype=np.uint8)
    x = y = 0
    i = 0
    while i < len(data) and y < height:
        count = data[i]; i += 1
        if i >= len(data):
            break
        val   = data[i]; i += 1
        if count > 0:
            if debug: print(f"+ {count:02x} {val:02x} (repeat {val} {count} times)")
            end = min(x+count, width)
            out[y, x:end] = val
            x += count
            continue
        match val:
            case 0: # next line
                if debug: print("+ 00 00 (next line)")
                x = 0
                y += 1
            case 1: # end of file
                if debug: print("+ 00 01 (EOF)")
                break
            case 2: # delta encoding (skip zero pixels)
                if i+1 >= len(data):
                    break
                dx = data[i]; dy = data[i+1]
                if debug: print(f"+ 00 02 {dx:02x} {dy:02x} (skip dx, dy)")
                i += 2
                x += dx
                y += dy
            case _: # pixel container
                n = val
                end = min(x+n, width)
                if debug: print(f"+ 00 {n:02x} {data[i:i+(end-x)].hex()} (container)")
                out[y, x:end] = data[i:i+(end-x)]
                i += n
                if n & 1: # padding
                    i += 1
                x += n
    return out

def decode_rle4(data, width, height):
    out = np.zeros((height, width), dtype=np.uint8)
    x = y = 0
    i = 0
    while i < len(data) and y < height:
        count = data[i]; i += 1
        if i >= len(data):
            break
        val   = data[i]; i += 1
        if count > 0:
            hi = val >> 4
            lo = val & 0xF
            for k in range(count):
                if x >= width:
                    break
                out[y, x] = hi if (k % 2 == 0) else lo
                x += 1
            continue
        match val:
            case 0: # next line
                x = 0
                y += 1
            case 1: # end of file
                break
            case 2: # delta encoding (skip zero pixels)
                if i+1 >= len(data):
                    break
                dx = data[i]; dy = data[i+1]
                i += 2
                x += dx
                y += dy
            case _: # pixel container
                n = val
                for k in range(n):
                    if i + k//2 >= len(data) or x >= width:
                        break
                    b = data[i + k//2]
                    out[y, x] = (b >> 4) if (k % 2 == 0) else (b & 0xF)
                    x += 1
                data_bytes = (n+1) // 2
                i += data_bytes
                if data_bytes & 1: # padding
                    i += 1
    return out

# ------------------------------------------------------------
# RLE ENCODERS (для индексных карт)
# ------------------------------------------------------------

def encode_rle8(idxmap):
    """
    RLE8 encoder with DELTA optimization.
    Supports:
      - run-length mode (>00 value of repeat)
      - EOL (00 00)
      - EOF (00 01)
      - delta jumps (00 02 dx dy)
      - absolute mode (00 >02 container)
    """
    h, w = idxmap.shape
    out = bytearray()

    y = 0
    while y < h:
        row = idxmap[y]
        x = 0
        force = True

        while x < w:
            # ----------------------------------------------------
            # 1. НЕНУЛЕВОЙ ПИКСЕЛЬ → RLE или ABSOLUTE
            # ----------------------------------------------------
            if row[x] or force:
                force = False
                val = int(row[x])
                run = 1
                while x + run < w and row[x + run] == val and run < 255:
                    run += 1

                if run >= 3:
                    if not val and x + run >= w:
                        break # EOL
                    out.append(run)
                    out.append(val)
                    x += run
                    continue

                # ABSOLUTE
                start = x
                x += 1
                zeros = 0
                while x < w and (row[x] != row[x - 1] or not row[x]) and (x - start) < 255 and zeros < 5:
                    if row[x]: zeros = 0
                    else: zeros += 1
                    x += 1
                if zeros == 5:
                    x -= 5

                n = x - start
                if n == 1:
                    # один пиксель — кодируем как обычный RLE длиной 1
                    out.append(1)
                    out.append(int(row[start]))
                elif n == 2:
                    # два пикселя — либо два RLE по 1, либо RLE2, если одинаковые
                    v0 = int(row[start])
                    v1 = int(row[start + 1])
                    if v0 == v1:
                        out.append(2)
                        out.append(v0)
                    else:
                        out.append(1)
                        out.append(v0)
                        out.append(1)
                        out.append(v1)
                else: # n >= 3
                    # только тут можно делать настоящий ABSOLUTE
                    out.append(0)
                    out.append(n)
                    out.extend(row[start:x].astype(np.uint8).tobytes())
                    if n & 1:
                        out.append(0)
                continue

            # ----------------------------------------------------
            # 2. НУЛИ → не до конца строки
            # ----------------------------------------------------
            zeros = 1
            while x + zeros < w and row[x + zeros] == 0 and zeros < 255:
                zeros += 1

            if x + zeros < w:
                if zeros < 5:
                    # мало нулей — пусть их заберёт ABS-последовательность
                    force = True
                    continue
                # 3 4 5 0 0 0 0 7 8 9 -> (0 3 3 4 5) (4 0) (0 3 7 8 9) = 12 bytes
                #                     -> (0 10) 3 4 5 0 0 0 0 7 8 9    = 12 bytes
                # стоит сделать уже 5 нулей, то ABS станет выгоднее!
                while zeros > 255:
                    out.extend((255, 0))
                    x += 255
                    zeros -= 255
                out.append(zeros)
                out.append(0)
                x += zeros
                continue

            # ----------------------------------------------------
            # 3. НУЛИ → после конца строки
            # ----------------------------------------------------
            nx = ny = None
            for yy in range(y + 1, min(h, y + 256)): # limit for dy <= 255
                yy_row = idxmap[yy]
                for xx in range(w):
                    if yy_row[xx]:
                        nx, ny = xx, yy
                        break
                if nx is not None:
                    break

            if nx is None:
                # все нули до самого конца растра
                out.extend(b"\x00\x00") # EOL
                out.extend(b"\x00\x01") # EOF
                return out

            dx = nx - x
            dy = ny - y
            assert dy <= 255

            if dx > 0:
                if dx > 255: dx = 255
                out.extend((0, 2, dx, dy))
                x += dx
                y += dy
                row = idxmap[y]
            else: # dx <= 0:
                if x == 0 and dy == 1:
                    break # EOL
                # если целевой пиксель левее текущего — сначала завершаем строку, потом прыгаем вниз
                dx += x
                dy -= 1
                x = 0
                y += 1
                out.extend(b"\x00\x00") # EOL
                row = idxmap[y]

        out.extend(b"\x00\x00") # EOL
        y += 1

    out.extend(b"\x00\x01") # EOF
    return out

def encode_rle4(idxmap):
    """
    RLE4 encoder with DELTA optimization.
    Supports:
      - run-length mode (>00 value of repeat)   nibble! v0 << 4 | v0
      - EOL (00 00)
      - EOF (00 01)
      - delta jumps (00 02 dx dy)
      - absolute mode (00 >02 container)        nibble! container is packed
    """
    h, w = idxmap.shape
    out = bytearray()

    y = 0
    while y < h:
        row = idxmap[y]
        x = 0
        force = True

        while x < w:
            # ----------------------------------------------------
            # 1. НЕНУЛЕВОЙ ПИКСЕЛЬ → RLE или ABSOLUTE
            # ----------------------------------------------------
            val = int(row[x]) & 0xF
            if val or force:
                force = False
                run = 1
                while x + run < w and row[x + run] & 0xF == val and run < 255:
                    run += 1

                if run >= 3:
                    if not val and x + run >= w:
                        break # EOL
                    out.append(run)
                    out.append(val << 4 | val) # O_o   по тому я ввёл 1.5 пункт :)
                    x += run
                    continue

                # ----------------------------------------------------
                # 1.5. ЧЕРЕДУЮЩИЙСЯ ПАТТЕРН ABABAB...
                # ----------------------------------------------------
                if x + 1 < w:
                    v0 = row[x] & 0xF
                    v1 = row[x+1] & 0xF
                    if v0 != v1:
                        run2 = 2
                        while x + run2 < w and (row[x + run2] & 0xF) == (v1 if run2 & 1 else v0) and run2 < 255:
                            run2 += 1

                        # AB‑паттерн выгоден только если >= 4 пикселей
                        if run2 >= 4:
                            out.append(run2)
                            out.append((v0 << 4) | v1)
                            x += run2
                            continue

                # ABSOLUTE
                start = x
                x += 1
                zeros = 0
                while x < w and (x - start) < 255 and zeros < 5:
                    pix = row[x] & 0xF
                    if pix != row[x - 1] & 0xF or not pix:
                        if pix: zeros = 0
                        else: zeros += 1
                        x += 1
                    else: break
                if zeros == 5:
                    x -= 5

                n = x - start # количество nibble
                if n == 1:
                    # один пиксель — кодируем как обычный RLE длиной 1
                    v0 = int(row[start]) & 0xF
                    out.append(1)
                    out.append(v0 << 4 | v0)
                elif n == 2:
                    # два пикселя — либо два RLE по 1, либо RLE2, если одинаковые
                    v0 = int(row[start]) & 0xF
                    v1 = int(row[start + 1]) & 0xF
                    if v0 == v1:
                        out.append(2)
                        out.append(v0 << 4 | v0)
                    else:
                        out.append(1)
                        out.append(v0 << 4 | v0)
                        out.append(1)
                        out.append(v1 << 4 | v1)
                else: # n >= 3
                    # только тут можно делать настоящий ABSOLUTE
                    out.append(0)
                    out.append(n)
                    # упаковываем nibble в байты
                    for i in range(0, n, 2):
                        a = row[start + i] & 0xF
                        b = row[start + i + 1] & 0xF if i + 1 < n else 0
                        out.append(a << 4 | b)
                    if (n + 1) // 2 & 1:
                        out.append(0) # padding
                continue

            # ----------------------------------------------------
            # 2. НУЛИ → не до конца строки
            # ----------------------------------------------------
            zeros = 1
            while x + zeros < w and row[x + zeros] & 0xF == 0 and zeros < 255:
                zeros += 1

            if x + zeros < w:
                if zeros < 5:
                    # мало нулей — пусть их заберёт ABS-последовательность
                    force = True
                    continue
                # 3 4 5 0 0 0 0 7 8 9 -> (0 3 3 4 5) (4 0) (0 3 7 8 9) = 12 bytes
                #                     -> (0 10) 3 4 5 0 0 0 0 7 8 9    = 12 bytes
                # стоит сделать уже 5 нулей, то ABS станет выгоднее!
                while zeros > 255:
                    out.extend((255, 0))
                    x += 255
                    zeros -= 255
                out.append(zeros)
                out.append(0)
                x += zeros
                continue

            # ----------------------------------------------------
            # 3. НУЛИ → после конца строки
            # ----------------------------------------------------
            ny = None
            nx = None
            for yy in range(y + 1, min(h, y + 256)): # limit for dy <= 255
                yy_row = idxmap[yy]
                for xx in range(w):
                    if yy_row[xx] & 0xF:
                        nx, ny = xx, yy
                        break
                if nx is not None:
                    break

            if nx is None:
                # все нули до самого конца растра
                out.extend(b"\x00\x00") # EOL
                out.extend(b"\x00\x01") # EOF
                return out

            dx = nx - x
            dy = ny - y
            assert dy <= 255

            if dx > 0:
                if dx > 255: dx = 255
                out.extend((0, 2, dx, dy))
                x += dx
                y += dy
                row = idxmap[y]
            else: # dx <= 0:
                if x == 0 and dy == 1:
                    break # EOL
                # если целевой пиксель левее текущего — сначала завершаем строку, потом прыгаем вниз
                dx += x
                dy -= 1
                x = 0
                y += 1
                out.extend(b"\x00\x00") # EOL
                row = idxmap[y]
            # print("end of line", x, y, "| dxy:", dx, dy)
            # exit()

        out.extend(b"\x00\x00") # EOL
        y += 1

    out.extend(b"\x00\x01") # EOF
    return out

# ------------------------------------------------------------
# RGB DECODER / ENCODER (vectorized)
# ------------------------------------------------------------

def decode_rgb(raw, width, height, bpp, top_down):
    row_size = ((bpp * width + 31) // 32) * 4

    if bpp == 24:
        arr = np.frombuffer(raw, dtype=np.uint8)
        arr = arr.reshape((height, row_size))[:, :width*3]
        arr = arr.reshape((height, width, 3))
        return arr if not top_down else arr[::-1]

    if bpp == 32:
        arr = np.frombuffer(raw, dtype=np.uint8)
        arr = arr.reshape((height, row_size))[:, :width*4]
        arr = arr.reshape((height, width, 4))
        return arr if not top_down else arr[::-1]

    if bpp == 8:
        arr = np.frombuffer(raw, dtype=np.uint8)
        arr = arr.reshape((height, row_size))[:, :width]
        return arr if not top_down else arr[::-1]

    raise ValueError(f"Unsupported bpp for BI_RGB: {bpp}")

def encode_rgb(arr, bpp):
    h, w = arr.shape[:2]
    buf = bytearray()

    if arr.ndim == 2 and bpp == 1:
        # 1‑битная упаковка: 8 пикселей → 1 байт
        row_bits = (w + 7) // 8             # байт на строку до выравнивания
        row_size = (row_bits + 3) // 4 * 4  # выравнивание до 4 байт
        pad = row_size - row_bits

        for y in range(h):
            row = arr[y]
            byte = 0
            bitpos = 7

            for x in range(w):
                if row[x]:
                    byte |= (1 << bitpos)
                bitpos -= 1
                if bitpos < 0:
                    buf.append(byte)
                    byte = 0
                    bitpos = 7
            if bitpos != 7: # если остались недозаполненные биты
                buf.append(byte)
            buf.extend(b"\x00" * pad)

        return buf

    if arr.ndim == 2 and bpp == 8:
        row_size = ((bpp * w + 31) // 32) * 4
        pad = row_size - w
        for y in range(h):
            buf.extend(arr[y].tobytes())
            if pad > 0:
                buf.extend(b"\x00" * pad)
        return buf

    if arr.ndim == 3 and arr.shape[2] == 3 and bpp == 24:
        row_size = ((bpp * w + 31) // 32) * 4
        pad = row_size - w*3
        for y in range(h):
            buf.extend(arr[y].tobytes())
            if pad > 0:
                buf.extend(b"\x00" * pad)
        return buf

    if arr.ndim == 3 and arr.shape[2] == 4 and bpp == 32:
        buf.extend(arr.tobytes())
        return buf

    raise ValueError("Unsupported array shape/bpp for encode_rgb")

# ------------------------------------------------------------
# BITFIELDS DECODER (vectorized)
# ------------------------------------------------------------

def _extract_mask(v, mask):
    # gmask          = 0b0000011111100000 (RGB565)
    # gmask & -gmask = 0b0000000000100000 (first bit)
    # shift          = 5 zero bits  ^^^^^
    shift = (mask & -mask).bit_length() - 1
    return (v & mask) >> shift

def _mask_max(mask):
    shift = (mask & -mask).bit_length() - 1
    return mask >> shift

def decode_bitfields(raw, width, height, bpp, rmask, gmask, bmask, top_down):
    row_size = ((bpp * width + 31) // 32) * 4
    px = np.frombuffer(raw, dtype=np.uint8)
    px = px.reshape((height, row_size))[:, :width*(bpp//8)]

    if bpp == 16: # 16-bit pixels → uint16
        v = px.view(np.uint16).reshape((height, width))
    elif bpp == 32: # 32-bit pixels → uint32
        v = px.view(np.uint32).reshape((height, width))
    else: raise ValueError(f"BITFIELDS: unsupported bpp={bpp}")

    R = _extract_mask(v, rmask)
    G = _extract_mask(v, gmask)
    B = _extract_mask(v, bmask)

    R = R * 255 // _mask_max(rmask)
    G = G * 255 // _mask_max(gmask)
    B = B * 255 // _mask_max(bmask)

    arr = np.stack([R, G, B], axis=-1).astype(np.uint8)
    return arr if not top_down else arr[::-1]

def decode_bitfields_alpha(raw, width, height, bpp, rmask, gmask, bmask, amask, top_down):
    row_size = ((bpp * width + 31) // 32) * 4
    px = np.frombuffer(raw, dtype=np.uint8)
    px = px.reshape((height, row_size))[:, :width*(bpp//8)]

    if bpp == 16: # uint16 → 16-bit pixels
        v = px.view(np.uint16).reshape((height, width))
    elif bpp == 32: # uint32 → 32-bit pixels
        v = px.view(np.uint32).reshape((height, width))
    else: raise ValueError(f"ALPHABITFIELDS: unsupported bpp={bpp}")

    R = _extract_mask(v, rmask)
    G = _extract_mask(v, gmask)
    B = _extract_mask(v, bmask)
    A = _extract_mask(v, amask)

    R = R * 255 // _mask_max(rmask)
    G = G * 255 // _mask_max(gmask)
    B = B * 255 // _mask_max(bmask)
    A = A * 255 // _mask_max(amask)

    arr = np.stack([R, G, B, A], axis=-1).astype(np.uint8)
    return arr if not top_down else arr[::-1]

# ------------------------------------------------------------
# CMYK DECODER (vectorized)
# ------------------------------------------------------------

def cmyk_row_size(width):
    # BI_CMYK = 32 bpp → 4 bytes per pixel
    bpp = 32
    row_size = ((bpp * width + 31) // 32) * 4
    #                          ^^     ^^
    # For any bpp, alignment is up to 4 bytes
    return row_size

def decode_cmyk(raw, width, height, top_down):
    row_size = cmyk_row_size(width) # BMP row alignment
    px = np.frombuffer(raw, dtype=np.uint8)
    px = px.reshape((height, row_size))[:, :width*4]
    px = px.reshape((height, width, 4))

    C, M, Y, K = px[..., 0], px[..., 1], px[..., 2], px[..., 3]
    R = 255 - np.minimum(255, C + K)
    G = 255 - np.minimum(255, M + K)
    B = 255 - np.minimum(255, Y + K)
    rgb = np.stack([R,G,B], axis=-1).astype(np.uint8)
    return rgb if not top_down else rgb[::-1]

def decode_cmyk_rle8(raw, colors_used, width, height, top_down):
    # raw = palette(4*N bytes) + rle_stream
    palette_size = colors_used * 4
    palette = np.frombuffer(raw[:palette_size], dtype=np.uint8).reshape((colors_used, 4))
    rle_stream = raw[palette_size:]

    idxmap = decode_rle8(rle_stream, width, height)
    cmyk = palette[idxmap]

    C, M, Y, K = cmyk[..., 0], cmyk[..., 1], cmyk[..., 2], cmyk[..., 3]
    R = 255 - np.minimum(255, C + K)
    G = 255 - np.minimum(255, M + K)
    B = 255 - np.minimum(255, Y + K)

    rgb = np.stack([R,G,B], axis=-1).astype(np.uint8)
    return rgb if not top_down else rgb[::-1]

def decode_cmyk_rle4(raw, colors_used, width, height, top_down):
    palette_size = colors_used * 4
    palette = np.frombuffer(raw[:palette_size], dtype=np.uint8).reshape((colors_used, 4))
    rle_stream = raw[palette_size:]

    idxmap = decode_rle4(rle_stream, width, height)
    cmyk = palette[idxmap]

    C, M, Y, K = cmyk[..., 0], cmyk[..., 1], cmyk[..., 2], cmyk[..., 3]
    R = 255 - np.minimum(255, C + K)
    G = 255 - np.minimum(255, M + K)
    B = 255 - np.minimum(255, Y + K)

    rgb = np.stack([R,G,B], axis=-1).astype(np.uint8)
    return rgb if not top_down else rgb[::-1]

# ------------------------------------------------------------
# CMYK ENCODER (vectorized)
# ------------------------------------------------------------

def encode_cmyk(arr):
    R, G, B = arr[...,0], arr[...,1], arr[...,2]
    C = 255 - R
    M = 255 - G
    Y = 255 - B
    K = np.zeros_like(C)

    cmyk = np.stack([C, M, Y, K], axis=-1).astype(np.uint8)

    h, w = arr.shape[:2]
    row_size = cmyk_row_size(w) # BMP row alignment
    pad = row_size - w * 4

    buf = bytearray()
    for y in range(h):
        buf.extend(cmyk[y].tobytes())
        if pad: buf.extend(b"\x00" * pad)
    return buf

def encode_cmyk_rle8(arr):
    h, w = arr.shape[:2]

    # RGB → CMYK
    R, G, B = arr[..., 0], arr[..., 1], arr[..., 2]
    C = 255 - R
    M = 255 - G
    Y = 255 - B
    K = np.zeros_like(C)
    cmyk = np.stack([C, M, Y, K], axis=-1).astype(np.uint8)

    # строим палитру 256 CMYK-цветов
    flat = cmyk.reshape((-1, 4))
    uniq, idx = np.unique(flat, axis=0, return_inverse=True)

    if uniq.shape[0] > 256:
        raise ValueError("Too many CMYK colors for RLE8 (max 256)")

    palette = np.zeros((256, 4), dtype=np.uint8)
    palette[:uniq.shape[0]] = uniq

    idxmap = idx.reshape((h, w)).astype(np.uint8)

    rle = encode_rle8(idxmap)

    buf = bytearray()
    buf.extend(palette.tobytes())
    buf.extend(rle)
    return buf

def encode_cmyk_rle4(arr):
    h, w = arr.shape[:2]

    R, G, B = arr[..., 0], arr[..., 1], arr[..., 2]
    C = 255 - R
    M = 255 - G
    Y = 255 - B
    K = np.zeros_like(C)
    cmyk = np.stack([C,M,Y,K], axis=-1).astype(np.uint8)

    flat = cmyk.reshape((-1, 4))
    uniq, idx = np.unique(flat, axis=0, return_inverse=True)

    if uniq.shape[0] > 16:
        raise ValueError("Too many CMYK colors for RLE4 (max 16)")

    palette = np.zeros((16, 4), dtype=np.uint8)
    palette[:uniq.shape[0]] = uniq

    idxmap = idx.reshape((h, w)).astype(np.uint8)

    rle = encode_rle4(idxmap)

    buf = bytearray()
    buf.extend(palette.tobytes())
    buf.extend(rle)
    return buf

# ------------------------------------------------------------
# MAIN DISPATCHER (match-case)
# ------------------------------------------------------------

# https://github.com/image-rs/image/blob/main/src/codecs/bmp/decoder.rs#L37-L46
BI_RGB            =  0
BI_RLE8           =  1
BI_RLE4           =  2
BI_BITFIELDS      =  3
BI_JPEG           =  4 # Used in legacy Windows pass-through printing path (not supported) and for RLE24
BI_PNG            =  5 # Used in legacy Windows pass-through printing path - not supported
BI_ALPHABITFIELDS =  6
BI_CMYK           = 11
BI_CMYKRLE8       = 12
BI_CMYKRLE4       = 13

BMP_COMPRESSION_to_str = {
     0: "BI_RGB (no compression)",
     1: "BI_RLE8",
     2: "BI_RLE4",
     3: "BI_BITFIELDS",
     4: "BI_JPEG",
     5: "BI_PNG",
     6: "BI_ALPHABITFIELDS",
    11: "BI_CMYK",
    12: "BI_CMYKRLE8",
    13: "BI_CMYKRLE4",
}

def decode_bmp_pixels(raw, width, height, bpp, comp, palette, colors_used, masks, top_down):
    rmask, gmask, bmask, amask = masks

    match comp:
        case 0: # BI_RGB
            return decode_rgb(raw, width, height, bpp, top_down)

        case 1: # BI_RLE8
            idx = decode_rle8(raw, width, height)
            if palette is None:
                raise ValueError("RLE8 requires palette for decoding to RGB")
            rgb = palette[idx]
            return rgb if not top_down else rgb[::-1]

        case 2: # BI_RLE4
            idx = decode_rle4(raw, width, height)
            if palette is None:
                raise ValueError("RLE4 requires palette for decoding to RGB")
            rgb = palette[idx]
            return rgb if not top_down else rgb[::-1]

        case 3: # BI_BITFIELDS
            if rmask is None or gmask is None or bmask is None:
                raise ValueError("BITFIELDS requires RGB masks")
            return decode_bitfields(raw, width, height, bpp, rmask, gmask, bmask, top_down)

        case 6: # BI_ALPHABITFIELDS
            if rmask is None or gmask is None or bmask is None or amask is None:
                raise ValueError("ALPHABITFIELDS requires RGBA masks")
            return decode_bitfields_alpha(raw, width, height, bpp, rmask, gmask, bmask, amask, top_down)

        case 4: # BI_JPEG
            Image = get_pillow_Image()
            img = Image.open(BytesIO(raw)).convert("RGBA")
            return np.array(img)

        case 5: # BI_PNG
            Image = get_pillow_Image()
            img = Image.open(BytesIO(raw)).convert("RGBA")
            return np.array(img)

        case 11: # BI_CMYK
            return decode_cmyk(raw, width, height, top_down)

        case 12: # BI_CMYKRLE8
            return decode_cmyk_rle8(raw, colors_used, width, height, top_down)

        case 13: # BI_CMYKRLE4
            return decode_cmyk_rle4(raw, colors_used, width, height, top_down)

        case _:
            comp_name = BMP_COMPRESSION_to_str.get(comp, f"unknown ({comp})")
            raise ValueError(f"Unknown BMP compression: {comp_name}")

def encode_bmp_pixels(arr, comp, *, bpp=None, palette=None, masks=None):
    rmask, gmask, bmask, amask = masks if masks else (None, None, None, None)

    match comp:
        case 0: # BI_RGB
            if bpp is None:
                if arr.ndim == 2:
                    bpp = 8
                elif arr.ndim == 3 and arr.shape[2] == 3:
                    bpp = 24
                elif arr.ndim == 3 and arr.shape[2] == 4:
                    bpp = 32
                else:
                    raise ValueError("Cannot infer bpp for BI_RGB")
            if bpp in (1, 8, 24, 32):
                return encode_rgb(arr, bpp)
            if bpp == 4:
                raise ValueError("BI_RGB does not support 4 bpp. Use BI_RLE4 instead.")
            if bpp == 2:
                raise ValueError("2 bpp BMP does not exist in the BMP specification.")
            raise ValueError(f"unknown bpp: {bpp}")

        case 1: # BI_RLE8
            if arr.ndim != 2 or arr.dtype != np.uint8:
                raise ValueError("BI_RLE8 encoder expects index map (H, W), uint8")
            return encode_rle8(arr)

        case 2: # BI_RLE4
            if arr.ndim != 2 or arr.dtype != np.uint8:
                raise ValueError("BI_RLE4 encoder expects index map (H, W), uint8")
            return encode_rle4(arr)

        case 3 | 6: # BI_BITFIELDS | BI_ALPHABITFIELDS
            raise ValueError("BITFIELDS encoding not implemented (decoder only)")

        case 4: # BI_JPEG
            Image = get_pillow_Image()
            buf = BytesIO()
            Image.fromarray(arr).save(buf, format="JPEG")
            return bytearray(buf.getvalue())

        case 5: # BI_PNG
            Image = get_pillow_Image()
            buf = BytesIO()
            Image.fromarray(arr).save(buf, format="PNG")
            return bytearray(buf.getvalue())

        case 11: # BI_CMYK
            return encode_cmyk(arr)

        case 12: # BI_CMYKRLE8
            return encode_cmyk_rle8(arr)

        case 13: # BI_CMYKRLE4
            return encode_cmyk_rle4(arr)

        case _:
            comp_name = BMP_COMPRESSION_to_str.get(comp, f"unknown ({comp})")
            raise ValueError(f"Unknown BMP compression: {comp_name}")



# ------------------------------------------------------------
# TESTS
# ------------------------------------------------------------

def test_rle8_case(idxmap, debug=False):
    h, w = idxmap.shape
    raw_size = h * w

    if debug: print("Original:"); print_complex_map(idxmap)
    enc = encode_rle8(idxmap)
    dec = decode_rle8(enc, w, h, debug)

    rle_size = len(enc)

    if not np.array_equal(idxmap, dec):
        print("❌ RLE8 FAIL")
        if not debug:
            print("Original:"); print_complex_map(idxmap)
            print("Decoded:");  print_complex_map(dec)
        print(f"Raw size: {raw_size} bytes")
        print(f"RLE size: {rle_size} bytes")
        print("RLE:", enc.hex())
        raise AssertionError("RLE8 mismatch")

    if debug: print("Decoded:"); print_complex_map(dec)
    print(f"✔ RLE8 OK  | {raw_size} → {rle_size} bytes")
    return True

def test_rle4_case(idxmap, debug=False):
    h, w = idxmap.shape
    raw_size = h * w # индексная карта всё равно хранится как байты

    if debug: print("Original:"); print_complex_map(idxmap)
    enc = encode_rle4(idxmap)
    dec = decode_rle4(enc, w, h) # debug is not supported, т.к. всё заработало с первого раза! :)

    rle_size = len(enc)

    if not np.array_equal(idxmap, dec):
        print("❌ RLE4 FAIL")
        if not debug:
            print("Original:"); print_complex_map(idxmap)
            print("Decoded:");  print_complex_map(dec)
        print(f"Raw size: {raw_size} bytes")
        print(f"RLE size: {rle_size} bytes")
        print("RLE:", enc.hex())
        raise AssertionError("RLE4 mismatch")

    if debug: print("Decoded:"); print_complex_map(dec)
    print(f"✔ RLE4 OK  | {raw_size} → {rle_size} bytes")
    return True

# ------------------------------------------------------------
# ROW GENERATORS (унифицированные)
# ------------------------------------------------------------

def zeros_row(w):
    return np.zeros(w, dtype=np.uint8)

def solid_row(w, val=None):
    if val is None:
        val = np.random.randint(1, 256)
    return np.full(w, val, dtype=np.uint8)

def stripes_row(w, offset=0):
    return np.array([(x + offset) & 1 for x in range(w)], dtype=np.uint8)

def sparse_row(w, density=0.05):
    row = np.zeros(w, dtype=np.uint8)
    mask = np.random.rand(w) < density
    row[mask] = np.random.randint(1, 256, mask.sum(), dtype=np.uint8)
    return row

def random_row(w):
    return np.random.randint(0, 256, w, dtype=np.uint8)

def partial_right_zeros_row(w):
    if w < 4: return np.zeros(w, dtype=np.uint8)
    k = np.random.randint(1, w//2)
    row = np.random.randint(1, 256, w, dtype=np.uint8)
    row[-k:] = 0
    return row

def partial_left_zeros_row(w):
    if w < 4: return np.zeros(w, dtype=np.uint8)
    k = np.random.randint(1, w//2)
    row = np.random.randint(1, 256, w, dtype=np.uint8)
    row[:k] = 0
    return row

# ------------------------------------------------------------
# COMPLEX MAP GENERATOR
# ------------------------------------------------------------

def print_complex_map(raster):
    for row in raster:
        data = ' '.join(map(lambda n: hex(n)[2:].rjust(2, '0'), row))
        print(data)

def make_complex_map(w, max_blocks=50):
    rows = []

    for _ in range(max_blocks):
        block_type = np.random.choice([
            "zeros", "solid", "stripes", "sparse", "random"
        ])

        if block_type == "zeros":
            # переходные строки ПЕРЕД zeros
            for _ in range(np.random.randint(1, 4)):
                rows.append(partial_right_zeros_row(w))

            # сам zeros-блок
            for _ in range(np.random.randint(1, 6)):
                rows.append(zeros_row(w))

            # переходные строки ПОСЛЕ zeros
            for _ in range(np.random.randint(1, 4)):
                rows.append(partial_left_zeros_row(w))

        elif block_type == "solid":
            for _ in range(np.random.randint(1, 6)):
                rows.append(solid_row(w))

        elif block_type == "stripes":
            offset = np.random.randint(0, 2)
            for _ in range(np.random.randint(1, 6)):
                rows.append(stripes_row(w, offset))

        elif block_type == "sparse":
            for _ in range(np.random.randint(1, 6)):
                rows.append(sparse_row(w))

        elif block_type == "random":
            for _ in range(np.random.randint(1, 6)):
                rows.append(random_row(w))

    return np.vstack(rows)

# ------------------------------------------------------------
# FULL RLE TEST SUITE
# ------------------------------------------------------------

def run_all_rle_tests(test_rounds=50, row_rounds=50, debug=False):
    print("=== RLE8 / RLE4 COMPLEX TESTS ===")

    for r in range(test_rounds):
        w = np.random.randint(1, 513)  # ширина 1..512
        idx  = make_complex_map(w, row_rounds)
        idx4 = idx & 0xF

        print(f"Round {r+1}/{test_rounds}  (width={w}, height={idx.shape[0]})")

        # RLE8
        test_rle8_case(idx, debug)
      # test_rle8_case(idx4, debug) явно видно, что rle4 на 16-битных картах в 2-3 раза лучше!

        # RLE4 (ограничиваем палитру)
        test_rle4_case(idx4, debug)

    print("\n✔ ALL COMPLEX RLE TESTS PASSED")

# ------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------

if __name__ == "__main__":
    print_complex_map(make_complex_map(32))
    print("~" * 77)
    np.random.seed(123)
    run_all_rle_tests(256)
