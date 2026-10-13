"""
Клиент: подключение к комнате, ввод пароля, конфирмация.

Сетевые части (MQV, шифрование, отправка сообщений) — отдельно.
Здесь только регистрация: kind=0 (UID), kind=1 (join),
kind=2 (password), kind=3 (create).
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
        self.wlock = threading.Lock()  # wire-lock
        self.running = False

        self.callbacks = {}  # kind -> cb (приложение)

        self.handlers = {   # kind -> парсер+эмиттер
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
        except (EOFError, OSError) as e:
            if self.running:  # закрытие инициировали не мы
                print(f"[recv _loop] {type(e).__name__}: {e}", file=sys.stderr)
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
                return  # поток десинхронизирован, дальше читать нечего

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
        n = read_uleb128(read)
        batch = [
            {"sender": read_str(read),
             "flag": read_byte(read),
             "text": read_str_bin(read).decode("utf-8", "replace")}
            for _ in range(n)
        ]
        cb = self.callbacks.get(10)
        if cb:
            cb(batch)


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


# ---------- приложение ----------

def app(gui = None):
    host = sys.argv[1] if len(sys.argv) > 1 else HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else PORT

    # ~~~ да, это весь контекст клиента ~~~

    uid = None
    room_id = None
    members: list[str] = []
    messages: list[dict] = []

    # ~~~ REPL ~~~

    def _redraw(uid: str, room_id: str, members: list[str], messages: list[dict]):
        sys.stdout.write("\033[2J\033[H")  # clear + cursor home
        # в VSCode сохраняется scrollback,
        # т.е. мы всё ещё видим предыдущие кадры, если покрутим СКМ
        print(f"UID: {uid}")
        print(f"Комната: {room_id}")
        print(f"Участников: {len(members)}")
        for m in members:
            mark = " ← ты" if m == uid else ""
            print(f"  {m}{mark}")
        if messages:
            print("─" * 60)
            for msg in messages:
                kind = "личное" if msg["flag"] else "всем"
                print(f"[{kind}] {msg['sender']}: {msg['text']}")
        print("─" * 60)
        sys.stdout.flush()

    def redraw():
        _redraw(uid, room_id, members, messages)

    # ~~~ событийные мозги приложения ~~~

    def ask_room():
        nonlocal room_id
        room_id = input_room_id()
        client.join_room(room_id)

    def on_uid(value: str):
        nonlocal uid
        uid = value
        print(f"UID: {uid}")
        ask_room()

    def on_join(code: int):
        if code == 1:
            print(f"Ты в комнате {room_id!r}.")
            return

        if code == 0:
            print(f"Комнаты {room_id!r} нет.")
            if not input_yes_no("Создать её? (yes/no): "):
                ask_room()
                return
            if input_yes_no("С паролем? (yes/no): "):
                password = input_password()
            else:
                password = ""
            client.create_room(room_id, password)
            return

        if code == 2:
            print(f"Комната {room_id!r} запаролена.")
            password = input("Пароль: ")
            client.send_password(password)
            return

        if code == 3:
            print(f"Комната {room_id!r} заполнена.")
            ask_room()
            return

        print(f"[join] неизвестный код {code}")
        ask_room()

    def on_create(code: int):
        if code == 1:
            print(f"Комната {room_id!r} создана, ты внутри.")
            return
        if code == 0:
            print(f"Комната {room_id!r} уже существует.")
        elif code == 2:
            print(f"Не удалось войти в {room_id!r}.")
        else:
            print(f"[create] неизвестный код {code}")
        ask_room()

    def on_password(code: int):
        if code == 2:
            print(f"Ты в комнате {room_id!r}.")
            return
        if code == 1:
            print("Пароль не подошёл.")
        elif code == 0:
            print("Сервер потерял состояние join.")
        elif code == 3:
            print(f"Комната {room_id!r} заполнена.")
        else:
            print(f"[password] неизвестный код {code}")
        ask_room()

    def on_count(n: int):
        print(f"Участников: {n}")
        client.list_members()  # триггерим on_members

    def on_members(member_list: list[str]):
        nonlocal members
        members = member_list
        redraw()

    def on_message(_messages: list[dict[str]]):
        messages.extend(_messages)
        redraw()

    client = Client(host, port)
    client.register(0, on_uid)
    client.register(1, on_join)
    client.register(2, on_password)
    client.register(3, on_create)
    client.register(4, on_count)
    client.register(5, on_members)
    client.register(10, on_message)

    if gui is not None:
        _redraw = gui.redraw
        gui.client = client

    client.get_uid()
    client.start()


if __name__ == "__main__":
    app()
