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
