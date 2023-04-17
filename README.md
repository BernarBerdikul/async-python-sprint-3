# Работа с приложением

В папке `src` находятся файлы `server.py` и `client.py`.

Проект без интерфейса, все действия происходят в консоли.

### Для запуска сервера

Необходимо выполнить команду: `python server.py`

По дефолту сервер запускается на локальном хосте (`localhost`) на порту `8000`.
Также вместе с запуском сервера, создастся основной чат с названием `main`, куда будут добавлены все подключенные клиенты.

**Подробности ендпоинтов можно посмотреть ниже в выпадающем блоке `Список возможных методов для взаимодействия`.**

### Для запуска клиента

Необходимо выполнить команду: `python client.py`

Шаги по работе клиента:
1. Указать логин и пароль для подключения к серверу.
2. После подключения к серверу, будут доступны CLI команды по работе с сервером.
3. Для получения списка доступных чатов и данных их участников, необходимо ввести команду `status`.
4. Для отправки сообщения в общий чат, необходимо ввести команду `send` и написать сообщение.
В последующем сообщение добавиться в чат `main`.
5. Для отправки сообщения в приватный чат, необходимо ввести команду `send_to`, написать логин получателя и само сообщение. -
*Логин существующего пользователя можно посмотреть в списке участников чата, полученном в пункте 3.*
6. Для получения не просмотренных сообщений из чата, необходимо ввести команду `messages` и указать название чата. -
*Повторный вызов команды `messages` не вернет ранее просмотренные сообщения.*
7. Для завершения работы клиента, необходимо ввести команду `close`.

Пользователь может вернуться к работе с сервером, после перезапуска клиента и ввода ранее созданного логина и пароля.

Почему для получения сообщений из чата необходимо вводить постоянно команду `messages`? -
*В реальности пришлось бы делать веб-сокет или request polling на ендпоинт.*

# Проектное задание третьего спринта

Спроектируйте и реализуйте приложение для получения и обработки сообщений от клиента.

Кроме основного задания, выберите из списка дополнительные требования. У каждого требования есть определённая сложность, от которой зависит количество баллов. Необходимо выбрать такое количество заданий, чтобы общая сумма баллов была больше или равна `4`. Выбор заданий никак не ограничен: можно выбрать все простые или одно среднее и два простых, или одно продвинутое, или решить все.

## Описание задания

### `Сервер`

Реализовать сервис, который обрабатывает поступающие запросы от клиентов.

Условия и требования:
1. Подключенный клиент добавляется в «общий» чат, где находятся ранее подключенные клиенты.
2. После подключения новому клиенту доступны последние N cообщений из общего чата (20, по умолчанию).
3. Повторно подключенный клиент имеет возможность просмотреть все ранее непрочитанные сообщения до момента последнего опроса (как из общего чата, так и приватные).
4. По умолчанию сервер стартует на локальном хосте (127.0.0.1) и на 8000 порту (возможность задать любой).

<details>
<summary> Список возможных методов для взаимодействия </summary>

1. Подключиться к серверу и общему чату.

```python
POST /connect

# BODY
{
    "login": "<user_login>",
    "password": "<user_password>"
}
```

2. Получить статус и информацию о чатах.

```python
GET /status

# HEADERS
{
    "Authorization": "<user_token>"
}
```

3. Отправить сообщение в общий чат.

```python
POST /send

# HEADERS
{
    "Authorization": "<user_token>"
}

# BODY
{
    "message": "<message>"
}
```

4. Отправить сообщение определенному пользователю в приватный чат.

```python
POST /send_to

# HEADERS
{
    "Authorization": "<user_token>"
}

# BODY
{
    "user_login": "<user_login>",
    "message": "<message>"
}
```

5. Получить до 20 не просмотренных сообщений из определенного чата.

```python
POST /chats/<chat_name>/messages

# HEADERS
{
    "Authorization": "user_token"
}
```
</details>


### `Клиент`

Реализовать сервис, который умеет подключаться к серверу для обмена сообщениями с другими клиентами.

Условия и требования:
1. После подключения клиент может отправлять сообщения в «общий» чат.
2. Возможность отправки сообщения в приватном чате (1-to-1) любому участнику из общего чата.


### Дополнительные требования (отметить [Х] выбранные пункты):

- [ ] (1 балл) Период жизни доставленных сообщений — 1 час (по умолчанию).
- [ ] (1 балл) Клиент может отправлять не более 20 (по умолчанию) сообщений в общий чат в течение определенного периода — 1 час (по умолчанию). В конце каждого периода лимит обнуляется.
- [ ] (1 балл) Возможность комментировать сообщения.
- [ ] (2 балла) Возможность создавать сообщения с заранее указанным временем отправки; созданные, но не отправленные сообщения можно отменить.
- [ ] (2 балла) Возможность пожаловаться на пользователя. При достижении лимита в 3 предупреждения, пользователь становится «забанен» — невозможность отправки сообщений в течение 4 часов (по умолчанию).
- [ ] (3 балла) Возможность отправлять файлы различного формата (объёмом не более 5Мб, по умолчанию).
- [ ] (3 балла) Возможность создавать кастомные приватные чаты и приглашать в него других пользователей. Неприглашенный пользователь может «войти» в такой чат только по сгенерированной ссылке и после подтверждения владельцем чата.
- [ ] (4 балла) Пользователь может подключиться с двух и более клиентов одновременно. Состояния должны синхронизироваться между клиентами.
- [X] **(5 баллов) Реализовать кастомную реализацию для взаимодействия по протоколу `http` (можно использовать `asyncio.streams`);


## Требования к решению

1. Опишите документацию по разработанному API.
2. Используйте концепции ООП.
3. Используйте аннотацию типов.
4. Предусмотрите обработку исключительных ситуаций.
5. Приведите стиль кода в соответствие pep8, flake8, mypy.
6. Логируйте результаты действий.
7. Покройте написанный код тестами.


## Рекомендации к решению

1. Можно использовать внешние библиотеки, но не фреймворки (описать в **requirements.txt**).
2. Можно не проектировать БД: информацию хранить в памяти и/или десериализовать/сериализировать в файл (формат на выбор) и восстанавливать при старте сервера.
3. Нет необходимости разрабатывать UI для клиента: можно выводить информацию в консоль или использовать лог-файлы.
4. API может быть, как вызов по команде/флагу для консольного приложения или эндпойнт для http-сервиса.
