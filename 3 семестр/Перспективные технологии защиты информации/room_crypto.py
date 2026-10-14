"""
Крипто-слой поверх комнаты.

- derive_key(password, salt) → 32 байта ключа (PBKDF2-HMAC-SHA256)
- make_verifier(kc)          → (iv, ct)  — публичный verifier пароля
- check_verifier(kc, iv, ct) → bool
- encrypt(kc, plaintext)     → (iv, ct)
- decrypt(kc, iv, ct)        → plaintext
"""

import os
from hashlib import sha256, pbkdf2_hmac
from typing import Optional

from sosemanuk import (
    SosemanukKeyContext,
    SosemanukRunContext,
    sosemanuk_schedule,
    sosemanuk_init,
    sosemanuk_encrypt,
)


PBKDF2_ITERATIONS = 100_000
SALT_LEN          = 16
IV_LEN            = 16
VERIFIER_PT_LEN   = 256  # длина проверочного сообщения (просто хотелка)
VERIFIER_TAG_LEN  = 32   # сколько из них байтов съесть sha256
VERIFIER_DATA_LEN = VERIFIER_PT_LEN - VERIFIER_TAG_LEN  # что осталось для os.urandom


def derive_key(password: str, salt: bytes) -> bytes:
    return pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt,
        PBKDF2_ITERATIONS, dklen=32,
    )

def make_kc(key: bytes) -> SosemanukKeyContext:
    kc = SosemanukKeyContext()
    sosemanuk_schedule(kc, key)
    return kc

def _xor(data: bytes, kc: SosemanukKeyContext, iv: bytes) -> bytes:
    rc = SosemanukRunContext()
    sosemanuk_init(rc, kc, iv)
    return sosemanuk_encrypt(rc, data)


def make_verifier(kc: SosemanukKeyContext) -> tuple[bytes, bytes, bytes]:
    """Генерирует (iv, ct, proof). Клиент-создатель кладёт это в комнату открыто."""
    data  = os.urandom(VERIFIER_DATA_LEN)
    tag   = sha256(data).digest()
    pt    = data + tag
    iv    = os.urandom(IV_LEN)
    proof = sha256(pt).digest()
    return iv, _xor(pt, kc, iv), proof

def check_verifier(kc: SosemanukKeyContext, iv: bytes, ct: bytes) -> tuple[bool, bytes]:
    if len(ct) != VERIFIER_PT_LEN:
        return False, b""
    pt    = _xor(ct, kc, iv)
    proof = sha256(pt).digest()
    data, tag = pt[:VERIFIER_DATA_LEN], pt[VERIFIER_DATA_LEN:]
    return sha256(data).digest() == tag, proof


def encrypt(kc: Optional[SosemanukKeyContext], plaintext: bytes) -> bytes:
    if kc is None:
        return plaintext

    iv = os.urandom(IV_LEN)
    ct = _xor(plaintext, kc, iv)
    return iv + ct

def decrypt(kc: Optional[SosemanukKeyContext], data: bytes) -> bytes:
    if kc is None:
        return data

    if len(data) < IV_LEN:
        return b"??? no IV ???"

    iv = data[:IV_LEN]
    ct = data[IV_LEN:]
    return _xor(ct, kc, iv)
