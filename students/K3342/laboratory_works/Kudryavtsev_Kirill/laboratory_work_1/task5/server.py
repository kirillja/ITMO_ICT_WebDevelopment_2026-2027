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
