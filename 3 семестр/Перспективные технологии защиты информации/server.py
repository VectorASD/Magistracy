"""
TCP-сервер: комнаты + relay зашифрованных сообщений.

Протокол: первый байт — kind команды. Клиент шлёт один запрос, ждёт
ответ, сервер сбрасывает буфер после обработки.

Сервер не знает ключа K и не расшифровывает трафик между клиентами —
он только связывает участников комнаты и перекладывает пакеты.
"""

import socket
import sys
import threading
from io import BytesIO

from codec import (
    read_byte, write_byte,
    read_str, write_str, write_str_bin,
    read_uleb128, write_uleb128,
)


HOST = "0.0.0.0"
PORT = 5000

OPEN_ROOM_MAX = 100  # без пароля — комната-беседа
PRIVATE_ROOM_MAX = 2  # с паролем — личный чат


class Client:
    def __init__(self, uid, conn, addr, timeout=0.5):
        self.uid = uid
        self.conn = conn;  conn.settimeout(timeout)
        self.addr = addr
        self.room = None
        self.pending_room = None
        self.peer_uid = None  # выставляется kind=6
        self.rbuf = BytesIO()
        self.wbuf = BytesIO()
        self.inbox = {}  # sender_uid -> list[bytes]
        self.inbox_lock = threading.Lock()

    # --- buffered IO ---

    def _end(self) -> int:
        """Позиция конца буфера, без изменения текущей позиции."""
        pos = self.rbuf.tell()
        self.rbuf.seek(0, 2)
        end = self.rbuf.tell()
        self.rbuf.seek(pos)
        return end

    def read(self, n: int) -> bytes:
        """Прочитать ровно n байт. Блокируется, пока в буфере меньше n."""
        while self._end() - self.rbuf.tell() < n:
            pos = self.rbuf.tell()
            try:
                data = self.conn.recv(4096)
            except socket.timeout:  # дать python обработать Ctrl+C
                continue
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
            self.conn.sendall(data)
            self.wbuf.truncate(0)
            self.wbuf.seek(0)

    def reset_input(self) -> None:
        """Сбросить буфер, если из него вычитано всё."""
        if self.rbuf.tell() == self._end():
            self.rbuf.truncate(0)
            self.rbuf.seek(0)

    # --- mailbox ---

    def push_message(self, sender_uid: str, data: bytes) -> None:
        with self.inbox_lock:
            self.inbox.setdefault(sender_uid, []).append(data)

    def pop_message(self, sender_uid: str):
        with self.inbox_lock:
            q = self.inbox.get(sender_uid)
            return q.pop(0) if q else None


class Room:
    def __init__(self, room_id, password, max_members):
        self.room_id = room_id
        self.password = password
        self.max_members = max_members
        self.members = {}
        self.version = 0                # растёт при каждом изменении состава
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)

    def add(self, client) -> bool:
        with self.lock:
            if client.uid in self.members:
                return True
            if len(self.members) >= self.max_members:
                return False
            self.members[client.uid] = client
            self.version += 1
            self.condition.notify_all()
            return True

    def remove(self, client) -> None:
        with self.lock:
            if client.uid in self.members:
                del self.members[client.uid]
                self.version += 1
                self.condition.notify_all()

    def snapshot_uids(self) -> list[str]:
        with self.lock:
            return list(self.members.keys())

    def wait_change(self, last_version, timeout=None):
        with self.lock:
            self.condition.wait_for(
                lambda: self.version != last_version, timeout=timeout)
            return self.version, len(self.members)


class Server:
    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.uid_counter = 0
        self.uid_lock = threading.Lock()
        self.clients = {}
        self.clients_lock = threading.Lock()
        self.rooms = {}
        self.rooms_lock = threading.Lock()

        self.handlers = {
            0: self.handle_uid,
            1: self.handle_join,
            2: self.handle_password,
            3: self.handle_create,
            4: self.handle_wait_room,
            5: self.handle_list_members,
            6: self.handle_set_peer,
            7: self.handle_send_msg,
            8: self.handle_recv_msg,
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
                    except socket.timeout:  # дать python обработать Ctrl+C
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
        client = Client(uid, conn, addr)
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
                client.flush()
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
        if client.room is not None:
            client.room.remove(client)
            client.room = None

    # --- handlers ---

    def handle_uid(self, client):
        write_str(client.write, client.uid)

    def handle_join(self, client):
        room_id = read_str(client.read)

        # смена комнаты — отписаться от старой
        if client.room is not None:
            client.room.remove(client)
            client.room = None
        client.pending_room = None

        room = self.get_room(room_id)
        if room is None:
            write_byte(client.write, 0)          # не создана
        elif room.password is None:
            if room.add(client):
                client.room = room
                write_byte(client.write, 1)      # подключён
            else:
                write_byte(client.write, 3)      # мест нет
        else:
            client.pending_room = room
            write_byte(client.write, 2)          # запаролена

    def handle_password(self, client):
        password = read_str(client.read)
        room = client.pending_room
        if room is None:
            write_byte(client.write, 0)          # сначала kind=1
        elif password != room.password:
            write_byte(client.write, 1)          # не подошёл
        elif room.add(client):
            client.room = room
            client.pending_room = None
            write_byte(client.write, 2)          # подошёл
        else:
            write_byte(client.write, 3)          # мест нет

    def handle_create(self, client):
        room_id = read_str(client.read)
        password = read_str(client.read)
        if password == "":
            password = None
            max_members = OPEN_ROOM_MAX
        else:
            max_members = PRIVATE_ROOM_MAX

        with self.rooms_lock:
            if room_id in self.rooms:
                write_byte(client.write, 0)      # уже существует
                return
            room = Room(room_id, password, max_members)
            self.rooms[room_id] = room

        if client.room is not None:
            client.room.remove(client)
            client.room = None
        if room.add(client):
            client.room = room
            write_byte(client.write, 1)
        else:
            write_byte(client.write, 2)

    def handle_wait_room(self, client):
        """Long-poll: ждём изменения состава комнаты."""
        room = client.room
        if room is None:
            write_uleb128(client.write, 0)
            return
        with room.lock:
            last_version = room.version
        _, count = room.wait_change(last_version)
        write_uleb128(client.write, count)

    def handle_list_members(self, client):
        room = client.room
        if room is None:
            write_uleb128(client.write, 0)
            return
        uids = room.snapshot_uids()
        write_uleb128(client.write, len(uids))
        for uid in uids:
            write_str(client.write, uid)

    def handle_set_peer(self, client):
        peer_uid = read_str(client.read)
        if client.room is None or peer_uid == client.uid:
            write_byte(client.write, 0)
            return
        with client.room.lock:
            peer = client.room.members.get(peer_uid)
        if peer is None:
            write_byte(client.write, 0)
            return
        client.peer_uid = peer_uid
        write_byte(client.write, 1)

    def handle_send_msg(self, client):
        if client.peer_uid is None:
            write_byte(client.write, 0)
            return
        data = read_str(client.read, True)
        with self.clients_lock:
            target = self.clients.get(client.peer_uid)
        if target is None:
            write_byte(client.write, 0)
            return
        target.push_message(client.uid, data)
        write_byte(client.write, 1)

    def handle_recv_msg(self, client):
        if client.peer_uid is None:
            write_byte(client.write, 0)
            return
        data = client.pop_message(client.peer_uid)
        if data is None:
            write_byte(client.write, 0)
            return
        write_byte(client.write, 1)
        write_str_bin(client.write, data)


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else PORT
    Server(host, port).run()


if __name__ == "__main__":
    main()
