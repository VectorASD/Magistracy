"""
Клиент для РГР: подключение к комнате, ввод пароля, конфирмация.

Сетевые части (MQV, шифрование, отправка сообщений) — отдельно.
Здесь только регистрация: kind=0 (UID), kind=1 (join), kind=2 (password),
kind=3 (create).
"""

import socket
import sys
from io import BytesIO

from codec import (
    read_byte, write_byte,
    read_str, write_str,
    read_uleb128, write_uleb128,
)


HOST = "127.0.0.1"
PORT = 5000


# ---------- buffered IO (симметрично серверу) ----------

class Client:
    def __init__(self, host, port):
        self.sock = socket.create_connection((host, port))
        self.rbuf = BytesIO()
        self.wbuf = BytesIO()
        self.uid = None

    def _end(self) -> int:
        pos = self.rbuf.tell()
        self.rbuf.seek(0, 2)
        end = self.rbuf.tell()
        self.rbuf.seek(pos)
        return end

    def read(self, n: int) -> bytes:
        while self._end() - self.rbuf.tell() < n:
            pos = self.rbuf.tell()
            data = self.sock.recv(4096)
            if not data:
                raise EOFError("connection closed")
            self.rbuf.seek(0, 2)
            self.rbuf.write(data)
            self.rbuf.seek(pos)
        return self.rbuf.read(n)

    def write(self, data: bytes) -> None:
        self.wbuf.write(data)

    def flush(self) -> None:
        data = self.wbuf.getvalue()
        if data:
            self.sock.sendall(data)
            self.wbuf.truncate(0)
            self.wbuf.seek(0)

    def reset_input(self) -> None:
        if self.rbuf.tell() == self._end():
            self.rbuf.truncate(0)
            self.rbuf.seek(0)

    def close(self):
        self.sock.close()

    # ---------- RPC ----------

    def get_uid(self) -> str:
        write_byte(self.write, 0)
        self.flush()
        uid = read_str(self.read)
        self.reset_input()
        return uid

    def join_room(self, room_id: str) -> int:
        """0 — не создана, 1 — подключён, 2 — запаролена, 3 — мест нет."""
        write_byte(self.write, 1)
        write_str(self.write, room_id)
        self.flush()
        code = read_byte(self.read)
        self.reset_input()
        return code

    def send_password(self, password: str) -> int:
        """0 — не было join, 1 — не подошёл, 2 — подошёл, 3 — мест нет."""
        write_byte(self.write, 2)
        write_str(self.write, password)
        self.flush()
        code = read_byte(self.read)
        self.reset_input()
        return code

    def create_room(self, room_id: str, password: str) -> int:
        """0 — уже существует, 1 — создана и ты внутри, 2 — не смог добавить."""
        write_byte(self.write, 3)
        write_str(self.write, room_id)
        write_str(self.write, password)
        self.flush()
        code = read_byte(self.read)
        self.reset_input()
        return code

    def wait_room(self) -> int:
        """Long-poll: блокируется, пока состав комнаты не изменится.
        Возвращает число участников."""
        write_byte(self.write, 4)
        self.flush()
        count = read_uleb128(self.read)
        self.reset_input()
        return count

    def list_members(self) -> list[str]:
        """Список UID в текущей комнате."""
        write_byte(self.write, 5)
        self.flush()
        n = read_uleb128(self.read)
        members = [read_str(self.read) for _ in range(n)]
        self.reset_input()
        return members


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


def show_members(members: list[str], me: str) -> None:
    print(f"Участники ({len(members)}):")
    for uid in members:
        mark = " ← ты" if uid == me else ""
        print(f"  {uid}{mark}")

def room_session(client: Client) -> None:
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

def handle_command(client: Client, cmd: str, members: list[str]) -> None:
    """
    Заглушка под будущие команды: отправка сообщений, файлов и т.п.
    Пока любая неизвестная команда — RuntimeError.
    """
    # TODO: handshake MQV, обмен X, Y, A, B
    # TODO: ожидание второго участника (kind=4)
    # TODO: обмен шифрованными сообщениями (kind=6..8)
    raise RuntimeError(f"команда {cmd!r} не поддерживается")


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else PORT

    client = Client(host, port)
    try:
        client.uid = client.get_uid()
        print(f"Твой UID: {client.uid}")

        room_id = choose_room(client)
        print(f"Готов. Ты в комнате {room_id!r} под UID {client.uid!r}.")
        room_session(client)
    finally:
        client.close()


if __name__ == "__main__":
    main()
