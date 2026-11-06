
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from num2words import num2words

from classifier.base import SkillDefinition, BaseSkill

from protocol import Response
from skills.base import SkillRequest

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

WEEKDAYS = [
    "понедельник",
    "вторник",
    "среда",
    "четверг",
    "пятница",
    "суббота",
    "воскресенье",
]

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
        ],

        priority=10,
    )

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