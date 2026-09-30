# Проверки лабораторной

Проверено 30 сентября 2026 года на macOS, Python 3.13.0.
Все пять тестов запускают настоящие серверы на свободных локальных портах.

## Команда и результат

```sh
python3 -m unittest discover -s tests -v
```

```text
test_chat_three_users_duplicate_name_messages_exit (test_integration.IntegrationTests.test_chat_three_users_duplicate_name_messages_exit) ... ok
test_gradebook_grouping_errors_escaping_restart (test_integration.IntegrationTests.test_gradebook_grouping_errors_escaping_restart) ... ok
test_static_html (test_integration.IntegrationTests.test_static_html) ... ok
test_tcp_calculation_and_keyboard (test_integration.IntegrationTests.test_tcp_calculation_and_keyboard) ... ok
test_udp_exchange (test_integration.IntegrationTests.test_udp_exchange) ... ok

----------------------------------------------------------------------
Ran 5 tests in 0.272s

OK
```

## Что проверяется

| Задание | Проверки |
| --- | --- |
| UDP | Запуск серверного и клиентского скриптов, точные строки приветствия с обеих сторон |
| TCP | Запрос по одному байту, результат 5 для катетов 3 и 4, клавиатурный клиент, неверные данные |
| HTML | Тело равно index.html, длина в байтах, UTF-8, ответы 404 и 405 |
| Чат | Три подключения, запрет дубликата имени, две строки в одном TCP-пакете, выход и повторное использование имени |
| Журнал | GET и POST, запрос частями, одна запись с двумя оценками, неверный ввод, HTTP-ошибки, экранирование HTML, загрузка после перезапуска |

## Реальные примеры работы

Ниже вывод демонстрационного запуска, в котором для чата использованы три
реальных процесса `task4.client`. Ввод передавался через stdin; поэтому
подсказки ввода могут находиться на одной строке с ответом.

```text
UDP server: Hello, server
UDP client: Hello, client
TCP client: Первый катет a: Второй катет b: Гипотенуза c = 5
HTTP static: 200, Content-Length=330 bytes
<!doctype html>
<html lang="ru"><meta charset="utf-8"><title>ЛР1 — HTTP на сокетах</title>
<body><h1>HTML из файла index.html</h1>
<p>Кирилл Кудрявцев. Группа К3342.</p>
<p>Эту страницу отправляет сервер на Python через TCP-сокет.</p></body></html>
Alice: NAME Введите уникальное имя (1–32 символа):
Alice: Имя: OK Вы вошли как Alice. Выход: /quit
Bob: NAME Введите уникальное имя (1–32 символа):
Bob: Имя: OK Вы вошли как Bob. Выход: /quit
Chat: SYSTEM Bob вошёл в чат
Кирилл: NAME Введите уникальное имя (1–32 символа):
Кирилл: Имя: OK Вы вошли как Кирилл. Выход: /quit
Chat: SYSTEM Кирилл вошёл в чат
Chat: SYSTEM Кирилл вошёл в чат
Chat: MSG Alice: Привет всем
Chat: MSG Alice: Привет всем
Bob: BYE До встречи
Chat: SYSTEM Bob вышел из чата
Chat: SYSTEM Bob вышел из чата
POST Математика 5: 303
POST Математика 4: 303
GET /grades: 200
JSON storage: {"Математика": [5, 4]}
```

[Исходный лог проверок](../assets/tests.txt) и [лог примеров](../assets/demo.txt).
