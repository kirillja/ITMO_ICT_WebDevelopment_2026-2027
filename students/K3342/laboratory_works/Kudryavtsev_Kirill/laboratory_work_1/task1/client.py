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
