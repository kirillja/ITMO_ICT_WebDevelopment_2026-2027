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
