# Исходный код лабораторной

Полные тексты клиента и сервера для всех пяти заданий.

## common

Файл `common.py`.

```python
"""Общие настройки адреса и сокета для учебных серверов."""
import argparse
import socket


def arguments(description, port):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=port)
    return parser.parse_args()


def listener(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(20)
    print(f'Listening on {host}:{sock.getsockname()[1]}', flush=True)
    return sock
```

## http_protocol

Файл `http_protocol.py`.

```python
"""Минимальный HTTP/1.x поверх socket, без http.server и веб-фреймворков."""
MAX_HEADERS = 16384
MAX_BODY = 65536
REASONS = {200: 'OK', 303: 'See Other', 400: 'Bad Request', 404: 'Not Found',
           405: 'Method Not Allowed', 408: 'Request Timeout', 411: 'Length Required',
           413: 'Content Too Large', 415: 'Unsupported Media Type', 500: 'Internal Server Error'}


class HTTPError(ValueError):
    def __init__(self, status, message):
        self.status = status
        super().__init__(message)


def read_request(conn):
    data = bytearray()
    while b'\r\n\r\n' not in data:
        chunk = conn.recv(4096)
        if not chunk:
            raise HTTPError(400, 'Неполные заголовки')
        data.extend(chunk)
        if len(data.split(b'\r\n\r\n', 1)[0]) > MAX_HEADERS:
            raise HTTPError(413, 'Слишком большие заголовки')
    raw_headers, body = bytes(data).split(b'\r\n\r\n', 1)
    try:
        lines = raw_headers.decode('iso-8859-1').split('\r\n')
        method, target, version = lines[0].split(' ')
        if version not in ('HTTP/1.0', 'HTTP/1.1') or not target.startswith('/'):
            raise ValueError
        headers = {}
        for line in lines[1:]:
            name, value = line.split(':', 1)
            name = name.strip().lower()
            if not name or name in headers:
                raise ValueError
            headers[name] = value.strip()
        if 'transfer-encoding' in headers:
            raise HTTPError(400, 'Transfer-Encoding не поддерживается')
        if method == 'POST' and 'content-length' not in headers:
            raise HTTPError(411, 'Нужен Content-Length')
        length_text = headers.get('content-length', '0')
        if not length_text.isascii() or not length_text.isdecimal():
            raise ValueError
        length = int(length_text)
        if length > MAX_BODY:
            raise HTTPError(413, 'Слишком большое тело')
    except ValueError as error:
        if isinstance(error, HTTPError):
            raise
        raise HTTPError(400, 'Некорректный HTTP-запрос') from error
    while len(body) < length:
        chunk = conn.recv(min(4096, length - len(body)))
        if not chunk:
            raise HTTPError(400, 'Неполное тело запроса')
        body += chunk
    return method, target.split('?', 1)[0], headers, body[:length]


def send_response(conn, status, body=b'', extra_headers=None):
    if isinstance(body, str):
        body = body.encode('utf-8')
    headers = {'Content-Type': 'text/html; charset=utf-8', 'Content-Length': str(len(body)),
               'Connection': 'close'}
    headers.update(extra_headers or {})
    head = f'HTTP/1.1 {status} {REASONS[status]}\r\n'
    head += ''.join(f'{key}: {value}\r\n' for key, value in headers.items())
    conn.sendall(head.encode('ascii') + b'\r\n' + body)
```

## task1 server

Файл `task1/server.py`.

```python
import socket
from common import arguments


def main():
    args = arguments('UDP server', 9001)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((args.host, args.port))
        print(f'Listening on {args.host}:{sock.getsockname()[1]}', flush=True)
        while True:
            data, address = sock.recvfrom(4096)
            print(data.decode('utf-8', errors='replace'), flush=True)
            sock.sendto(b'Hello, client', address)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
```

## task1 client

Файл `task1/client.py`.

```python
import socket
from common import arguments


def main():
    args = arguments('UDP client', 9001)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(5)
        sock.connect((args.host, args.port))
        sock.send(b'Hello, server')
        print(sock.recv(4096).decode('utf-8'))


if __name__ == '__main__':
    try:
        main()
    except (OSError, UnicodeError) as error:
        raise SystemExit(f'Ошибка обмена: {error}')
```

## task2 server

Файл `task2/server.py`.

```python
"""Вариант 1: вычисление гипотенузы по двум катетам."""
import json
import math
import socket
from common import arguments, listener


def calculate(request):
    if not isinstance(request, dict):
        raise ValueError('Ожидается объект с катетами a и b')
    a, b = request.get('a'), request.get('b')
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in (a, b)):
        raise ValueError('Катеты должны быть числами')
    if not all(math.isfinite(x) and x > 0 for x in (a, b)):
        raise ValueError('Катеты должны быть положительными конечными числами')
    c = math.hypot(a, b)
    if not math.isfinite(c):
        raise ValueError('Результат слишком велик')
    return {'a': a, 'b': b, 'c': c}


def serve_connection(conn):
    conn.settimeout(5)
    try:
        with conn.makefile('rb') as stream:
            line = stream.readline(4097)
        if not line.endswith(b'\n') or len(line) > 4096:
            raise ValueError('Запрос должен быть строкой JSON длиной до 4096 байт')
        result = calculate(json.loads(line))
        response = {'ok': True, 'result': result}
    except (ValueError, OverflowError, socket.timeout) as error:
        response = {'ok': False, 'error': str(error)}
    conn.sendall((json.dumps(response, ensure_ascii=False, allow_nan=False) + '\n').encode())


def main():
    args = arguments('TCP Pythagoras server', 9002)
    with listener(args.host, args.port) as server:
        while True:
            conn, _ = server.accept()
            with conn:
                try:
                    serve_connection(conn)
                except OSError:
                    pass


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
```

## task2 client

Файл `task2/client.py`.

```python
import json
import math
import socket
from common import arguments


def positive_number(prompt):
    while True:
        try:
            value = float(input(prompt).replace(',', '.'))
            if math.isfinite(value) and value > 0:
                return value
        except ValueError:
            pass
        print('Введите положительное конечное число.')


def main():
    args = arguments('TCP Pythagoras client', 9002)
    a = positive_number('Первый катет a: ')
    b = positive_number('Второй катет b: ')
    with socket.create_connection((args.host, args.port), timeout=5) as sock:
        sock.sendall((json.dumps({'a': a, 'b': b}) + '\n').encode())
        with sock.makefile('rb') as stream:
            response = json.loads(stream.readline(4097))
    if response['ok']:
        print(f"Гипотенуза c = {response['result']['c']:g}")
    else:
        print(f"Ошибка сервера: {response['error']}")


if __name__ == '__main__':
    try:
        main()
    except (OSError, EOFError, ValueError) as error:
        raise SystemExit(f'Ошибка: {error}')
```

## task3 server

Файл `task3/server.py`.

```python
from pathlib import Path
import socket
from common import arguments, listener
from http_protocol import HTTPError, read_request, send_response

PAGE = Path(__file__).with_name('index.html')


def handle(conn):
    try:
        method, path, _, _ = read_request(conn)
        if method != 'GET':
            send_response(conn, 405, 'Используйте GET', {'Allow': 'GET'})
        elif path not in ('/', '/index.html'):
            send_response(conn, 404, 'Страница не найдена')
        else:
            send_response(conn, 200, PAGE.read_bytes())
    except HTTPError as error:
        send_response(conn, error.status, str(error))
    except socket.timeout:
        send_response(conn, 408, 'Время ожидания истекло')
    except OSError:
        pass


def main():
    args = arguments('Static HTTP socket server', 9003)
    with listener(args.host, args.port) as server:
        while True:
            conn, _ = server.accept()
            with conn:
                conn.settimeout(5)
                try:
                    handle(conn)
                except OSError:
                    pass


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
```

## task3 index

Файл `task3/index.html`.

```html
<!doctype html>
<html lang="ru"><meta charset="utf-8"><title>ЛР1 — HTTP на сокетах</title>
<body><h1>HTML из файла index.html</h1>
<p>Кирилл Кудрявцев. Группа К3342.</p>
<p>Эту страницу отправляет сервер на Python через TCP-сокет.</p></body></html>
```

## task4 server

Файл `task4/server.py`.

```python
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
```

## task4 client

Файл `task4/client.py`.

```python
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
```

## task5 server

Файл `task5/server.py`.

```python
"""HTTP-журнал: dict[str, list[int]], сохраняемый в JSON."""
import argparse
from html import escape
import json
from pathlib import Path
import socket
from urllib.parse import parse_qs
from common import listener
from http_protocol import HTTPError, read_request, send_response


class Gradebook:
    def __init__(self, path):
        self.path = Path(path)
        self.grades = json.loads(self.path.read_text('utf-8')) if self.path.exists() else {}
        if not isinstance(self.grades, dict) or any(
            not isinstance(k, str) or not isinstance(v, list) or
            any(type(g) is not int or g not in range(1, 6) for g in v)
            for k, v in self.grades.items()
        ):
            raise ValueError('Некорректный файл журнала')

    def add(self, subject, grade):
        updated = {key: list(value) for key, value in self.grades.items()}
        updated.setdefault(subject, []).append(grade)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + '.tmp')
        temporary.write_text(json.dumps(updated, ensure_ascii=False, indent=2), 'utf-8')
        temporary.replace(self.path)
        self.grades = updated

    def page(self):
        rows = ''.join(
            f'<tr><td>{escape(subject)}</td><td>{", ".join(map(str, grades))}</td></tr>'
            for subject, grades in sorted(self.grades.items())
        ) or '<tr><td colspan="2">Оценок пока нет</td></tr>'
        return f'''<!doctype html><html lang="ru"><meta charset="utf-8">
<title>Журнал оценок</title><style>body{{font:18px system-ui;max-width:900px;margin:40px auto;padding:0 20px}}td,th{{padding:12px;border:1px solid #ccc}}table{{border-collapse:collapse;width:100%}}label{{display:block;margin:12px 0}}button{{padding:10px}}</style>
<h1>Журнал оценок по дисциплинам</h1><table><thead><tr><th>Дисциплина</th><th>Оценки</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Добавить оценку</h2><form action="/grades" method="post">
<label>Дисциплина <input name="subject" maxlength="100" required></label>
<label>Оценка <input name="grade" type="number" min="1" max="5" required></label>
<button type="submit">Сохранить</button></form></html>'''


def handle(conn, book):
    try:
        method, path, headers, body = read_request(conn)
        if path not in ('/', '/grades'):
            send_response(conn, 404, 'Страница не найдена')
        elif method == 'GET':
            send_response(conn, 200, book.page())
        elif method == 'POST' and path == '/grades':
            if headers.get('content-type', '').split(';')[0].strip().lower() != 'application/x-www-form-urlencoded':
                raise HTTPError(415, 'Нужна HTML-форма application/x-www-form-urlencoded')
            try:
                form = parse_qs(body.decode('utf-8'), keep_blank_values=True,
                                encoding='utf-8', errors='strict', max_num_fields=10)
                if set(form) != {'subject', 'grade'} or any(len(v) != 1 for v in form.values()):
                    raise ValueError
                subject = form['subject'][0].strip()
                grade = int(form['grade'][0])
                if not 1 <= len(subject) <= 100 or grade not in range(1, 6):
                    raise ValueError
            except (ValueError, UnicodeError) as error:
                raise HTTPError(400, 'Укажите дисциплину (1–100 символов) и оценку от 1 до 5') from error
            try:
                book.add(subject, grade)
            except OSError as error:
                raise HTTPError(500, 'Не удалось сохранить журнал') from error
            send_response(conn, 303, extra_headers={'Location': '/grades'})
        else:
            send_response(conn, 405, 'Метод не поддерживается', {'Allow': 'GET, POST' if path == '/grades' else 'GET'})
    except HTTPError as error:
        send_response(conn, error.status, escape(str(error)))
    except socket.timeout:
        send_response(conn, 408, 'Время ожидания истекло')
    except OSError:
        pass


def main():
    parser = argparse.ArgumentParser(description='Socket HTTP gradebook')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=9005)
    parser.add_argument('--data', type=Path, default=Path(__file__).with_name('grades.json'))
    args = parser.parse_args()
    book = Gradebook(args.data)
    with listener(args.host, args.port) as server:
        while True:
            conn, _ = server.accept()
            with conn:
                conn.settimeout(5)
                try:
                    handle(conn, book)
                except OSError:
                    pass


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
```
