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
