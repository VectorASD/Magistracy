"""
TCP-сервер: комнаты + relay зашифрованных сообщений.

Протокол: первый байт — kind команды. Клиент шлёт запрос, сервер
отвечает kind'ом на push-канал того же клиента (или broadcast'ит
по комнате).

Сервер не знает ключа K и не расшифровывает трафик между клиентами —
он только связывает участников комнаты и перекладывает пакеты.
"""

import socket
import sys
import threading
from io import BytesIO
from collections import deque
import os
import atexit

from typing import Optional

from codec import (
    read_byte, write_byte,
    read_str, write_str,
    write_uleb128,
    read_str_bin, write_str_bin,
)
from profiling import measure, STATS


HOST = "0.0.0.0"
PORT = 5000

ROOM_MAX = 100


class Client:
    def __init__(self, uid, conn, timeout=0.5):
        self.uid = uid
        self.conn = conn
        conn.settimeout(timeout)
        self.room: Optional[Room] = None
        self.pending_room: Optional[Room] = None
        self.rbuf = BytesIO()
        self.wlock = threading.Lock()

    def push(self, kind: int, payload):
        buf = BytesIO()
        write_byte(buf.write, kind)
        payload(buf.write)
        with self.wlock:
            try:
                self.conn.sendall(buf.getvalue())
            except OSError as e:
                print(f"{self.uid}: push failed: {e}", flush=True)

    def push_messages(self, messages: list[tuple[str, int, bool, bytes]]) -> None:
        """Отправить один kind=10 со списком сообщений (sender, flag, is_blob, data)."""
        if not messages:
            return

        def payload(w):
            write_uleb128(w, len(messages))
            for sender, flag, is_blob, data in messages:
                write_str(w, sender)
                write_byte(w, flag)
                write_byte(w, is_blob)
                write_str_bin(w, data)

        self.push(10, payload)

    # --- buffered input ---

    def _end(self) -> int:
        pos = self.rbuf.tell()
        self.rbuf.seek(0, 2)
        end = self.rbuf.tell()
        self.rbuf.seek(pos)
        return end

    def read(self, n: int) -> bytes:
        while self._end() - self.rbuf.tell() < n:
            pos = self.rbuf.tell()
            try:
                data = self.conn.recv(4096)
            except socket.timeout:
                continue
            if not data:
                raise EOFError("connection closed")
            self.rbuf.seek(0, 2)
            self.rbuf.write(data)
            self.rbuf.seek(pos)
        return self.rbuf.read(n)

    def reset_input(self) -> None:
        if self.rbuf.tell() == self._end():
            self.rbuf.truncate(0)
            self.rbuf.seek(0)


HISTORY_LIMIT = 1000

class Room:
    def __init__(self, room_id, salt = None,
                 verifier_iv = None, verifier_ct = None, verifier_proof = None,
                 max_members = ROOM_MAX):
        self.room_id        = room_id
        self.max_members    = max_members
        self.salt           = salt
        self.verifier_iv    = verifier_iv
        self.verifier_ct    = verifier_ct
        self.verifier_proof = verifier_proof
        self.members: dict[str, Client] = {}
        self.lock    = threading.Lock()
        self.history = deque(maxlen=HISTORY_LIMIT)  # а, вот как... чтобы вручную не юзать popleft!

    @property
    def is_protected(self):
        return bool(self.salt)

    def add(self, client: Client) -> bool:
        with self.lock:
            if client.uid in self.members:
                return True
            if len(self.members) >= self.max_members:
                return False
            self.members[client.uid] = client
        return True

    def remove(self, client: Client) -> None:
        with self.lock:
            if client.uid in self.members:
                del self.members[client.uid]

    def push_count(self) -> None:
        with self.lock:
            members = list(self.members.values())
        n = len(members)
        for m in members:
            m.push(4, lambda w, c=n: write_uleb128(w, c))

    def snapshot_uids(self) -> list[str]:
        with self.lock:
            return list(self.members.keys())

    def remember(self, sender_uid: str, flag: int, is_blob: bool, data: bytes):
        with self.lock:
            self.history.append((sender_uid, flag, is_blob, data))
            from sosemanuk import short_repr
            print("Сервер сообщение видит так:", short_repr(data))

    def snapshot_history(self) -> list[tuple[str, int, bool, bytes]]:
        with self.lock:
            return list(self.history)


class Server:
    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port

        self.uid_counter = 0
        self.uid_lock = threading.Lock()

        self.clients = {}
        self.clients_lock = threading.Lock()

        self.rooms: dict[str, Room] = {}
        self.rooms_lock = threading.Lock()

        self.blobs: dict[bytes, bytes] = {}
        self.blobs_lock = threading.Lock()

        self.handlers = {
            0: self.handle_uid,
            1: self.handle_join,
            2: self.handle_password,
            3: self.handle_create,
            5: self.handle_list_members,
            10: self.handle_send_message,
            11: self.handle_fetch_blob,
        }

    def new_uid(self) -> str:
        with self.uid_lock:
            uid = self.uid_counter
            self.uid_counter += 1
        return f"user_{uid}"

    def get_room(self, room_id):
        with self.rooms_lock:
            return self.rooms.get(room_id)

    # --- main loop ---

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((self.host, self.port))
            srv.listen(16)
            srv.settimeout(0.5)
            print(f"listening on {self.host}:{self.port}", flush=True)
            try:
                while True:
                    try:
                        conn, addr = srv.accept()
                    except socket.timeout:
                        continue
                    print(f"connected: {addr}", flush=True)
                    threading.Thread(
                        target=self.handle_client,
                        args=(conn, addr),
                        daemon=True,
                    ).start()
            except KeyboardInterrupt:
                print("\nshutting down", flush=True)

    def handle_client(self, conn, addr):
        uid = self.new_uid()
        client = Client(uid, conn)
        with self.clients_lock:
            self.clients[uid] = client
        print(f"{addr} -> {uid}", flush=True)
        try:
            while True:
                kind = read_byte(client.read)
                handler = self.handlers.get(kind)
                if handler is None:
                    print(f"{uid}: unknown kind {kind}", flush=True)
                    break
                handler(client)
                client.reset_input()
        except EOFError:
            pass
        except Exception as e:
            print(f"{uid}: {type(e).__name__}: {e}", flush=True)
        finally:
            print(f"{uid} disconnected", flush=True)
            self.disconnect(client)
            conn.close()

    def disconnect(self, client):
        with self.clients_lock:
            self.clients.pop(client.uid, None)
        room = client.room
        if room is not None:
            room.remove(client)
            client.room = None
            room.push_count()

    # --- handlers ---

    def handle_uid(self, client: Client):
        client.push(0, lambda w: write_str(w, client.uid))

    def handle_join(self, client: Client):
        room_id = read_str(client.read)
        old = client.room
        if old is not None:
            old.remove(client)
            client.room = None
            old.push_count()
        client.pending_room = None

        room = self.get_room(room_id)
        if room is None:
            client.push(1, lambda w: write_byte(w, 0))      # не создана
            return

        if not room.is_protected:
            if room.add(client):
                client.room = room
                client.push(1, lambda w: write_byte(w, 1))  # зашёл
                room.push_count()
                client.push_messages(room.snapshot_history())
            else:
                client.push(1, lambda w: write_byte(w, 3))  # мест нет
            return

        # protected
        client.pending_room = room

        def payload_with_verifier(w):
            write_byte(w, 2)  # нужна проверка
            write_str_bin(w, room.salt)
            write_str_bin(w, room.verifier_iv)
            write_str_bin(w, room.verifier_ct)
        client.push(1, payload_with_verifier)


    def handle_password(self, client: Client):
        """kind=2 теперь значит `клиент подтвердил пароль, добавь его в комнату`."""
        proof = read_str_bin(client.read)
        room = client.pending_room
        if room is None:
            client.push(2, lambda w: write_byte(w, 0))  # сначала kind=1
        elif proof != room.verifier_proof:
            # Клиент соврал о прохождении челленджа
            # Исключительно нужно для того, чтобы кто попало не мог
            # считать все blob-id из истории чата. Это всё равно не даёт
            # без ключа ни серверу, ни клиенту доступ к зашифрованным данным.
            client.push(2, lambda w: write_byte(w, 1))
        elif room.add(client):
            client.room = room
            client.pending_room = None
            client.push(2, lambda w: write_byte(w, 2))  # зашёл
            room.push_count()
            client.push_messages(room.snapshot_history())
        else:
            client.push(2, lambda w: write_byte(w, 3))  # мест нет

    def handle_create(self, client: Client):
        room_id = read_str(client.read)
        salt    = read_str_bin(client.read)
        if salt:
            verifier_iv    = read_str_bin(client.read)
            verifier_ct    = read_str_bin(client.read)
            verifier_proof = read_str_bin(client.read)
        else:
            salt = verifier_iv = verifier_ct = verifier_proof = None

        with self.rooms_lock:
            if room_id in self.rooms:
                client.push(3, lambda w: write_byte(w, 0))  # уже существует
                return
            room = Room(room_id, salt, verifier_iv, verifier_ct, verifier_proof)
            self.rooms[room_id] = room

        if client.room is not None:
            old = client.room
            old.remove(client)
            client.room = None
            old.push_count()

        if room.add(client):
            client.room = room
            client.push(3, lambda w: write_byte(w, 1))  # удалось создать
            room.push_count()
        else:
            client.push(3, lambda w: write_byte(w, 2))  # не удалось создать

    def handle_list_members(self, client: Client):
        room = client.room
        if room is None:
            client.push(5, lambda w: write_uleb128(w, 0))
            return
        uids = room.snapshot_uids()

        def payload(w):
            write_uleb128(w, len(uids))
            for uid in uids:
                write_str(w, uid)

        client.push(5, payload)

    def handle_send_message(self, client: Client):
        with measure("srv.read"):
            r = client.read
            target_uid = read_str(r)
            is_blob = bool(read_byte(r))
            metadata = read_str_bin(r) if is_blob else None
            data = read_str_bin(r)

        room = client.room
        if room is None:
            return

        flag = 1 if target_uid else 0
        if is_blob:
            with measure("srv.blob_store"):
                uuid = os.urandom(16)
                with self.blobs_lock:
                    self.blobs[uuid] = data
                data = metadata + uuid  # в историю и рассылку едет metadata вместо blob'а

        with measure("srv.remember"):
            room.remember(client.uid, flag, is_blob, data)

        messages = [(client.uid, flag, is_blob, data)]

        if target_uid:
            # личное: ровно одному получателю
            with measure("srv.unicast"):
                with room.lock:
                    other = room.members.get(target_uid)
                if other is None:
                    print(f"[!] {client.uid}: target {target_uid} not in room", flush=True)
                else:
                    other.push_messages(messages)
        else:
            # broadcast: всем
            with measure("srv.broadcast"):
                with room.lock:
                    members = list(room.members.values())
                for other in members:
                    # if other.uid != client.uid:
                    # В нормальном мессенджере у нас клиент добавляет сообщение,
                    # а сервер лишь заменяет "часы" на "одну галочку".
                    # Но, т.к. это приложение не для web, а локальное, то сильно пинговать просто нечему
                    other.push_messages(messages)

    def handle_fetch_blob(self, client: Client):
        with measure("srv.blob_read"):
            uuid = read_str_bin(client.read)
            with self.blobs_lock:
                blob = self.blobs.get(uuid)

        def payload(w):
            exists = blob is not None
            write_str_bin(w, uuid)
            write_byte(w, exists)
            if exists:
                write_str_bin(w, blob)
        client.push(11, payload)


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else PORT
    atexit.register(STATS.dump, "server")
    Server(host, port).run()


if __name__ == "__main__":
    main()
