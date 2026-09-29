from random import Random, SystemRandom
import re
import time

from primes import probable_prime, is_probable_prime, pow


LINE_SEPARATOR = f"\n{'~' * 100}\n"

def gen_safe_prime(bits_p: int, rnd) -> tuple[int, int]:
    """
    Генерирует safe prime p = 2q + 1, где p и q оба простые.
    bits_p — битовая длина p. q получается bit_length(p) - 1.
    """
    bits_q = bits_p - 1
    while True:
        q = probable_prime(bits_q, rnd)
        p = 2 * q + 1
        if p.bit_length() == bits_p and is_probable_prime(p, 100, rnd):
            return p, q

# q не обязательно делать простым, чтобы алгоритм вообще работал,
# но тогда мы раскроем путь целой серии атак:
#
# 1. Pohlig–Hellman.
#    Если p-1 разлагается на малые простые множители, задача
#    дискретного логарифма (DLP) сводится к DLP в подгруппах
#    малого порядка. Зная x mod r для каждого малого r | p-1,
#    атакующий собирает x через китайскую теорему об остатках.
#    Safe prime гарантирует, что единственный большой множитель
#    p-1 — это q, а второй — двойка. Мелочь не помогает взлому.
#
# 2. Small subgroup attack (атака малой подгруппой).
#    Атакующий подсовывает жертве открытый ключ Y, лежащий в
#    подгруппе малого порядка r | p-1 (например, порядка 2).
#    Жертва считает K = Y^x и как-то отвечает. По ответу атакующий
#    узнаёт x mod r. Перебирая разные малые подгруппы, он
#    восстанавливает x по битам.
#    Safe prime оставляет только подгруппы порядка 2 и q.
#    От подгруппы порядка 2 защищает проверка Y^q mod p == 1.
#    От порядка q защищаться не нужно — она большая.
#
# 3. Атака на структуру подгрупп в общем случае.
#    Именно малые подгруппы позволяют атакующему "прощупывать"
#    секрет по частям. Каждая подгруппа малого порядка r даёт
#    атакующему ровно один бит (или log2(r) бит) информации о x.
#    Safe prime закрывает этот канал: большая подгруппа q не
#    даёт пошаговой утечки, а подгруппа порядка 2 либо тривиальна,
#    либо отсекается проверкой.

def find_generator(p: int, rnd: Random) -> int:
    """
    Генератор ℤₚ* для safe prime p = 2q + 1.
    Проверяет g^2 ≠ 1 и g^q ≠ 1 — покрывает все делители p-1.
    """
    q = (p - 1) // 2
    while True:
        g = rnd.randrange(2, p - 1)   # [2, p-2]
        if pow(g, 2, p) != 1 and pow(g, q, p) != 1:
            return g

def gen_safe_params(bits_p: int, rnd: Random) -> tuple[int, int, int]:
    """p = 2q+1 (safe prime) + генератор g группы ℤₚ*."""
    p, q = gen_safe_prime(bits_p, rnd)
    g = find_generator(p, rnd)
    return p, q, g


def gen_subgroup_params(bits_p: int, bits_q: int, rnd: Random) -> tuple[int, int, int]:
    """
    p = t·q + 1, где p и q — простые.
    g = r^t mod p — генератор подгруппы порядка q.
    """
    bits_t = bits_p - bits_q
    q = probable_prime(bits_q, rnd)

    while True:
      # t = rnd.getrandbits(bits_t) | 1  баг: t должно быть всегда чётным
        t = (rnd.getrandbits(bits_t) | (1 << (bits_t - 1))) & ~1
        if t.bit_length() < bits_t:
            continue
        p = t * q + 1
        if p.bit_length() != bits_p:
            continue
        if is_probable_prime(p, 100, rnd):
            break

    while True:
        r = rnd.randrange(2, p - 1)
        g = pow(r, t, p)
        if g != 1:
            return p, q, g


def cdiv(num, div):
    return (num + div - 1) // div


# escape почти такой же, как в jpeg, чтобы 0 в данных не путать с терминатором:

_ESCAPE   = re.compile(rb'[\x00\xff]', re.DOTALL)
_BODY     = re.compile(rb'(?:\xff.|[^\x00])*', re.DOTALL)
_UNESCAPE = re.compile(rb'\xff(.)', re.DOTALL)

def message_to_int(msg: str) -> int:
    data = msg.encode('cp1251')
    stuffed = _ESCAPE.sub(lambda m: b'\xff' + m.group(), data)
    return int.from_bytes(stuffed, 'big')

def int_to_message(n: int) -> str:
    data = n.to_bytes(cdiv(n.bit_length(), 8) or 1, 'big')
    body = _BODY.match(data).group()
    return _UNESCAPE.sub(lambda m: m.group(1), body).decode('cp1251')

# ''.join(bytes((i,)).decode("cp1251") for i in range(256) if i != 0x98)
# Таблица допустимых символов windows-1251 (cp1251):
#
# \x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14
# \x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f !"#$%&\'()*+,-./0123456789:;<=>?@
# ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz
# {|}~\x7fЂЃ‚ѓ„…†‡€‰Љ‹ЊЌЋЏђ‘’“”•–—™љ›њќћџ\xa0ЎўЈ¤Ґ¦§Ё©Є«¬\xad®Ї°±Ііґµ¶·ё№є»јЅѕї
# АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдежзийклмнопрстуфхцчшщъыьэюя


def dh_demo(*, group_mode: bool):
    print(LINE_SEPARATOR)
    rnd = SystemRandom()

    print("Генерация параметров...")

    t0 = time.perf_counter()
    if group_mode:
        p, q, g = gen_subgroup_params(1024, 256, rnd)
        ord_g = q  # 256 битов, не 1024
    else:
        p, q, g = gen_safe_params(256, rnd)
        ord_g = p - 1  # 255 битов
    elapsed0 = time.perf_counter() - t0

    print(f"p = {p} ({p.bit_length()} бит)")
    print(f"q = {q} ({q.bit_length()} бит)")
    print(f"g = {g}")
    # ord_g - порядок генератора

    # A
    t1 = time.perf_counter()
    x = rnd.randrange(2, ord_g)
    X = pow(g, x, p)

    # B
    y = rnd.randrange(2, ord_g)
    Y = pow(g, y, p)

    # Обмен X, Y (в реальности по сети)
    # A: K = Y^x mod p
    K_A = pow(Y, x, p)
    # B: K = X^y mod p
    K_B = pow(X, y, p)

    assert K_A == K_B
    K = K_A
    print(f"K = {K}")

    # Сообщение
    msg = "Привет, мир! От \x00 до я..."
    m = message_to_int(msg)
    print(f"Сообщение: {msg!r}")
    print(f"m = {m} ({m.bit_length()} бит)")

    assert m < p, "Сообщение слишком длинное для p"

    # Шифрование: c = m * K mod p
    c = (m * K) % p
    print(f"c = {c}")

    # Расшифровка: m = c * K^-1 mod p
    K_inv = pow(K, -1, p)
    m2 = (c * K_inv) % p

    msg2 = int_to_message(m2)
    print(f"Расшифровано: {msg2!r}")
    assert msg == msg2
    elapsed1 = time.perf_counter() - t1

    print()
    print(f"Генерация p, q, g:    {elapsed0:.3f}s")
    print(f"Протокол + сообщение: {elapsed1:.3f}s")


def mqv_demo(*, group_mode: bool):
    print(LINE_SEPARATOR)
    rnd = SystemRandom()

    print("Генерация параметров...")
    t0 = time.perf_counter()
    if group_mode:
        p, q, g = gen_subgroup_params(1024, 256, rnd)
    else:
        p, q, g = gen_safe_params(256, rnd)
        # В safe prime g имеет порядок p−1 = 2q, не q.
        # Формулы MQV выведены для подгруппы порядка q — там показатель корректно берётся mod q.
        # При порядке 2q выражение g^(x+da mod q) ≠ g^(x+da) mod p, и S_A ≠ S_B с вероятностью ~50%.
        g = pow(g, 2, p)  # переходим в подгруппу порядка q
    elapsed0 = time.perf_counter() - t0
    # q - порядок генератора

    print(f"p = {p} ({p.bit_length()} бит)")
    print(f"q = {q} ({q.bit_length()} бит)")
    print(f"g = {g}")

    l = cdiv(q.bit_length(), 2)
    mask = (1 << l) - 1
    base = 1 << l
    print(f"l = {l}")

    t1 = time.perf_counter()

    # Долговременные ключи (в реальности — из справочника)
    a = rnd.randrange(2, q)
    A = pow(g, a, p)
    b = rnd.randrange(2, q)
    B = pow(g, b, p)

    # Сеансовые ключи A и B
    x = rnd.randrange(2, q)
    X = pow(g, x, p)
    y = rnd.randrange(2, q)
    Y = pow(g, y, p)

    # Обмен X, Y

    # Коэффициенты d и e из X, Y
    d = base + (X & mask)
    e = base + (Y & mask)

    # A: S_A = (Y · B^e)^(x + d·a) mod p
    S_A = pow(Y * pow(B, e, p) % p, (x + d * a) % q, p)

    # B: S_B = (X · A^d)^(y + e·b) mod p
    S_B = pow(X * pow(A, d, p) % p, (y + e * b) % q, p)

    assert S_A == S_B
    K = S_A
    print(f"K = {K}")

    # Сообщение
    msg = "Привет, мир! От \x00 до я..."
    m = message_to_int(msg)
    print(f"Сообщение: {msg!r}")
    print(f"m = {m} ({m.bit_length()} бит)")

    assert m < p, "Сообщение слишком длинное для p"

    # Шифрование: c = m * K mod p
    c = (m * K) % p
    print(f"c = {c}")

    # Расшифровка
    K_inv = pow(K, -1, p)
    m2 = (c * K_inv) % p

    msg2 = int_to_message(m2)
    print(f"Расшифровано: {msg2!r}")
    assert msg == msg2
    elapsed1 = time.perf_counter() - t1

    print()
    print(f"Генерация p, q, g:    {elapsed0:.3f}s")
    print(f"Протокол + сообщение: {elapsed1:.3f}s")


if __name__ == "__main__":
    dh_demo(group_mode=False)
    dh_demo(group_mode=True)
    mqv_demo(group_mode=False)
    mqv_demo(group_mode=True)
    print(LINE_SEPARATOR)
