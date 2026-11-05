
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from num2words import num2words

from classifier.base import SkillDefinition, BaseSkill
from classifier.util import SemanticMatcher

from protocol import Response
from skills.base import SkillRequest
from skills.time.events import EVENTS

from config.settings import TIMEZONE_NAME


MONTHS_GENITIVE = [
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
]


def format_date(now: datetime) -> str:
    day = num2words(now.day, lang="ru", to="ordinal")
    year = num2words(now.year, lang="ru", to="ordinal")

    return (
        f"Сегодня {day} {MONTHS_GENITIVE[now.month - 1]} "
        f"{year} года"
    )

MONTHS = {
    "января": 1, "январь": 1,
    "февраля": 2, "февраль": 2,
    "марта": 3, "март": 3,
    "апреля": 4, "апрель": 4,
    "мая": 5, "май": 5,
    "июня": 6, "июнь": 6,
    "июля": 7, "июль": 7,
    "августа": 8, "август": 8,
    "сентября": 9, "сентябрь": 9,
    "октября": 10, "октябрь": 10,
    "ноября": 11, "ноябрь": 11,
    "декабря": 12, "декабрь": 12,
}


EVENT_DATES = {
    "new_year": (1, 1),
    "christmas": (1, 7),
    "defender_day": (2, 23),
    "womens_day": (3, 8),
    "cosmonautics_day": (4, 12),
    "victory_day": (5, 9),
    "russia_day": (6, 12),
    "knowledge_day": (9, 1),
    "halloween": (10, 31),
    "unity_day": (11, 4),
}


WEEKDAYS = [
    "понедельник",
    "вторник",
    "среда",
    "четверг",
    "пятница",
    "суббота",
    "воскресенье",
]


def extract_target_text(text: str) -> str:
    text = text.lower().replace("ё", "е").strip()

    text = re.sub(
        r"^.*?\bдо\b\s*",
        "",
        text,
        count=1,
    )

    text = re.sub(
        r"^через\s+сколько\s+",
        "",
        text,
    )

    text = re.sub(
        r"^(?:наступит|будет|придет|настанет)\s+",
        "",
        text,
    )

    return text.strip(" ?!.,") 


def parse_target(text: str, now: datetime) -> datetime | None:
    text = extract_target_text(text)

    if not text:
        return None

    # Послезавтра
    if re.search(r"\bпослезавтра\b", text):
        return (now + timedelta(days=2)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    # Завтра
    if re.search(r"\bзавтра\b", text):
        return (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    # Конец года
    if re.search(r"\bконца года\b", text):
        return now.replace(
            year=now.year + 1,
            month=1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

    # Время: 18:30 или 18.30
    time_match = re.search(
        r"\b(\d{1,2})[:.](\d{2})\b",
        text,
    )

    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2))

        if hour > 23 or minute > 59:
            return None

        target = now.replace(
            hour=hour,
            minute=minute,
            second=0,
            microsecond=0,
        )

        if target <= now:
            target += timedelta(days=1)

        return target

    # Время: 18 часов / 18 часов 30 минут
    time_match = re.search(
        r"\b(\d{1,2})\s*(?:час(?:ов|а)?|ч)"
        r"(?:\s*(\d{1,2})\s*минут(?:ы|у)?)?",
        text,
    )

    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)

        if hour > 23 or minute > 59:
            return None

        target = now.replace(
            hour=hour,
            minute=minute,
            second=0,
            microsecond=0,
        )

        if target <= now:
            target += timedelta(days=1)

        return target

    # Дата: 15.11 или 15.11.2027
    date_match = re.search(
        r"\b(\d{1,2})[./](\d{1,2})(?:[./](\d{4}))?\b",
        text,
    )

    if date_match:
        day = int(date_match.group(1))
        month = int(date_match.group(2))
        year = int(date_match.group(3) or now.year)
        explicit_year = date_match.group(3) is not None

    else:
        # Дата: 15 ноября
        date_match = re.search(
            r"\b(\d{1,2})\s+([а-яё]+)(?:\s+(\d{4}))?\b",
            text,
        )

        if not date_match:
            return None

        day = int(date_match.group(1))
        month = MONTHS.get(date_match.group(2))

        if month is None:
            return None

        year = int(date_match.group(3) or now.year)
        explicit_year = date_match.group(3) is not None

    try:
        target = now.replace(
            year=year,
            month=month,
            day=day,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
    except ValueError:
        return None

    if not explicit_year and target <= now:
        try:
            target = target.replace(year=year + 1)
        except ValueError:
            return None

    return target


def plural(value: int, forms: tuple[str, str, str]) -> str:
    n = abs(value) % 100

    if 11 <= n <= 19:
        form = forms[2]
    elif n % 10 == 1:
        form = forms[0]
    elif 2 <= n % 10 <= 4:
        form = forms[1]
    else:
        form = forms[2]

    return f"{value} {form}"


def format_remaining(delta: timedelta) -> str:
    total_minutes = int(delta.total_seconds() // 60)

    if total_minutes <= 0:
        return "меньше минуты"

    days, remainder = divmod(total_minutes, 1440)
    hours, minutes = divmod(remainder, 60)

    parts = []

    if days:
        parts.append(plural(days, ("день", "дня", "дней")))

    if hours:
        parts.append(plural(hours, ("час", "часа", "часов")))

    if minutes:
        parts.append(plural(minutes, ("минута", "минуты", "минут")))

    return " ".join(parts)
def format_time(now: datetime) -> str:
    hour = plural(now.hour, ("час", "часа", "часов"))
    minute = plural(now.minute, ("минута", "минуты", "минут"))

    return f"Сейчас {hour} {minute}"

class TimeSkill(BaseSkill):

    definition = SkillDefinition(
        name="time",

        rules=[
            r"\bкоторый час\b",
            r"\bсколько сейчас времени\b",
            r"\bкакое сегодня число\b",
            r"\bкакой сегодня день недели\b",
            r"\bтекущая дата\b",
            r"\bскажи точное время\b",
            r"\bкоторый час в\b",
            r"\bкакое сейчас время по\b",
            r"\bсколько сейчас времени в\b",
            r"\bсколько осталось до\b",
            r"\bчерез сколько\b",
        ],

        examples=[
            "Который час?",
            "Сколько сейчас времени?",
            "Какое сегодня число?",
            "Какой сегодня день недели?",
            "Текущая дата",
            "Скажи точное время",
            "Который час в Москве?",
            "Какое сейчас время по Лондону?",
            "Сколько сейчас времени в Токио?",
            "Сколько осталось до полуночи?",
            "Сколько осталось до Нового года?",
            "Сколько осталось до 18:30?",
            "Сколько осталось до 15 ноября?",
            "Сколько осталось до Рождества?",
            "Через сколько наступит Новый год?",
        ],

        priority=10,
    )

    def __init__(self):
        self.event_matcher = None

    def get_event_matcher(self, request: SkillRequest):
        if self.event_matcher is None:
            self.event_matcher = SemanticMatcher(
                model=request.semantic_model,
                intents=EVENTS,
                threshold=0.55,
                margin=0.05,
            )

        return self.event_matcher

    def resolve_event(
        self,
        text: str,
        now: datetime,
        request: SkillRequest,
    ) -> datetime | None:

        target_text = extract_target_text(text)

        result = self.get_event_matcher(request).classify(target_text)
        event_name = result["intent"]

        # Ежедневное событие: полночь
        if event_name == "midnight":
            target = now.replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )

            if target <= now:
                target += timedelta(days=1)

            return target

        # Ежегодные события
        if event_name not in EVENT_DATES:
            return None

        month, day = EVENT_DATES[event_name]

        try:
            target = now.replace(
                month=month,
                day=day,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
        except ValueError:
            return None

        if target <= now:
            try:
                target = target.replace(year=now.year + 1)
            except ValueError:
                return None

        return target

    async def handle(self, request: SkillRequest):

        text = request.text.strip()
        normalized = text.lower().replace("ё", "е")

        now = datetime.now(ZoneInfo(TIMEZONE_NAME))

        # Время в другом городе
        if re.search(
            r"\b(который час в|сколько сейчас времени в|какое сейчас время по)\b",
            normalized,
        ):
            return (
                Response(
                    skill="time",
                    intent="time.city",
                    asr_text=text,
                )
                .say("Пока я не умею определять время в других городах")
            )

        # Обратный отсчёт
        if re.search(
            r"\b(сколько осталось до|через сколько|осталось до)\b",
            normalized,
        ):
            # Сначала пробуем распознать конкретную дату или время
            target = parse_target(text, now)
            print(target)
            # Затем пробуем распознать именованное событие
            if target is None:
                target = self.resolve_event(text, now, request)
            (print(target))
            if target is None:
                return (
                    Response(
                        skill="time",
                        intent="time.countdown",
                        asr_text=text,
                    )
                    .say(
                        "Не совсем поняла, до какого события нужно посчитать время"
                    )
                )

            answer = format_remaining(target - now)

            return (
                Response(
                    skill="time",
                    intent="time.countdown",
                    asr_text=text,
                )
                .say(f"Осталось {answer}")
            )

        # Дата
        if re.search(
            r"\b(какое сегодня число|текущая дата)\b",
            normalized,
        ):
            return (
                Response(
                    skill="time",
                    intent="time.date",
                    asr_text=text,
                )
                .say(format_date(now))
            )

        # День недели
        if re.search(
            r"\b(какой сегодня день недели|какой сегодня день)\b",
            normalized,
        ):
            answer = "Сегодня " + WEEKDAYS[now.weekday()]

            return (
                Response(
                    skill="time",
                    intent="time.weekday",
                    asr_text=text,
                )
                .say(answer)
            )

        # Текущее время
        answer = format_time(now)

        return (
            Response(
                skill="time",
                intent="time.current",
                asr_text=text,
            )
            .say(answer)
        )


SKILL = TimeSkill.definition
SKILL.handler = TimeSkill().handle