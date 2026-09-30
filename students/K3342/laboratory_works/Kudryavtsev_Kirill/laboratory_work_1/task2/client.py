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
