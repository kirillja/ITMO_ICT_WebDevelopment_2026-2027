"""Один поток на TCP-подключение; список клиентов защищён блокировкой."""
from dataclasses import dataclass, field
import socket
import threading
from common import arguments, listener


@dataclass
class Client:
    sock: socket.socket
    name: str = ''
    send_lock: threading.Lock = field(default_factory=threading.Lock)

    def send(self, text):
        # Два серверных потока не должны смешать байты разных сообщений.
        with self.send_lock:
            self.sock.sendall((text + '\n').encode('utf-8'))


class Chat:
    def __init__(self):
        self.clients = {}
        self.lock = threading.Lock()

    def broadcast(self, text, exclude=None):
        with self.lock:
            recipients = [c for sock, c in self.clients.items() if sock is not exclude]
        for client in recipients:
            try:
                client.send(text)
            except OSError:
                # Отключение обнаружит поток чтения этого клиента.
                try:
                    client.sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

    def handle(self, sock):
        client = Client(sock)
        registered = False
        try:
            sock.settimeout(30)
            with sock.makefile('rb') as stream:
                client.send('NAME Введите уникальное имя (1–32 символа):')
                raw = stream.readline(4097)
                if not raw.endswith(b'\n') or len(raw) > 4096:
                    return
                name = raw.decode('utf-8').strip()
                if not 1 <= len(name) <= 32 or any(ord(c) < 32 for c in name):
                    client.send('ERROR Некорректное имя')
                    return
                client.name = name
                with self.lock:
                    if any(c.name.casefold() == name.casefold() for c in self.clients.values()):
                        duplicate = True
                    else:
                        duplicate = False
                        # Сначала подтверждаем имя, затем разрешаем рассылку клиенту.
                        client.send(f'OK Вы вошли как {name}. Выход: /quit')
                        self.clients[sock] = client
                        registered = True
                if duplicate:
                    client.send('ERROR Имя уже занято')
                    return
                print(f'{name} joined', flush=True)
                self.broadcast(f'SYSTEM {name} вошёл в чат', exclude=sock)
                # Для учебного чата чтение ожидает сообщение без таймаута.
                sock.settimeout(None)
                while True:
                    raw = stream.readline(4097)
                    if not raw:
                        break
                    if not raw.endswith(b'\n') or len(raw) > 4096:
                        client.send('ERROR Сообщение слишком длинное')
                        break
                    message = raw.decode('utf-8').strip()
                    if message == '/quit':
                        client.send('BYE До встречи')
                        break
                    if message:
                        self.broadcast(f'MSG {name}: {message}', exclude=sock)
        except (OSError, UnicodeError):
            pass
        finally:
            with self.lock:
                self.clients.pop(sock, None)
            sock.close()
            if registered:
                print(f'{client.name} left', flush=True)
                self.broadcast(f'SYSTEM {client.name} вышел из чата')


def main():
    args = arguments('TCP multiuser chat server', 9004)
    chat = Chat()
    with listener(args.host, args.port) as server:
        try:
            while True:
                sock, _ = server.accept()
                threading.Thread(target=chat.handle, args=(sock,), daemon=True).start()
        finally:
            with chat.lock:
                clients = list(chat.clients)
            for sock in clients:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
