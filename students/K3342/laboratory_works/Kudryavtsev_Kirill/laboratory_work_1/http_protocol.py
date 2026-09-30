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
