from hashlib import sha256
import struct
from time import time
import os
import sys
import pickle
from random import randint

import ASDcoderAES # написан мною ещё в 2019 году, оптимизирован в 2021 году
import mygram      # тот же AES, но с ошеломительной оптимизацией от разработчиков telegram! Бонусом ige256, cbc256, TDF reader и KeyFile reader

ASDcoderAES.Nr = 14 # а было 10, т.к. в Java, да и в целом, настроено именно так...



def test():
    password = "MeowMeowMeow!"
    key = sha256(password.encode("utf-8")).digest()
    assert len(key) == 32 # именно такая длина и требуется в AES

    # eK -> expandedKey
    eK1 = ASDcoderAES.KeyExpansion(key)
    eK2 = mygram.aes256_set_encryption_key(key)
    ek3 = mygram.aes256_set_decryption_key(eK2, is_eK = True)
    assert ek3 == mygram.aes256_set_decryption_key(key)

    viewA = tuple(zip(*eK1))
    viewB = tuple(tuple(struct.pack(">I", num)) for num in eK2)
    print(len(viewA), len(viewB)) # 60 60
    print(viewA)
    print(viewB)
    # вывод: это всё равно разные KeyExpansion... Хоть и начало очень похоже
    # они как-то умудрились sbox встроить прямо в ключ!

    T1 = time()

    ASDcoderAES.KeyC = eK1
    encoded = ASDcoderAES.EncoderAES("test message")
    decoded = ASDcoderAES.DecoderAES(encoded)
    print("encoded:", encoded) # bfed357e69d4d1ff0e95909eee3e9a59
    print("decoded:", decoded) # test message

    T2 = time()

    text = "test message".encode("utf-8")
    pad = 16 - len(text) & 15
    text += bytes((pad,)) * pad

    encoded = mygram.aes256_encrypt(text,    eK2)
    decoded = mygram.aes256_decrypt(encoded, ek3)
    print("tg encoded:", encoded.hex()) # e470bdff5ea010dee96a2af48aaf2f91
    print("tg decoded:", decoded[:-decoded[-1]].decode("utf-8")) # test message
    # вывод: хоть в обоих случаях это AES с 14-мя раундами, но они почему-то разные...

    T3 = time()

    iv = b"\0" * 16
    assert mygram.cbc256(text, key, iv, True) == encoded

    print("my AES:", T2 - T1) # 0.017785310745239258
    print("tg AES:", T3 - T2) # 0.018413782119750977, в смысле чуть медленнее?!?!?!?!?



def get_appdata_path() -> str:
    if sys.platform.startswith("win"):
        # В Windows используем переменную окружения APPDATA
        return os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming"))
    else:
        # В Linux/macOS чаще всего используется ~/.config
        return os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))

class Storage:
    def __init__(self, name):
        appdata = get_appdata_path()
        workdir = os.path.join(appdata, "ASD_storage")
        os.makedirs(workdir, exist_ok=True)
        self.path = os.path.join(workdir, name)
        self.pw_base = {}
        self.load_passwords()

    @staticmethod
    def password_to_ek(password):
        key = sha256(password.encode("utf-8")).digest()
        assert len(key) == 32
        return mygram.aes256_set_encryption_key(key)

    def store_password(self, key, eK):
        # print(self.path, key in self.pw_base)
        if key in self.pw_base: return
        with open(self.path, "ab") as file:
            pickle.dump((key, eK), file, protocol=4)
        self.pw_base[key] = eK

    def load_passwords(self):
        try:
            with open(self.path, "rb") as file:
                while True:
                    key, eK = pickle.load(file)
                    self.pw_base[key] = eK
        except (EOFError, FileNotFoundError): pass

    def check_password(self, key, name = None):
        try: return True, self.pw_base[key]
        except KeyError: pass

        password = input(f"Введите пароль для {name or key!r}: ")
        eK = self.password_to_ek(password)
        return False, mygram.aes256_set_decryption_key(eK, is_eK = True)

    def store(self, obj, password, path):
        data = pickle.dumps(obj, protocol=4)
        pad = 16 - len(data) & 15

        data += bytes((pad,)) * pad
        eK = self.password_to_ek(password)
        iv = bytes(randint(1, 255) for i in range(16))

        encoded = mygram.cbc256(data, eK, iv, True, is_eK = True)
        with open(path, "wb") as file:
            file.write(iv)
            file.write(encoded)

        key = os.path.abspath(path)
        eK  = mygram.aes256_set_decryption_key(eK, is_eK = True)
        self.store_password(key, eK)

    def load(self, path, name = None):
        with open(path, "rb") as file:
            iv = file.read(16)
            encoded = file.read()

        while True:
            key = os.path.abspath(path)
            stored, eK = self.check_password(key, name)

            decoded = mygram.cbc256(encoded, eK, iv, False, is_eK = True)

            try:
                # result = pickle.loads(decoded[:-decoded[-1]])
                result = pickle.loads(decoded) # удаление pad можно пропустить, из-за особенности pickle
                break
            except Exception:
                msg = f"Неверный пароль от {name or key!r}!"
                if stored: raise ValueError(msg)
                print(msg)

        self.store_password(key, eK)
        return result

def test2():
    storage = Storage("test.asd")
    # storage.store({123: "meow!"}, "Meow!", "token.asd")
    obj = storage.load("token.asd", "token")
    print(obj)

if __name__ == "__main__":
    # test()
    test2()
