"""
Клиент для РГР: подключение к комнате, ввод пароля, конфирмация.

Сетевые части (MQV, шифрование, отправка сообщений) — отдельно.
Здесь только регистрация: kind=0 (UID), kind=1 (join), kind=2 (password),
kind=3 (create).
"""

import socket
import sys
from io import BytesIO
import threading

from codec import (
    read_byte, write_byte,
    read_str, write_str,
    read_uleb128,
    read_str_bin, write_str_bin,
)


HOST = "127.0.0.1"
PORT = 5000


class Client:
    def __init__(self, host, port, timeout=0.1):
        self.sock = socket.create_connection((host, port))
        self.sock.settimeout(timeout)
        self.rbuf = BytesIO()
        self.wlock = threading.Lock()
        self.running = False
        self.uid = None

        self.callbacks = {}                 # kind -> cb (приложение)

        self.handlers = {                   # kind -> парсер+эмиттер
            0: self.handle_uid,
            1: self.handle_join,
            2: self.handle_password,
            3: self.handle_create,
            4: self.handle_count,
            5: self.handle_members,
            10: self.handle_message,
        }

    # ---------- buffered IO ----------

    def _end(self):
        pos = self.rbuf.tell()
        self.rbuf.seek(0, 2)
        end = self.rbuf.tell()
        self.rbuf.seek(pos)
        return end

    def read(self, n: int) -> bytes:
        while self._end() - self.rbuf.tell() < n:
            pos = self.rbuf.tell()
            try:
                data = self.sock.recv(4096)
            except socket.timeout:
                continue
            if not data:
                raise EOFError("connection closed")
            self.rbuf.seek(0, 2)
            self.rbuf.write(data)
            self.rbuf.seek(pos)
        return self.rbuf.read(n)

    def send(self, kind: int, payload):
        buf = BytesIO()
        write_byte(buf.write, kind)
        if payload is not None:
            payload(buf.write)
        with self.wlock:
            self.sock.sendall(buf.getvalue())

    def close(self):
        self.running = False
        try:
            self.sock.close()
        except OSError:
            pass

    # ---------- receiver ----------

    def start(self):
        self.running = True
        try:
            self._loop()
        except KeyboardInterrupt:
            print("\nExited with Ctrl+C")
        finally:
            self.close()

    def _loop(self):
        while self.running:
            kind = read_byte(self.read)
            h = self.handlers.get(kind)
            if h is None:
                continue
            try:
                h(self.read)
            except Exception as e:
                print(f"[recv {kind}] {type(e).__name__}: {e}", file=sys.stderr)

    def register(self, kind: int, cb):
        self.callbacks[kind] = cb

    # ---------- senders: задействуют rpc на сервере ----------

    def get_uid(self):
        self.send(0, None)

    def join_room(self, room_id: str):
        self.send(1, lambda w: write_str(w, room_id))

    def send_password(self, password: str):
        self.send(2, lambda w: write_str(w, password))

    def create_room(self, room_id: str, password: str):
        def payload(w):
            write_str(w, room_id)
            write_str(w, password)
        self.send(3, payload)

    def list_members(self):
        self.send(5, None)

    def send_message(self, target_uid: str, data: bytes):
        def payload(w):
            write_str(w, target_uid)
            write_str_bin(w, data)
        self.send(10, payload)

    # ---------- handlers: wire-парсеры ----------

    def handle_uid(self, read):
        cb = self.callbacks.get(0)
        if cb:
            cb(read_str(read))

    def handle_join(self, read):
        cb = self.callbacks.get(1)
        if cb:
            cb(read_byte(read))

    def handle_password(self, read):
        cb = self.callbacks.get(2)
        if cb:
            cb(read_byte(read))

    def handle_create(self, read):
        cb = self.callbacks.get(3)
        if cb:
            cb(read_byte(read))

    def handle_count(self, read):
        cb = self.callbacks.get(4)
        if cb:
            cb(read_uleb128(read))

    def handle_members(self, read):
        n = read_uleb128(read)
        members = [read_str(read) for _ in range(n)]
        cb = self.callbacks.get(5)
        if cb:
            cb(members)

    def handle_message(self, read):
        sender = read_str(read)
        flag = read_byte(read)
        data = read_str_bin(read)
        cb = self.callbacks.get(10)
        if cb:
            cb(sender, flag, data)


# ---------- ввод с валидацией ----------

def input_int(prompt: str) -> int:
    """Читает строку, пока не получится int."""
    while True:
        s = input(prompt).strip()
        try:
            return int(s)
        except ValueError:
            print(f"  «{s}» — не число, попробуй ещё.")

def input_yes_no(prompt: str) -> bool:
    """yes/no/1/0/да/нет."""
    yes = {"y", "yes", "д", "да", "1"}
    no  = {"n", "no", "н", "нет", "0"}
    while True:
        s = input(prompt).strip().lower()
        if s in yes:
            return True
        if s in no:
            return False
        print("  Ответь yes/да/1 или no/н/0.")

def input_password(prompt: str = "Пароль: ") -> str:
    """Ввод пароля с конфирмацией. Пустая строка допустима только если
    вызывающий код сам решил, что пароль не нужен."""
    while True:
        p1 = input(prompt)
        p2 = input("Повтори пароль: ")
        if p1 == p2:
            return p1
        print("  Пароли не совпали, попробуй ещё.")

def input_room_id(prompt: str = "Номер комнаты: ") -> str:
    """Пустая строка не допускается."""
    while True:
        s = input(prompt).strip()
        if s:
            return s
        print("  Пустой ID не подходит.")


# ---------- сценарий подключения ----------

def choose_room(client: Client) -> str:
    """Крутится, пока клиент не окажется в комнате. Возвращает room_id."""
    while True:
        room_id = input_room_id()
        code = client.join_room(room_id)

        if code == 1:
            print(f"Ты в комнате {room_id!r}.")
            return room_id

        if code == 0:
            print(f"Комнаты {room_id!r} нет.")
            if not input_yes_no("Создать её? (yes/no): "):
                continue
            if input_yes_no("С паролем? (yes/no): "):
                password = input_password()
            else:
                password = ""
            c = client.create_room(room_id, password)
            if c == 1:
                print(f"Комната {room_id!r} создана, ты внутри.")
                return room_id
            if c == 0:
                # кто-то создал её прямо сейчас — начнём заново с join
                print("  Комната уже существует, попробуй ещё раз.")
                continue
            raise RuntimeError(f"create_room: неожиданный код {c}")

        if code == 2:
            print(f"Комната {room_id!r} запаролена.")
            password = input("Пароль: ")
            c = client.send_password(password)
            if c == 2:
                print(f"Ты в комнате {room_id!r}.")
                return room_id
            if c == 1:
                print("  Пароль не подошёл.")
                continue
            if c == 0:
                raise RuntimeError("send_password: сервер потерял join")
            if c == 3:
                print("  Комната заполнена.")
                continue
            raise RuntimeError(f"send_password: неожиданный код {c}")

        if code == 3:
            print(f"Комната {room_id!r} заполнена.")
            continue

        raise RuntimeError(f"join_room: неожиданный код {code}")


def show_members(members: list[str], me: str):
    print(f"Участники ({len(members)}):")
    for uid in members:
        mark = " ← ты" if uid == me else ""
        print(f"  {uid}{mark}")

def room_session(client: Client):
    """Основной REPL."""
    while True:
        # 1. Обновляем список с сервера
        try:
            members = client.list_members()
        except (EOFError, OSError) as e:
            print(f"Соединение потеряно: {e}")
            return

        show_members(members, client.uid)

        # 2. Если один — ждём второго через long-poll
        if len(members) < 2:
            print("Ожидание второго участника... (Ctrl+C — выйти)")
            try:
                client.wait_room()
            except (EOFError, OSError):
                print("Соединение потеряно.")
                return
            except KeyboardInterrupt:
                print()
                return
            continue

        # 3. Меню
        print("пусто — обновить, q/quit/e/exit — выйти")
        try:
            cmd = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if cmd in ("q", "quit", "e", "exit"):
            return
        if cmd == "":
            continue

        # 4. Всё остальное — попытка операции с участниками.
        #    Любая ошибка (disconnected user, гонки в списке) — обновляем
        #    список и продолжаем, а не падаем.
        try:
            handle_command(client, cmd, members)
        except RuntimeError as e:
            print(f"Ошибка: {e}")

def handle_command(client: Client, cmd: str, members: list[str]):
    """
    Заглушка под будущие команды: отправка сообщений, файлов и т.п.
    Пока любая неизвестная команда — RuntimeError.
    """
    # TODO: handshake MQV, обмен X, Y, A, B
    # TODO: ожидание второго участника (kind=4)
    # TODO: обмен шифрованными сообщениями (kind=6..8)
    raise RuntimeError(f"команда {cmd!r} не поддерживается")


def app():
    host = sys.argv[1] if len(sys.argv) > 1 else HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else PORT

    def on_uid(uid: str):
        client.uid = uid
        print(f"UID: {uid}")

    client = Client(host, port)
    client.register(0, on_uid)

    client.get_uid()
    client.start()


if __name__ == "__main__":
    app()
