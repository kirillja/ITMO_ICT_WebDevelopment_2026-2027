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
