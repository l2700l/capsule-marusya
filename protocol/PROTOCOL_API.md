# Protocol API: команды для VK Капсулы

Пакет строит JSON-ответы, в которых маруся передаёт колонке команды. Пакет описывает именно формат ответов навыков/команд для колонки.

## Быстрый пример

```python
from capsule_proxy.protocol import Response

response = (
    Response(
        skill="pretty_mode",
        intent="pretty_mode.on",
        asr_text="сделай ми ми ми",
    )
    .pretty_mode(True)
    .delay(300)
    .say("Посмотрим — вы на меня, а я на вас")
    .listen(
        min_waiting_time=4.0,
        forced_listen=True,
        listen_previous_intent="pretty_mode.on",
    )
)

payload = response.to_dict()  # обычный dict, готовый для JSON-ответа
```

Методы можно вызывать цепочкой. `commands` и `controls` сериализуются в отдельные массивы. `to_json()` возвращает JSON-строку.

## Примеры

```python
# Произнести текст
Response(skill="custom", intent="custom.hello").say("Привет!").to_dict()

# Вывести 4PDA на 15 секунд
Response(skill="custom", intent="custom.display").show_digits("4PDA", duration=15).to_dict()

# Включить радио (URL и обложка должны быть доступны колонке)
Response(skill="radio", intent="radio.play").play_radio(
    "https://example.com/radio.mp3",
    title="Радио",
    artist="Станция",
    cover_url="https://example.com/cover.jpg",
).to_dict()

# Пауза и установка громкости попадают в controls, а не commands
Response(skill="music", intent="music.pause").pause().set_volume(30).to_dict()

# Любая пока не обёрнутая команда
Response().raw_command("unknown_or_new_type", value=123).to_dict()
```

## Доступные методы

- Речь и последовательность: `say`, `delay`, `listen`.
- Экран: `show_digits(text)` или `add(led_digits_animation(...))`.
- Режимы устройства: `pretty_mode`, `bluetooth`, `light_demo`.
- Таймер: `start_timer(seconds)`, `cancel_timer()`.
- Медиа: `play_url`, `play_radio`.
- Контроллы: `next_track`, `previous_track`, `pause`, `resume`, `shuffle`, `set_volume`, `control`.
- Настройки: `settings`, `night_mode`, `alarm_settings`.
- Совместимость с будущими открытиями: `raw_command` и `add`.

## Важные оговорки

- `Response.to_dict()` возвращает полный конверт `{"qid": ..., "result": ...}`. В текущем `routes.invoke_route` поле `qid` словаря будет заменено новым UUID — это не мешает использованию API.
- `settings()` принимает полный объект настроек. Мы пока не считаем, что прошивка принимает частичные обновления.
- `play_url()` и `play_radio()` строят структуру `media` по известным примерам, но детали `stat_flags` и поведение разных источников ещё исследуются. Параметры можно переопределять.
- Для дисплея `brightness_for_text()` поддерживает только явно перечисленные символы. Неизвестный символ вызовет ошибку, а не будет молча отображён неверно.
- Это первая версия API: поля, которые не подтверждены захватами, не следует считать окончательно установленной спецификацией.

## Тесты

Из корня репозитория:

```bash
python3 -m unittest discover -s tests -v
```
