# ~~~ Действительно полезная информация среди ВСЕХ заголовочников ~~~

# ROTL32(v, n)         =  ((v << n) | (v >> (32 - n))) & 0xFFFFFFFF
# U8TO32_LITTLE(p)     =  int.from_bytes(p, "little")
# U32TO8_LITTLE(p, v)  =  v.to_bytes(4, "little")
# T32(x) / U32V(x)     =  x & 0xFFFFFFFF

class SosemanukKeyContext:
    def __init__(self):
        self.sk = [0] * 100  # расписание ключа (Serpent24)

class SosemanukRunContext:
    def __init__(self):
        self.s = [0] * 10         # LFSR
        self.r1 = 0               # FSM
        self.r2 = 0
        self.buf = bytearray(80)  # байты keystream
        self.ptr = 0


# ~~~ Отладчик ~~~

from functools import cache
from hashlib import sha256

SOSEMANUK_VECTOR = False  # Просто debug-режим, должен выводить содержимое TEST_VECTOR_128.txt
DTV_digest = sha256()
@cache
def _dtv_fp():
    return open("MY_DETAILED_TEST_VECTOR.txt", "w", newline="")
    # newline=""  переключает Unix(LF) на Windows(CR LF), т.е. минус '\r' перед '\n'
def DTV_print(
    *values: object,
    sep: str | None = " ",
    end: str | None = "\n",
):
    block = sep.join(map(str, values))
    if SOSEMANUK_VECTOR:
        print(block, end=end)
      # print(block, end=end, file=_dtv_fp(), flush=True)
        DTV_digest.update(block.encode("utf-8"))
        DTV_digest.update(end.encode("utf-8"))


# ~~~ Заспидранненый Серпент ~~~

"""
 * Serpent S-boxes, implemented in bitslice mode. These circuits have
 * been published by Dag Arne Osvik ("Speeding up Serpent", published in
 * the 3rd AES Candidate Conference) and work on five 32-bit registers:
 * the four inputs, and a fifth scratch register. There are meant to be
 * quite fast on Pentium-class processors. These are not the fastest
 * published, but they are "fast enough" and they are unencumbered as
 * far as intellectual property is concerned (note: these are rewritten
 * from the article itself, and hence are not covered by the GPL on
 * Dag's code, which was not used here).
 *
 * The output bits are permuted. Here is the correspondance:
 *   S0:  1420
 *   S1:  2031
 *   S2:  2314
 *   S3:  1234
 *   S4:  1403
 *   S5:  1302
 *   S6:  0142
 *   S7:  4310
 * (for instance, the output of S0 is in "r1, r4, r2, r0").
"""

def _rotl(x: int, n: int) -> int:
    """ROTL(x, n), 0 < n < 32."""
    x &= 0xFFFFFFFF
    return ((x << n) | (x >> (32 - n))) & 0xFFFFFFFF

def _not(x: int) -> int:
    """Побитовое ~ с приведением к u32."""
    return (~x) & 0xFFFFFFFF


def _S0(r0, r1, r2, r3, r4):
    r3 ^= r0;   r4  = r1
    r1 &= r3;   r4 ^= r2
    r1 ^= r0;   r0 |= r3
    r0 ^= r4;   r4 ^= r3
    r3 ^= r2;   r2 |= r1
    r2 ^= r4;   r4 = _not(r4)
    r4 |= r1;   r1 ^= r3
    r1 ^= r4;   r3 |= r0
    r1 ^= r3;   r4 ^= r3
    return r0, r1, r2, r3, r4

def _S1(r0, r1, r2, r3, r4):
    r0 = _not(r0);  r2 = _not(r2)
    r4  = r0;       r0 &= r1
    r2 ^= r0;       r0 |= r3
    r3 ^= r2;       r1 ^= r0
    r0 ^= r4;       r4 |= r1
    r1 ^= r3;       r2 |= r0
    r2 &= r4;       r0 ^= r1
    r1 &= r2
    r1 ^= r0;       r0 &= r2
    r0 ^= r4
    return r0, r1, r2, r3, r4

def _S2(r0, r1, r2, r3, r4):
    r4  = r0;  r0 &= r2
    r0 ^= r3;  r2 ^= r1
    r2 ^= r0;  r3 |= r4
    r3 ^= r1;  r4 ^= r2
    r1  = r3;  r3 |= r4
    r3 ^= r0;  r0 &= r1
    r4 ^= r0;  r1 ^= r3
    r1 ^= r4;  r4 = _not(r4)
    return r0, r1, r2, r3, r4

def _S3(r0, r1, r2, r3, r4):
    r4  = r0;  r0 |= r3
    r3 ^= r1;  r1 &= r4
    r4 ^= r2;  r2 ^= r3
    r3 &= r0;  r4 |= r1
    r3 ^= r4;  r0 ^= r1
    r4 &= r0;  r1 ^= r3
    r4 ^= r2;  r1 |= r0
    r1 ^= r2;  r0 ^= r3
    r2  = r1;  r1 |= r3
    r1 ^= r0
    return r0, r1, r2, r3, r4

def _S4(r0, r1, r2, r3, r4):
    r1 ^= r3;       r3 = _not(r3)
    r2 ^= r3;       r3 ^= r0
    r4  = r1;       r1 &= r3
    r1 ^= r2;       r4 ^= r3
    r0 ^= r4;       r2 &= r4
    r2 ^= r0;       r0 &= r1
    r3 ^= r0;       r4 |= r1
    r4 ^= r0;       r0 |= r3
    r0 ^= r2;       r2 &= r3
    r0 = _not(r0);  r4 ^= r2
    return r0, r1, r2, r3, r4

def _S5(r0, r1, r2, r3, r4):
    r0 ^= r1;       r1 ^= r3
    r3 = _not(r3);  r4  = r1
    r1 &= r0;       r2 ^= r3
    r1 ^= r2;       r2 |= r4
    r4 ^= r3;       r3 &= r1
    r3 ^= r0;       r4 ^= r1
    r4 ^= r2;       r2 ^= r0
    r0 &= r3;       r2 = _not(r2)
    r0 ^= r4;       r4 |= r3
    r2 ^= r4
    return r0, r1, r2, r3, r4

def _S6(r0, r1, r2, r3, r4):
    r2 = _not(r2);  r4  = r3
    r3 &= r0;       r0 ^= r4
    r3 ^= r2;       r2 |= r4
    r1 ^= r3;       r2 ^= r0
    r0 |= r1;       r2 ^= r1
    r4 ^= r0;       r0 |= r3
    r0 ^= r2;       r4 ^= r3
    r4 ^= r0;       r3 = _not(r3)
    r2 &= r4
    r2 ^= r3
    return r0, r1, r2, r3, r4

def _S7(r0, r1, r2, r3, r4):
    r4  = r1;  r1 |= r2
    r1 ^= r3;  r4 ^= r2
    r2 ^= r1;  r3 |= r4
    r3 &= r0;  r4 ^= r2
    r3 ^= r1;  r1 |= r4
    r1 ^= r0;  r0 |= r4
    r0 ^= r2;  r1 ^= r4
    r2 ^= r1;  r1 &= r0
    r1 ^= r4;  r2 = _not(r2)
    r2 |= r0
    r4 ^= r2
    return r0, r1, r2, r3, r4


SBOX_TABLES = {
    0: [3, 8, 15, 1, 10, 6, 5, 11, 14, 13, 4, 2, 7, 0, 9, 12],
    1: [15, 12, 2, 7, 9, 0, 5, 10, 1, 11, 14, 8, 6, 13, 3, 4],
    2: [8, 6, 7, 9, 3, 12, 10, 15, 13, 1, 14, 4, 0, 11, 5, 2],
    3: [0, 15, 11, 8, 12, 9, 6, 3, 13, 1, 2, 4, 10, 7, 5, 14],
    4: [1, 15, 8, 3, 12, 0, 11, 6, 2, 5, 4, 10, 9, 14, 7, 13],
    5: [15, 5, 2, 11, 4, 10, 9, 12, 0, 3, 14, 8, 13, 6, 7, 1],
    6: [7, 2, 12, 5, 8, 4, 6, 11, 14, 9, 1, 15, 13, 3, 10, 0],
    7: [1, 13, 15, 0, 14, 8, 2, 11, 7, 4, 12, 10, 9, 3, 5, 6],
}

# (функция, [индекс регистра для бита 0, 1, 2, 3] выхода)
# из комментария "S0: 1420", "S3: 1234" и т.д.
SBOX_FUNCS = {
    0: (_S0, (1, 4, 2, 0)),   # 1420
    1: (_S1, (2, 0, 3, 1)),   # 2031
    2: (_S2, (2, 3, 1, 4)),   # 2314
    3: (_S3, (1, 2, 3, 4)),   # 1234
    4: (_S4, (1, 4, 0, 3)),   # 1403
    5: (_S5, (1, 3, 0, 2)),   # 1302
    6: (_S6, (0, 1, 4, 2)),   # 0142
    7: (_S7, (4, 3, 1, 0)),   # 4310
}

def _run_sbox_bitslice(func, x, bit_pos=0):
    """Кладём ниббл x в битовую позицию bit_pos, все прочие биты - 0."""
    r0 = ((x >> 0) & 1) << bit_pos
    r1 = ((x >> 1) & 1) << bit_pos
    r2 = ((x >> 2) & 1) << bit_pos
    r3 = ((x >> 3) & 1) << bit_pos
    o = func(r0, r1, r2, r3, 0)   # r4 = 0 безопасно: все S-боксы пишут в r4 до чтения
    return o


def test_sbox_table(num):
    func, perm = SBOX_FUNCS[num]
    table = SBOX_TABLES[num]
    for x in range(16):
        o = _run_sbox_bitslice(func, x, bit_pos=0)
        y = 0
        for k in range(4):
            y |= ((o[perm[k]] >> 0) & 1) << k
        assert y == table[x], (
            f"S{num}: вход {x:2d} → ожидалось {table[x]:2d}, получено {y:2d}"
        )
    print(f"S{num}: OK (16/16 входов)")

def test_sbox_other_bit_positions(num):
    """Bitslice-схема из ^ & | ~ не зависит от позиции бита -
    проверяем на бите 7 и 31, чтобы отловить случайный shift/rotate."""
    func, perm = SBOX_FUNCS[num]
    table = SBOX_TABLES[num]
    for bit in (7, 31):
        for x in range(16):
            o = _run_sbox_bitslice(func, x, bit_pos=bit)
            y = 0
            for k in range(4):
                y |= ((o[perm[k]] >> bit) & 1) << k
            assert y == table[x], (
                f"S{num} bit {bit}: вход {x} → ожидалось {table[x]}, получено {y}"
            )
    print(f"S{num}: OK на битах 7 и 31")


# ~~~ Основной привод ~~~

C_WUP  = 0x9E3779B9


def _rotl11(v: int) -> int:
    # ROTL(tt, 11) - сдвиг на константу 11, отдельная функция для читаемости
    return ((v << 11) | (v >> 21)) & 0xFFFFFFFF

def _wup(w: list, idx: int, i5: int, i3: int, i1: int, cc: int):
    # tt = w[idx] ^ w[i5] ^ w[i3] ^ w[i1] ^ (0x9E3779B9 ^ cc)
    # w[idx] = ROTL(tt, 11)
    tt = (w[idx] ^ w[i5] ^ w[i3] ^ w[i1] ^ (C_WUP ^ (cc & 0xFFFFFFFF))) & 0xFFFFFFFF
    w[idx] = _rotl11(tt)

def _wup0(w: list, cc: int):
    # WUP0 обновляет w0..w3, СТРОГО последовательно:
    # w1 использует уже обновлённый w0; w3 - обновлённые w0 и w2
    _wup(w, 0, 3, 5, 7, cc)
    _wup(w, 1, 4, 6, 0, cc + 1)
    _wup(w, 2, 5, 7, 1, cc + 2)
    _wup(w, 3, 6, 0, 2, cc + 3)

def _wup1(w: list, cc: int):
    # WUP1 обновляет w4..w7, тоже последовательно
    _wup(w, 4, 7, 1, 3, cc)
    _wup(w, 5, 0, 2, 4, cc + 1)
    _wup(w, 6, 1, 3, 5, cc + 2)
    _wup(w, 7, 2, 4, 6, cc + 3)

def _sks(sbox_fn, w, in_idx, out_idx, sk, i):
    out = sbox_fn(w[in_idx[0]], w[in_idx[1]], w[in_idx[2]], w[in_idx[3]], 0)
    sk[i]     = out[out_idx[0]]
    sk[i + 1] = out[out_idx[1]]
    sk[i + 2] = out[out_idx[2]]
    sk[i + 3] = out[out_idx[3]]


# Циклическая последовательность из 8 шагов; повторяется 3 раза + последний SKS3
# Формат: (sbox_fn, in_idx, out_idx)
#   in_idx  = (o0, o1, o2, o3) из SKS*
#   out_idx = (d0, d1, d2, d3) из SKS*
_SKS_CYCLE = (
    (_S3, (0, 1, 2, 3), (1, 2, 3, 4)),  # SKS3
    (_S2, (4, 5, 6, 7), (2, 3, 1, 4)),  # SKS2
    (_S1, (0, 1, 2, 3), (2, 0, 3, 1)),  # SKS1
    (_S0, (4, 5, 6, 7), (1, 4, 2, 0)),  # SKS0
    (_S7, (0, 1, 2, 3), (4, 3, 1, 0)),  # SKS7
    (_S6, (4, 5, 6, 7), (0, 1, 4, 2)),  # SKS6
    (_S5, (0, 1, 2, 3), (1, 3, 0, 2)),  # SKS5
    (_S4, (4, 5, 6, 7), (1, 4, 0, 3)),  # SKS4
)

def sosemanuk_schedule(kc: SosemanukKeyContext, key: bytes):
    """
    Serpent24 key schedule для Sosemanuk.
    Заполняет kc.sk[0..99].

    key: bytes длиной 1..32.
    """
    key_len = len(key)
    if key_len == 0 or key_len > 32:
        raise ValueError("invalid key size: %d" % key_len)

    # pad to 256 bits per Serpent spec
    wbuf = bytearray(32)
    wbuf[:key_len] = key
    if key_len < 32:
        wbuf[key_len] = 0x01
        # остальное уже 0

    if SOSEMANUK_VECTOR:
        DTV_print("key = " + key.hex().upper())

    # decode32le - int.from_bytes(..., "little")
    w0 = int.from_bytes(wbuf[0:4],   "little")
    w1 = int.from_bytes(wbuf[4:8],   "little")
    w2 = int.from_bytes(wbuf[8:12],  "little")
    w3 = int.from_bytes(wbuf[12:16], "little")
    w4 = int.from_bytes(wbuf[16:20], "little")
    w5 = int.from_bytes(wbuf[20:24], "little")
    w6 = int.from_bytes(wbuf[24:28], "little")
    w7 = int.from_bytes(wbuf[28:32], "little")

    if SOSEMANUK_VECTOR:
        DTV_print("  -> %08X %08X %08X %08X %08X %08X %08X %08X" % (
                  w7, w6, w5, w4, w3, w2, w1, w0))

    # В C w0..w7 - отдельные регистры. В питоне удобнее список,
    # но семантика та же (передаётся по ссылке в _wup*).
    w = [w0, w1, w2, w3, w4, w5, w6, w7]

    sk = kc.sk
    i = 0
    for step in range(25):
        cc = step * 4
        if step % 2 == 0:
            _wup0(w, cc)      # WUP0(cc)  для cc = 0, 8, 16, ...
        else:
            _wup1(w, cc)      # WUP1(cc)  для cc = 4, 12, 20, ...
        sbox_fn, in_idx, out_idx = _SKS_CYCLE[step % 8]
        _sks(sbox_fn, w, in_idx, out_idx, sk, i)
        i += 4

    if SOSEMANUK_VECTOR:
        for u in range(0, 100, 4):
            DTV_print("Serpent24 subkey %2u: %08X %08X %08X %08X" % (
                      u // 4,
                      sk[u + 3], sk[u + 2], sk[u + 1], sk[u + 0]))


def _serpent_lt(x0, x1, x2, x3):
    """Linear transform Serpent (bitslice)."""
    x0 = _rotl(x0, 13)
    x2 = _rotl(x2, 3)
    x1 = (x1 ^ x0 ^ x2) & 0xFFFFFFFF
    x3 = (x3 ^ x2 ^ ((x0 << 3) & 0xFFFFFFFF)) & 0xFFFFFFFF
    x1 = _rotl(x1, 1)
    x3 = _rotl(x3, 7)
    x0 = (x0 ^ x1 ^ x3) & 0xFFFFFFFF
    x2 = (x2 ^ x3 ^ ((x1 << 7) & 0xFFFFFFFF)) & 0xFFFFFFFF
    x0 = _rotl(x0, 5)
    x2 = _rotl(x2, 22)
    return x0, x1, x2, x3

def sosemanuk_init(rc: SosemanukRunContext, kc: SosemanukKeyContext, iv: bytes):
    """
    Serpent24 encrypt-mode над IV + построение начального состояния LFSR/FSM.
    iv: 1..16 байт (короткий — добивается нулями до 16).
    """
    iv_len = len(iv)
    if iv_len >= 16:
        ivtmp = bytes(iv[:16])
    else:
        ivtmp = bytes(iv) + b"\x00" * (16 - iv_len)

    if SOSEMANUK_VECTOR:
        DTV_print("IV = " + ivtmp.hex().upper())

    # decode32le четыре слова
    r = [
        int.from_bytes(ivtmp[0:4],  "little"),   # r0
        int.from_bytes(ivtmp[4:8],  "little"),   # r1
        int.from_bytes(ivtmp[8:12], "little"),   # r2
        int.from_bytes(ivtmp[12:16],"little"),   # r3
        0,                                       # r4 — scratch, значение неважно
    ]

    if SOSEMANUK_VECTOR:
        DTV_print("  -> %08X %08X %08X %08X" % (r[3], r[2], r[1], r[0]))

    sk = kc.sk

    # FSS: KA -> S-box -> LT
    def fss(zc, sbox, i0, i1, i2, i3, i4, o0, o1, o2, o3):
        r[i0] ^= sk[zc]
        r[i1] ^= sk[zc + 1]
        r[i2] ^= sk[zc + 2]
        r[i3] ^= sk[zc + 3]
        r[i0], r[i1], r[i2], r[i3], r[i4] = sbox(r[i0], r[i1], r[i2], r[i3], r[i4])
        r[o0], r[o1], r[o2], r[o3] = _serpent_lt(r[o0], r[o1], r[o2], r[o3])

    # FSF: KA -> S-box -> LT -> KA (финальный Serpent24 раунд)
    def fsf(zc, sbox, i0, i1, i2, i3, i4, o0, o1, o2, o3):
        r[i0] ^= sk[zc]
        r[i1] ^= sk[zc + 1]
        r[i2] ^= sk[zc + 2]
        r[i3] ^= sk[zc + 3]
        r[i0], r[i1], r[i2], r[i3], r[i4] = sbox(r[i0], r[i1], r[i2], r[i3], r[i4])
        r[o0], r[o1], r[o2], r[o3] = _serpent_lt(r[o0], r[o1], r[o2], r[o3])
        r[o0] ^= sk[zc + 4]
        r[o1] ^= sk[zc + 5]
        r[o2] ^= sk[zc + 6]
        r[o3] ^= sk[zc + 7]

    # --- Раунды 0..11, затем извлекаем s06..s09 ---
    fss( 0, _S0, 0, 1, 2, 3, 4, 1, 4, 2, 0)
    fss( 4, _S1, 1, 4, 2, 0, 3, 2, 1, 0, 4)
    fss( 8, _S2, 2, 1, 0, 4, 3, 0, 4, 1, 3)
    fss(12, _S3, 0, 4, 1, 3, 2, 4, 1, 3, 2)
    fss(16, _S4, 4, 1, 3, 2, 0, 1, 0, 4, 2)
    fss(20, _S5, 1, 0, 4, 2, 3, 0, 2, 1, 4)
    fss(24, _S6, 0, 2, 1, 4, 3, 0, 2, 3, 1)
    fss(28, _S7, 0, 2, 3, 1, 4, 4, 1, 2, 0)
    fss(32, _S0, 4, 1, 2, 0, 3, 1, 3, 2, 4)
    fss(36, _S1, 1, 3, 2, 4, 0, 2, 1, 4, 3)
    fss(40, _S2, 2, 1, 4, 3, 0, 4, 3, 1, 0)
    fss(44, _S3, 4, 3, 1, 0, 2, 3, 1, 0, 2)
    rc.s[9] = r[3]
    rc.s[8] = r[1]
    rc.s[7] = r[0]
    rc.s[6] = r[2]

    # --- Раунды 12..17, затем извлекаем r1, r2, s04, s05 ---
    fss(48, _S4, 3, 1, 0, 2, 4, 1, 4, 3, 2)
    fss(52, _S5, 1, 4, 3, 2, 0, 4, 2, 1, 3)
    fss(56, _S6, 4, 2, 1, 3, 0, 4, 2, 0, 1)
    fss(60, _S7, 4, 2, 0, 1, 3, 3, 1, 2, 4)
    fss(64, _S0, 3, 1, 2, 4, 0, 1, 0, 2, 3)
    fss(68, _S1, 1, 0, 2, 3, 4, 2, 1, 3, 0)
    rc.r1  = r[2]
    rc.s[4] = r[1]
    rc.r2  = r[3]
    rc.s[5] = r[0]

    # --- Раунды 18..23 (последний — FSF), затем извлекаем s00..s03 ---
    fss(72, _S2, 2, 1, 3, 0, 4, 3, 0, 1, 4)
    fss(76, _S3, 3, 0, 1, 4, 2, 0, 1, 4, 2)
    fss(80, _S4, 0, 1, 4, 2, 3, 1, 3, 0, 2)
    fss(84, _S5, 1, 3, 0, 2, 4, 3, 2, 1, 0)
    fss(88, _S6, 3, 2, 1, 0, 4, 3, 2, 4, 1)
    fsf(92, _S7, 3, 2, 4, 1, 0, 0, 1, 2, 3)
    rc.s[3] = r[0]
    rc.s[2] = r[1]
    rc.s[1] = r[2]
    rc.s[0] = r[3]

    if SOSEMANUK_VECTOR:
        DTV_print(
            "Initial LFSR state:\n"
            "      s1  = %08X\n"
            "      s2  = %08X\n"
            "      s3  = %08X\n"
            "      s4  = %08X\n"
            "      s5  = %08X\n"
            "      s6  = %08X\n"
            "      s7  = %08X\n"
            "      s8  = %08X\n"
            "      s9  = %08X\n"
            "      s10 = %08X\n"
            "Initial FSM state:  r1 = %08X   r2 = %08X"
            % (
                rc.s[0], rc.s[1], rc.s[2], rc.s[3], rc.s[4],
                rc.s[5], rc.s[6], rc.s[7], rc.s[8], rc.s[9],
                rc.r1, rc.r2,
            )
        )

    rc.ptr = 80   # sizeof rc->buf — буфер "пуст", следующий prng заполнит


MUL_A_TABLE = (
	0x00000000, 0xE19FCF13, 0x6B973726, 0x8A08F835,
	0xD6876E4C, 0x3718A15F, 0xBD10596A, 0x5C8F9679,
	0x05A7DC98, 0xE438138B, 0x6E30EBBE, 0x8FAF24AD,
	0xD320B2D4, 0x32BF7DC7, 0xB8B785F2, 0x59284AE1,
	0x0AE71199, 0xEB78DE8A, 0x617026BF, 0x80EFE9AC,
	0xDC607FD5, 0x3DFFB0C6, 0xB7F748F3, 0x566887E0,
	0x0F40CD01, 0xEEDF0212, 0x64D7FA27, 0x85483534,
	0xD9C7A34D, 0x38586C5E, 0xB250946B, 0x53CF5B78,
	0x1467229B, 0xF5F8ED88, 0x7FF015BD, 0x9E6FDAAE,
	0xC2E04CD7, 0x237F83C4, 0xA9777BF1, 0x48E8B4E2,
	0x11C0FE03, 0xF05F3110, 0x7A57C925, 0x9BC80636,
	0xC747904F, 0x26D85F5C, 0xACD0A769, 0x4D4F687A,
	0x1E803302, 0xFF1FFC11, 0x75170424, 0x9488CB37,
	0xC8075D4E, 0x2998925D, 0xA3906A68, 0x420FA57B,
	0x1B27EF9A, 0xFAB82089, 0x70B0D8BC, 0x912F17AF,
	0xCDA081D6, 0x2C3F4EC5, 0xA637B6F0, 0x47A879E3,
	0x28CE449F, 0xC9518B8C, 0x435973B9, 0xA2C6BCAA,
	0xFE492AD3, 0x1FD6E5C0, 0x95DE1DF5, 0x7441D2E6,
	0x2D699807, 0xCCF65714, 0x46FEAF21, 0xA7616032,
	0xFBEEF64B, 0x1A713958, 0x9079C16D, 0x71E60E7E,
	0x22295506, 0xC3B69A15, 0x49BE6220, 0xA821AD33,
	0xF4AE3B4A, 0x1531F459, 0x9F390C6C, 0x7EA6C37F,
	0x278E899E, 0xC611468D, 0x4C19BEB8, 0xAD8671AB,
	0xF109E7D2, 0x109628C1, 0x9A9ED0F4, 0x7B011FE7,
	0x3CA96604, 0xDD36A917, 0x573E5122, 0xB6A19E31,
	0xEA2E0848, 0x0BB1C75B, 0x81B93F6E, 0x6026F07D,
	0x390EBA9C, 0xD891758F, 0x52998DBA, 0xB30642A9,
	0xEF89D4D0, 0x0E161BC3, 0x841EE3F6, 0x65812CE5,
	0x364E779D, 0xD7D1B88E, 0x5DD940BB, 0xBC468FA8,
	0xE0C919D1, 0x0156D6C2, 0x8B5E2EF7, 0x6AC1E1E4,
	0x33E9AB05, 0xD2766416, 0x587E9C23, 0xB9E15330,
	0xE56EC549, 0x04F10A5A, 0x8EF9F26F, 0x6F663D7C,
	0x50358897, 0xB1AA4784, 0x3BA2BFB1, 0xDA3D70A2,
	0x86B2E6DB, 0x672D29C8, 0xED25D1FD, 0x0CBA1EEE,
	0x5592540F, 0xB40D9B1C, 0x3E056329, 0xDF9AAC3A,
	0x83153A43, 0x628AF550, 0xE8820D65, 0x091DC276,
	0x5AD2990E, 0xBB4D561D, 0x3145AE28, 0xD0DA613B,
	0x8C55F742, 0x6DCA3851, 0xE7C2C064, 0x065D0F77,
	0x5F754596, 0xBEEA8A85, 0x34E272B0, 0xD57DBDA3,
	0x89F22BDA, 0x686DE4C9, 0xE2651CFC, 0x03FAD3EF,
	0x4452AA0C, 0xA5CD651F, 0x2FC59D2A, 0xCE5A5239,
	0x92D5C440, 0x734A0B53, 0xF942F366, 0x18DD3C75,
	0x41F57694, 0xA06AB987, 0x2A6241B2, 0xCBFD8EA1,
	0x977218D8, 0x76EDD7CB, 0xFCE52FFE, 0x1D7AE0ED,
	0x4EB5BB95, 0xAF2A7486, 0x25228CB3, 0xC4BD43A0,
	0x9832D5D9, 0x79AD1ACA, 0xF3A5E2FF, 0x123A2DEC,
	0x4B12670D, 0xAA8DA81E, 0x2085502B, 0xC11A9F38,
	0x9D950941, 0x7C0AC652, 0xF6023E67, 0x179DF174,
	0x78FBCC08, 0x9964031B, 0x136CFB2E, 0xF2F3343D,
	0xAE7CA244, 0x4FE36D57, 0xC5EB9562, 0x24745A71,
	0x7D5C1090, 0x9CC3DF83, 0x16CB27B6, 0xF754E8A5,
	0xABDB7EDC, 0x4A44B1CF, 0xC04C49FA, 0x21D386E9,
	0x721CDD91, 0x93831282, 0x198BEAB7, 0xF81425A4,
	0xA49BB3DD, 0x45047CCE, 0xCF0C84FB, 0x2E934BE8,
	0x77BB0109, 0x9624CE1A, 0x1C2C362F, 0xFDB3F93C,
	0xA13C6F45, 0x40A3A056, 0xCAAB5863, 0x2B349770,
	0x6C9CEE93, 0x8D032180, 0x070BD9B5, 0xE69416A6,
	0xBA1B80DF, 0x5B844FCC, 0xD18CB7F9, 0x301378EA,
	0x693B320B, 0x88A4FD18, 0x02AC052D, 0xE333CA3E,
	0xBFBC5C47, 0x5E239354, 0xD42B6B61, 0x35B4A472,
	0x667BFF0A, 0x87E43019, 0x0DECC82C, 0xEC73073F,
	0xB0FC9146, 0x51635E55, 0xDB6BA660, 0x3AF46973,
	0x63DC2392, 0x8243EC81, 0x084B14B4, 0xE9D4DBA7,
	0xB55B4DDE, 0x54C482CD, 0xDECC7AF8, 0x3F53B5EB,
)
MUL_IA_TABLE = (
	0x00000000, 0x180F40CD, 0x301E8033, 0x2811C0FE,
	0x603CA966, 0x7833E9AB, 0x50222955, 0x482D6998,
	0xC078FBCC, 0xD877BB01, 0xF0667BFF, 0xE8693B32,
	0xA04452AA, 0xB84B1267, 0x905AD299, 0x88559254,
	0x29F05F31, 0x31FF1FFC, 0x19EEDF02, 0x01E19FCF,
	0x49CCF657, 0x51C3B69A, 0x79D27664, 0x61DD36A9,
	0xE988A4FD, 0xF187E430, 0xD99624CE, 0xC1996403,
	0x89B40D9B, 0x91BB4D56, 0xB9AA8DA8, 0xA1A5CD65,
	0x5249BE62, 0x4A46FEAF, 0x62573E51, 0x7A587E9C,
	0x32751704, 0x2A7A57C9, 0x026B9737, 0x1A64D7FA,
	0x923145AE, 0x8A3E0563, 0xA22FC59D, 0xBA208550,
	0xF20DECC8, 0xEA02AC05, 0xC2136CFB, 0xDA1C2C36,
	0x7BB9E153, 0x63B6A19E, 0x4BA76160, 0x53A821AD,
	0x1B854835, 0x038A08F8, 0x2B9BC806, 0x339488CB,
	0xBBC11A9F, 0xA3CE5A52, 0x8BDF9AAC, 0x93D0DA61,
	0xDBFDB3F9, 0xC3F2F334, 0xEBE333CA, 0xF3EC7307,
	0xA492D5C4, 0xBC9D9509, 0x948C55F7, 0x8C83153A,
	0xC4AE7CA2, 0xDCA13C6F, 0xF4B0FC91, 0xECBFBC5C,
	0x64EA2E08, 0x7CE56EC5, 0x54F4AE3B, 0x4CFBEEF6,
	0x04D6876E, 0x1CD9C7A3, 0x34C8075D, 0x2CC74790,
	0x8D628AF5, 0x956DCA38, 0xBD7C0AC6, 0xA5734A0B,
	0xED5E2393, 0xF551635E, 0xDD40A3A0, 0xC54FE36D,
	0x4D1A7139, 0x551531F4, 0x7D04F10A, 0x650BB1C7,
	0x2D26D85F, 0x35299892, 0x1D38586C, 0x053718A1,
	0xF6DB6BA6, 0xEED42B6B, 0xC6C5EB95, 0xDECAAB58,
	0x96E7C2C0, 0x8EE8820D, 0xA6F942F3, 0xBEF6023E,
	0x36A3906A, 0x2EACD0A7, 0x06BD1059, 0x1EB25094,
	0x569F390C, 0x4E9079C1, 0x6681B93F, 0x7E8EF9F2,
	0xDF2B3497, 0xC724745A, 0xEF35B4A4, 0xF73AF469,
	0xBF179DF1, 0xA718DD3C, 0x8F091DC2, 0x97065D0F,
	0x1F53CF5B, 0x075C8F96, 0x2F4D4F68, 0x37420FA5,
	0x7F6F663D, 0x676026F0, 0x4F71E60E, 0x577EA6C3,
	0xE18D0321, 0xF98243EC, 0xD1938312, 0xC99CC3DF,
	0x81B1AA47, 0x99BEEA8A, 0xB1AF2A74, 0xA9A06AB9,
	0x21F5F8ED, 0x39FAB820, 0x11EB78DE, 0x09E43813,
	0x41C9518B, 0x59C61146, 0x71D7D1B8, 0x69D89175,
	0xC87D5C10, 0xD0721CDD, 0xF863DC23, 0xE06C9CEE,
	0xA841F576, 0xB04EB5BB, 0x985F7545, 0x80503588,
	0x0805A7DC, 0x100AE711, 0x381B27EF, 0x20146722,
	0x68390EBA, 0x70364E77, 0x58278E89, 0x4028CE44,
	0xB3C4BD43, 0xABCBFD8E, 0x83DA3D70, 0x9BD57DBD,
	0xD3F81425, 0xCBF754E8, 0xE3E69416, 0xFBE9D4DB,
	0x73BC468F, 0x6BB30642, 0x43A2C6BC, 0x5BAD8671,
	0x1380EFE9, 0x0B8FAF24, 0x239E6FDA, 0x3B912F17,
	0x9A34E272, 0x823BA2BF, 0xAA2A6241, 0xB225228C,
	0xFA084B14, 0xE2070BD9, 0xCA16CB27, 0xD2198BEA,
	0x5A4C19BE, 0x42435973, 0x6A52998D, 0x725DD940,
	0x3A70B0D8, 0x227FF015, 0x0A6E30EB, 0x12617026,
	0x451FD6E5, 0x5D109628, 0x750156D6, 0x6D0E161B,
	0x25237F83, 0x3D2C3F4E, 0x153DFFB0, 0x0D32BF7D,
	0x85672D29, 0x9D686DE4, 0xB579AD1A, 0xAD76EDD7,
	0xE55B844F, 0xFD54C482, 0xD545047C, 0xCD4A44B1,
	0x6CEF89D4, 0x74E0C919, 0x5CF109E7, 0x44FE492A,
	0x0CD320B2, 0x14DC607F, 0x3CCDA081, 0x24C2E04C,
	0xAC977218, 0xB49832D5, 0x9C89F22B, 0x8486B2E6,
	0xCCABDB7E, 0xD4A49BB3, 0xFCB55B4D, 0xE4BA1B80,
	0x17566887, 0x0F59284A, 0x2748E8B4, 0x3F47A879,
	0x776AC1E1, 0x6F65812C, 0x477441D2, 0x5F7B011F,
	0xD72E934B, 0xCF21D386, 0xE7301378, 0xFF3F53B5,
	0xB7123A2D, 0xAF1D7AE0, 0x870CBA1E, 0x9F03FAD3,
	0x3EA637B6, 0x26A9777B, 0x0EB8B785, 0x16B7F748,
	0x5E9A9ED0, 0x4695DE1D, 0x6E841EE3, 0x768B5E2E,
	0xFEDECC7A, 0xE6D18CB7, 0xCEC04C49, 0xD6CF0C84,
	0x9EE2651C, 0x86ED25D1, 0xAEFCE52F, 0xB6F3A5E2,
)

def _mul_a(x: int):
    return ((x << 8) & 0xFFFFFFFF) ^ MUL_A_TABLE[x >> 24]

def _mul_g(x: int):
    return (x >> 8) ^ MUL_IA_TABLE[x & 0xFF]

def _step(s: list[int], base: int, r1: int, r2: int):
    """Один STEP. s — список из 10 LFSR-слов, base — индекс s_t.
    Возвращает (dd, ee, r1, r2); s[base] обновляется in-place."""
    x1 = (base + 1) % 10
    x2 = (base + 2) % 10
    x3 = (base + 3) % 10
    x4 = (base + 4) % 10
    x5 = (base + 5) % 10
    x6 = (base + 6) % 10
    x7 = (base + 7) % 10
    x8 = (base + 8) % 10
    x9 = (base + 9) % 10

    # --- FSM (Trans инлайн) ---
    s_x1 = s[x1]
    s_x8 = s[x8]
    tt = (s_x1 ^ s_x8) if (r1 & 1) else s_x1
    or1 = r1
    r1 = (r2 + tt) & 0xFFFFFFFF
    tt = (or1 * 0x54655307) & 0xFFFFFFFF
    r2 = ((tt << 7) | (tt >> 25)) & 0xFFFFFFFF
    if SOSEMANUK_VECTOR:
        DTV_print("New FSM state:  r1 = %08X   r2 = %08X" % (r1, r2))

    # --- LRU (сдвиг LFSR) ---
    dd   = s[base]
    s_x9 = s[x9]
    s[base] = (_mul_a(dd) ^ _mul_g(s[x3]) ^ s_x9) & 0xFFFFFFFF
    if SOSEMANUK_VECTOR:
        DTV_print(
            "New LFSR state:\n"
            "   dropped (s_t): %08X\n"
            "         s_t+1  = %08X\n"
            "         s_t+2  = %08X\n"
            "         s_t+3  = %08X\n"
            "         s_t+4  = %08X\n"
            "         s_t+5  = %08X\n"
            "         s_t+6  = %08X\n"
            "         s_t+7  = %08X\n"
            "         s_t+8  = %08X\n"
            "         s_t+9  = %08X\n"
            "         s_t+10 = %08X"
            % (dd, s[x1], s[x2], s[x3], s[x4], s[x5],
                  s[x6], s[x7], s[x8], s[x9], s[base]))

    # --- CC1 ---
    ee = ((s_x9 + r1) & 0xFFFFFFFF) ^ r2
    if SOSEMANUK_VECTOR:
        DTV_print("Intermediate output: %08X" % ee)

    return dd, ee, r1, r2

def _srd(s: list[int], base: int, r1: int, r2: int, out_buf: bytearray, ooff: int):
    v = [0, 0, 0, 0]
    u = [0, 0, 0, 0]
    for k in range(4):
        v[k], u[k], r1, r2 = _step(s, (base + k) % 10, r1, r2)

    if SOSEMANUK_VECTOR:
        DTV_print("Serpent1 input:  %08X %08X %08X %08X"
                  % (u[3], u[2], u[1], u[0]))

    u = list(_S2(u[0], u[1], u[2], u[3], 0))

    if SOSEMANUK_VECTOR:
        # PSPOUT получает u2, u3, u1, u4 и печатает их в порядке u4 u1 u3 u2
        DTV_print("Serpent1 output: %08X %08X %08X %08X"
                  % (u[4], u[1], u[3], u[2]))

    w0 = (u[2] ^ v[0]) & 0xFFFFFFFF
    w1 = (u[3] ^ v[1]) & 0xFFFFFFFF
    w2 = (u[1] ^ v[2]) & 0xFFFFFFFF
    w3 = (u[4] ^ v[3]) & 0xFFFFFFFF

    out_buf[ooff + 0 :ooff + 4]  = w0.to_bytes(4, "little")
    out_buf[ooff + 4 :ooff + 8]  = w1.to_bytes(4, "little")
    out_buf[ooff + 8 :ooff + 12] = w2.to_bytes(4, "little")
    out_buf[ooff + 12:ooff + 16] = w3.to_bytes(4, "little")

    if SOSEMANUK_VECTOR:
        DTV_print("Stream output: " + out_buf[ooff:ooff + 16].hex().upper())

    return r1, r2


def _sosemanuk_internal(rc: SosemanukRunContext):
    """Один блок keystream — 80 байт в rc.buf."""
    s = rc.s
    r1, r2 = rc.r1, rc.r2
    for block in range(5):
        base = (block * 4) % 10
        r1, r2 = _srd(s, base, r1, r2, rc.buf, block * 16)
    rc.r1 = r1
    rc.r2 = r2


def sosemanuk_prng(rc: SosemanukRunContext, out_len: int):
    out = bytearray(out_len)
    pos = 0
    while pos < out_len:
        if rc.ptr >= 80:
            _sosemanuk_internal(rc)
            rc.ptr = 0
        n = min(80 - rc.ptr, out_len - pos)
        out[pos:pos + n] = rc.buf[rc.ptr:rc.ptr + n]
        rc.ptr += n
        pos += n
    return bytes(out)

def short_repr(data: bytes):
    out = repr(data.decode("utf-8", errors="replace"))
    if len(out) > 128:
        return f"{out[:64]} ... {out[-64:]}"
    return out
def sosemanuk_encrypt(rc: SosemanukRunContext, data: bytes):
    ks = sosemanuk_prng(rc, len(data))
    xored = bytes(a ^ b for a, b in zip(data, ks))
    print("Вход:", short_repr(data))
    print("Выход:", short_repr(xored))
    return xored


# ~~~ точка входа ~~~

def _hex_dump(data: bytes) -> str:
    """Формат C-референса: 16 байт/строка, uppercase, через пробел, с ведущим пробелом."""
    return "\n".join(
        " " + " ".join("%02X" % b for b in data[i:i + 16])
        for i in range(0, len(data), 16)
    )

def trace_vector(num, key_hex, iv_hex, out_len=160):
    if SOSEMANUK_VECTOR:
        DTV_print("=====================================================")
        DTV_print("Detailed test vector %d:" % num)
    kc = SosemanukKeyContext()
    sosemanuk_schedule(kc, bytes.fromhex(key_hex))
    rc = SosemanukRunContext()
    sosemanuk_init(rc, kc, bytes.fromhex(iv_hex))
    ks = sosemanuk_prng(rc, out_len)
    if SOSEMANUK_VECTOR:
        DTV_print(f"\nTotal output:\n{_hex_dump(ks)}\n")


if __name__ == "__main__":
    for i in range(8):
        test_sbox_table(i)
    for i in range(8):
        test_sbox_other_bit_positions(i)

    SOSEMANUK_VECTOR = True
    trace_vector(1, "A7C083FEB7", "00112233445566778899AABBCCDDEEFF")
    trace_vector(2, "00112233445566778899AABBCCDDEEFF", "8899AABBCCDDEEFF0011223344556677")
    print("DTV-digest:", DTV_digest.hexdigest())
    assert DTV_digest.hexdigest() == "7ad601eb1cc6b60e0c8591655ec3bc2b00c05bfce73e122ebca3b39f105974ea"
