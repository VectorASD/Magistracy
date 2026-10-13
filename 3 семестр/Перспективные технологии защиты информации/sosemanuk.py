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
        self.s = [0] * 10  # LFSR
        self.r1 = 0        # FSM
        self.r2 = 0
        self.buf = b""     # байты keystream
        self.ptr = 0


# ~~~ Отладчик ~~~

from functools import cache

SOSEMANUK_VECTOR = True  # Просто debug-режим, должен выводить содержимое TEST_VECTOR_128.txt
@cache
def _dtv_fp():
    return open("MY_DETAILED_TEST_VECTOR.txt", "w")
def DTV_print(
    *values: object,
    sep: str | None = " ",
    end: str | None = "\n",
):
    if SOSEMANUK_VECTOR:
        print(*values, sep=sep, end=end)
        print(*values, sep=sep, end=end, file=_dtv_fp(), flush=True)


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

def _wup(w: list, idx: int, i5: int, i3: int, i1: int, cc: int) -> None:
    # tt = w[idx] ^ w[i5] ^ w[i3] ^ w[i1] ^ (0x9E3779B9 ^ cc)
    # w[idx] = ROTL(tt, 11)
    tt = (w[idx] ^ w[i5] ^ w[i3] ^ w[i1] ^ (C_WUP ^ (cc & 0xFFFFFFFF))) & 0xFFFFFFFF
    w[idx] = _rotl11(tt)

def _wup0(w: list, cc: int) -> None:
    # WUP0 обновляет w0..w3, СТРОГО последовательно:
    # w1 использует уже обновлённый w0; w3 - обновлённые w0 и w2
    _wup(w, 0, 3, 5, 7, cc)
    _wup(w, 1, 4, 6, 0, cc + 1)
    _wup(w, 2, 5, 7, 1, cc + 2)
    _wup(w, 3, 6, 0, 2, cc + 3)

def _wup1(w: list, cc: int) -> None:
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
_SKS_CYCLE = [
    (_S3, (0, 1, 2, 3), (1, 2, 3, 4)),  # SKS3
    (_S2, (4, 5, 6, 7), (2, 3, 1, 4)),  # SKS2
    (_S1, (0, 1, 2, 3), (2, 0, 3, 1)),  # SKS1
    (_S0, (4, 5, 6, 7), (1, 4, 2, 0)),  # SKS0
    (_S7, (0, 1, 2, 3), (4, 3, 1, 0)),  # SKS7
    (_S6, (4, 5, 6, 7), (0, 1, 4, 2)),  # SKS6
    (_S5, (0, 1, 2, 3), (1, 3, 0, 2)),  # SKS5
    (_S4, (4, 5, 6, 7), (1, 4, 0, 3)),  # SKS4
]

def sosemanuk_schedule(kc, key: bytes) -> None:
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


# ~~~ точка входа ~~~

def trace_vector(num, key_hex, iv_hex):
    if SOSEMANUK_VECTOR:
        DTV_print("=====================================================")
        DTV_print("Detailed test vector %d:" % num)
    kc = SosemanukKeyContext()
    sosemanuk_schedule(kc, bytes.fromhex(key_hex))


if __name__ == "__main__":
    for i in range(8):
        test_sbox_table(i)
    for i in range(8):
        test_sbox_other_bit_positions(i)
    trace_vector(1, "A7C083FEB7", "00112233445566778899AABBCCDDEEFF")
