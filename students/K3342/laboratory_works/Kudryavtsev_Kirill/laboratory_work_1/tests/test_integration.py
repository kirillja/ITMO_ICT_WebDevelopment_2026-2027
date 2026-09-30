"""Интеграционные проверки настоящих серверов на свободных TCP/UDP-портах."""
from contextlib import contextmanager
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import urlencode
ROOT = Path(__file__).resolve().parents[1]

@contextmanager
def server(module, *extra):
    p = subprocess.Popen([sys.executable, '-u', '-m', module, '--port', '0', *extra], cwd=ROOT,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        line = p.stdout.readline()
        if not line.startswith('Listening on '):
            raise RuntimeError(line + p.stderr.read())
        yield int(line.rsplit(':', 1)[1]), p
    finally:
        p.terminate()
        try: p.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill(); p.communicate()

def connect(port):
    return socket.create_connection(('127.0.0.1', port), timeout=3)

def http(port, raw, fragmented=False):
    with connect(port) as sock:
        for chunk in ([raw[i:i+7] for i in range(0, len(raw), 7)] if fragmented else [raw]):
            sock.sendall(chunk)
        data = bytearray()
        while chunk := sock.recv(4096): data.extend(chunk)
    head, body = bytes(data).split(b'\r\n\r\n', 1)
    lines = head.decode().split('\r\n')
    fields = dict(line.split(': ', 1) for line in lines[1:])
    assert int(fields['Content-Length']) == len(body), 'Неверная длина HTTP-тела'
    return int(lines[0].split()[1]), fields, body

def post(subject, grade):
    body = urlencode({'subject': subject, 'grade': grade}).encode()
    return (b'POST /grades HTTP/1.1\r\nContent-Type: application/x-www-form-urlencoded\r\n'
            + f'Content-Length: {len(body)}\r\n\r\n'.encode() + body)

class IntegrationTests(unittest.TestCase):
    def test_udp_exchange(self):
        with server('task1.server') as (port, p):
            r = subprocess.run([sys.executable, '-m', 'task1.client', '--port', str(port)], cwd=ROOT,
                               capture_output=True, text=True, timeout=5)
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout.strip(), 'Hello, client')
            self.assertEqual(p.stdout.readline().strip(), 'Hello, server')

    def test_tcp_calculation_and_keyboard(self):
        with server('task2.server') as (port, _):
            with connect(port) as sock:
                for byte in b'{"a":3,"b":4}\n': sock.sendall(bytes([byte]))
                with sock.makefile('rb') as f:
                    self.assertEqual(json.loads(f.readline())['result']['c'], 5)
            r = subprocess.run([sys.executable, '-m', 'task2.client', '--port', str(port)], cwd=ROOT,
                               input='-1\n3\n4\n', capture_output=True, text=True, timeout=5)
            self.assertEqual(r.returncode, 0)
            self.assertIn('Гипотенуза c = 5', r.stdout)
            for raw in [b'{"a":0,"b":4}\n', b'{"a":NaN,"b":4}\n', b'[]\n', b'bad\n']:
                with connect(port) as sock:
                    sock.sendall(raw)
                    with sock.makefile('rb') as f: self.assertFalse(json.loads(f.readline())['ok'])

    def test_static_html(self):
        with server('task3.server') as (port, _):
            status, headers, body = http(port, b'GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
            self.assertEqual(status, 200)
            self.assertEqual(body, (ROOT/'task3/index.html').read_bytes())
            self.assertIn('charset=utf-8', headers['Content-Type'])
            self.assertEqual(http(port, b'GET /missing HTTP/1.1\r\n\r\n')[0], 404)
            self.assertEqual(http(port, b'PUT / HTTP/1.1\r\n\r\n')[0], 405)

    def test_chat_three_users_duplicate_name_messages_exit(self):
        with server('task4.server') as (port, _):
            socks, streams = [], []
            try:
                for name in ['Alice', 'Bob', 'Кирилл']:
                    s = connect(port); f = s.makefile('rb')
                    self.assertTrue(f.readline().startswith(b'NAME '))
                    s.sendall((name+'\n').encode())
                    self.assertTrue(f.readline().startswith(b'OK '))
                    socks.append(s); streams.append(f)
                    for old in streams[:-1]: self.assertIn('вошёл', old.readline().decode())
                with connect(port) as s:
                    with s.makefile('rb') as f:
                        f.readline(); s.sendall(b'alice\n')
                        self.assertTrue(f.readline().startswith(b'ERROR '))
                socks[0].sendall('Первое\nВторое\n'.encode())
                for f in streams[1:]:
                    self.assertEqual(f.readline().decode().strip(), 'MSG Alice: Первое')
                    self.assertEqual(f.readline().decode().strip(), 'MSG Alice: Второе')
                socks[1].sendall(b'/quit\n')
                self.assertTrue(streams[1].readline().startswith(b'BYE '))
                for i in (0, 2): self.assertIn('Bob вышел', streams[i].readline().decode())
                with connect(port) as s:
                    with s.makefile('rb') as f:
                        f.readline(); s.sendall(b'Bob\n')
                        self.assertTrue(f.readline().startswith(b'OK '))
            finally:
                for s in socks:
                    try: s.shutdown(socket.SHUT_RDWR)
                    except OSError: pass
                for f in streams: f.close()
                for s in socks: s.close()

    def test_gradebook_grouping_errors_escaping_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'grades.json'
            with server('task5.server', '--data', str(path)) as (port, _):
                self.assertEqual(http(port, b'GET / HTTP/1.1\r\n\r\n')[0], 200)
                self.assertEqual(http(port, post('Математика', 5), True)[0], 303)
                self.assertEqual(http(port, post('Математика', 4))[0], 303)
                self.assertEqual(json.loads(path.read_text()), {'Математика': [5, 4]})
                for subject, grade in [('', 5), ('Математика', 6)]:
                    self.assertEqual(http(port, post(subject, grade))[0], 400)
                for raw, status in [(b'POST /grades HTTP/1.1\r\n\r\n',411),
                                    (b'POST /grades HTTP/1.1\r\nContent-Length: 999999\r\n\r\n',413),
                                    (b'GET / HTTP/1.1\r\nContent-Length: -1\r\n\r\n',400),
                                    (b'GET /missing HTTP/1.1\r\n\r\n',404)]:
                    self.assertEqual(http(port, raw)[0], status)
                self.assertEqual(http(port, post('<script>alert(1)</script>', 3))[0], 303)
                body = http(port, b'GET /grades HTTP/1.1\r\n\r\n')[2].decode()
                self.assertIn('&lt;script&gt;', body)
                self.assertNotIn('<script>', body)
                self.assertEqual(body.count('<td>Математика</td>'), 1)
            with server('task5.server', '--data', str(path)) as (port, _):
                self.assertIn('5, 4', http(port, b'GET /grades HTTP/1.1\r\n\r\n')[2].decode())

if __name__ == '__main__': unittest.main(verbosity=2)
