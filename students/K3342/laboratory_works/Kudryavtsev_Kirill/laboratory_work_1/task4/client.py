import socket
import threading
from common import arguments


def receive(stream, stopped):
    try:
        while True:
            raw = stream.readline(8193)
            if not raw:
                print('Сервер закрыл соединение.', flush=True)
                break
            print(raw.decode('utf-8').rstrip(), flush=True)
            if raw.startswith(b'BYE '):
                break
    except (OSError, UnicodeError):
        print('Соединение прервано.', flush=True)
    finally:
        stopped.set()


def main():
    args = arguments('TCP chat client', 9004)
    with socket.create_connection((args.host, args.port), timeout=5) as sock:
        sock.settimeout(None)
        with sock.makefile('rb') as stream:
            print(stream.readline(8193).decode().rstrip())
            name = input('Имя: ').strip()
            sock.sendall((name + '\n').encode())
            answer = stream.readline(8193).decode().rstrip()
            print(answer)
            if not answer.startswith('OK '):
                return
            stopped = threading.Event()
            thread = threading.Thread(target=receive, args=(stream, stopped), daemon=True)
            thread.start()
            try:
                while not stopped.is_set():
                    text = input()
                    if len(text.encode()) > 4095:
                        print('Сообщение слишком длинное (до 4095 байт).')
                        continue
                    sock.sendall((text + '\n').encode())
                    if text.strip() == '/quit':
                        stopped.wait(2)
                        break
            except (EOFError, KeyboardInterrupt):
                if not stopped.is_set():
                    sock.sendall(b'/quit\n')
                    stopped.wait(2)
            finally:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                thread.join(timeout=2)


if __name__ == '__main__':
    try:
        main()
    except OSError as error:
        raise SystemExit(f'Ошибка соединения: {error}')
