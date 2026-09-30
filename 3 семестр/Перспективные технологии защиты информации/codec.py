from struct import pack, unpack, calcsize
from functools import cache
from io import BytesIO


# Заглушки, чисто ради целостности картины :)
# Выдрал всё это API из собственного jni_rpc клиента,
# там эти типы как раз и нужны в полном объёме

class jobject: pass
class jstring(jobject): pass
class jarray(jobject): pass
class jclass(jobject): pass

jvalue = bool | int | float | jobject


def read_byte(read, /) -> int:
    try: return read(1)[0]
    except Exception:
        raise EOFError("Unexpected end of stream") from None

def read_int(read, /) -> int:
    try: return unpack("=i", read(4))[0]
    except Exception:
        raise EOFError("Unexpected end of stream") from None

ptr_size = calcsize('P')
def read_ptr(read, /) -> int:
    try: return unpack('P', read(ptr_size))[0]
    except Exception as e:
        raise EOFError("Unexpected end of stream") from None

def read_uleb128(read, /) -> int:
    result = shift = 0
    while True:
        try: byte = read(1)[0]
        except Exception:
            raise EOFError("Unexpected end of stream") from None
        result |= (byte & 0x7f) << shift
        if not (byte & 0x80):
            break
        shift += 7
    return result

def read_sleb128(read, /) -> int:
    u = read_uleb128(read)
    return (u >> 1) ^ -(u & 1)

def read_str(read, bin=False, /) -> str:
    size = read_uleb128(read)
    data = read(size)
    if len(data) != size:
        raise EOFError("Unexpected end of stream") from None
    # сервер (utf16_to_utf8) гарантирует корректность кодировки
    return data if bin else data.decode("utf-8")

def read_bigint(read, /, signed=False) -> int:
    data = read_str(read, True)
    return int.from_bytes(data, "big", signed=signed)

result_dispatch = (
    lambda jni, /: jobject(jni, read_ptr(jni._read)),
    lambda jni, /: jstring(jni, read_ptr(jni._read)),
    lambda jni, /: jarray(jni, read_ptr(jni._read)),
    lambda jni, /: jclass(jni, None, read_ptr(jni._read)),
    lambda read, /: bool(read(1)[0]),  # boolean
    lambda read, /: read(1)[0],  # byte
    lambda read, /: chr(read_uleb128(read)),  # char
    read_sleb128,  # short
    read_sleb128,  # int
    read_sleb128,  # long
    lambda read, /: unpack("=f", read(4))[0],  # float
    lambda read, /: unpack("=d", read(8))[0],  # double
    lambda read, /: None,  # void
)
def read_value(jni, kind: int, /) -> jvalue:
    if kind < 4:  # LRAK
        return result_dispatch[kind](jni)
    return result_dispatch[kind](jni._read)


int2byte = tuple(bytes((i,)) for i in range(256))
def write_byte(write, val: int, /) -> None:
    write(int2byte[val])

def write_int(write, val: int, /) -> None:
    write(pack("=i", val))

def write_ptr(write, val: int, /) -> None:
    write(pack('P', val))

def write_uleb128(write, val: int, /) -> None:
    if val < 0:
        raise ValueError(f"negative value for write_uleb128: {val}")
    if val < 0x80:
        write(int2byte[val])
        return
    while val:
        byte = val & 0x7f
        val >>= 7
        write(int2byte[byte | 0x80 if val else byte])

def write_sleb128(write, val: int, /) -> None:
    u = ((val << 1) ^ (val >> 31)) & 0xffffffff
    write_uleb128(write, u)
    # -1 >> 7 = -1, по этому нужна неотрицательная маска

def write_sleb128L(write, val: int, /) -> None:
    u = ((val << 1) ^ (val >> 63)) & 0xffffffffffffffff
    write_uleb128(write, u)

def write_str(write, val: str, /) -> None:
    data = val.encode("utf-8")
    write_uleb128(write, len(data))
    write(data)

def write_str_bin(write, data: bytes, /) -> None:
    write_uleb128(write, len(data))
    write(data)

def write_bigint(write, val: int, /, signed=False) -> None:
    if val == 0:
        write_str_bin(write, b"")
        return
    if signed:
        # для отрицательных: ~val = -val-1, его bit_length = нужное
        nbits = val.bit_length() if val > 0 else (~val).bit_length()
        size = (nbits + 8) // 8
    else:
        size = (val.bit_length() + 7) // 8
    write_str_bin(write, val.to_bytes(size, "big", signed=signed))

value_dispatch = (
    lambda write, v, /: write(pack('P', v._o_inst)),  # jobject
    lambda write, v, /: write(pack('P', v._s_inst)),  # jstring
    lambda write, v, /: write(pack('P', v._a_inst)),  # jarray
    lambda write, v, /: write(pack('P', v._c_inst)),  # jclass
    lambda write, v, /: write(int2byte[bool(v)]),  # boolean
    lambda write, v, /: write(int2byte[int(v)]),  # byte
    lambda write, v, /: write_uleb128(write, ord(v)),  # char
    write_sleb128,  # short
    write_sleb128,  # int
    write_sleb128L,  # long
    lambda write, v, /: write(pack('=f', v)),  # float
    lambda write, v, /: write(pack('=d', v)),  # double
)
def write_value(write, val: jvalue, type: int, /):
    value_dispatch[type](write, val)

args_dispatch = [None] * 128  # ascii
args_dispatch[ord('Z')] = "write(int2byte[bool(args[{}])])"
args_dispatch[ord('B')] = "write(int2byte[int(args[{}])])"
args_dispatch[ord('C')] = "write_uleb128(write, ord(args[{}]))"
args_dispatch[ord('S')] = "write_sleb128(write, args[{}])"
args_dispatch[ord('I')] = "write_sleb128(write, args[{}])"
args_dispatch[ord('J')] = "write_sleb128L(write, args[{}])"
args_dispatch[ord('F')] = "write(pack('=f', args[{}]))"
args_dispatch[ord('D')] = "write(pack('=d', args[{}]))"

shorty2pack = [None] * 128  # ascii
shorty2pack[ord('Z')] = '?'
shorty2pack[ord('B')] = 'b'
shorty2pack[ord('F')] = 'f'
shorty2pack[ord('D')] = 'd'

shorty2attr = [None] * 128  # ascii
shorty2attr[ord('L')] = "_o_inst"
shorty2attr[ord('R')] = "_s_inst"
shorty2attr[ord('A')] = "_a_inst"
shorty2attr[ord('K')] = "_c_inst"
# jmethod -> _m_inst
# jfield -> _j_inst
# Нет конфликтов в защите указателей

# знаю про shorty ещё с сентября 2019 года, т.к. пилил весь месяц (свой отпуск) DexReader до финальной
# но shorty понадобился только сейчас: август 2026 года :)
@cache
def args_writer_gen(shorty):
    pos, L = 0, len(shorty)
    code = ["def func(write, args, /):"]
    add_line = code.append
    while pos < L:
        letter = shorty[pos]
        letter_c = ord(letter)
        next_ = pos + 1
        if letter in "LRAK":  # jobject | jstring | jarray | jclass
            while next_ < L and shorty[next_] in "LRAK":
                next_ += 1
            count = next_ - pos
            if count == 1:
                add_line(f"    write(pack('P', args[{pos}].{shorty2attr[letter_c]}))")
            else:
                args = [f"args[{i}].{shorty2attr[ord(shorty[i])]}" for i in range(pos, next_)]
                add_line(f"    write(pack({'P' * count !r}, {', '.join(args)}))")
            pos = next_
            continue
        c = shorty2pack[letter_c]
        packs = []
        if c is not None:
            packs.append(c)
            while next_ < L:
                c = shorty2pack[ord(shorty[next_])]
                if c is None:
                    break
                packs.append(c)
                next_ += 1
        if len(packs) > 1:
            add_line(f"    write(pack({'=' + ''.join(packs) !r}, *args[{pos if pos else ''}:{next_}]))")
        else:
            add_line("    " + args_dispatch[letter_c].format(pos))
        pos = next_
  # print('\n'.join(code))
    _G = {"int2byte": int2byte, "write_sleb128": write_sleb128,
          "write_uleb128": write_uleb128,
          "write_sleb128L": write_sleb128L, "pack": pack}
    exec('\n'.join(code), _G)
    return _G["func"]
# args_writer_gen("LLFLZLFDZBC")

def write_args(write, shorty: str, args: tuple[jvalue, ...], /):
    assert len(shorty) == len(args)
    if shorty:
        args_writer_gen(shorty)(write, args)


if __name__ == "__main__":
    for v in [0, 1, 127, 128, -1, -128, -129, 2**256, -(2**256)]:
        buf = BytesIO()
        write_bigint(buf.write, v, signed=True)
        buf.seek(0)
        readed_v = read_bigint(buf.read, signed=True)
        print(readed_v == v, buf.getvalue().hex(), readed_v, v)
