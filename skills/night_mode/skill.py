
from __future__ import annotations

import re

import httpx

from config.settings import SERVER_URL
from classifier.base import SkillDefinition, BaseSkill
from classifier.util import SemanticMatcher
from protocol import Response
from skills.base import SkillRequest
from utils.num_parser import extract_numbers


NIGHT_MODE_URL = f"{SERVER_URL}/device/settings/v1/id/night_mode"


NIGHT_MODE_INTENTS = {
    "enable": [
        "включи ночной режим",
        "активируй ночной режим",
        "сделай ночной режим активным",
        "включи режим ночи",
        "ночной режим включи",
    ],
    "disable": [
        "выключи ночной режим",
        "отключи ночной режим",
        "деактивируй ночной режим",
        "убери ночной режим",
        "выключи режим ночи",
    ],
    "schedule_set": [
        "установи расписание ночного режима",
        "включай ночной режим с 23 до 7",
        "ночной режим с 22:00 до 8:00",
        "установи ночной режим с 23:30 до 9:00",
        "пусть ночной режим работает с 22 до 10",
        "измени время работы ночного режима",
        "перенеси начало ночного режима на 23 часа",
        "поставь расписание с 22 до 8",
    ],
    "schedule_remove": [
        "удали расписание ночного режима",
        "отмени расписание ночного режима",
        "отключи расписание",
        "убери расписание ночного режима",
        "не используй расписание ночного режима",
        "сбрось расписание ночного режима",
    ],
    "schedule_show": [
        "покажи расписание ночного режима",
        "какое расписание ночного режима",
        "когда включается ночной режим",
        "когда выключается ночной режим",
        "во сколько включается ночной режим",
        "во сколько заканчивается ночной режим",
    ],
}


TIME_PATTERN = re.compile(
    r"(?<!\d)(\d{1,2})(?::([0-5]\d))?(?!\d)"
)


class NightModeSkill(BaseSkill):
    definition = SkillDefinition(
        name="night_mode",
        rules=[
            r"\bночн\w*\s+режим\b",
            r"\bрежим\s+ноч\w*\b",
            r"\bрасписан\w*\b",
            r"\bночн\w*\s+час\w*\b",
        ],
        examples=[
            example
            for examples in NIGHT_MODE_INTENTS.values()
            for example in examples
        ],
        priority=10,
    )

    def __init__(self):
        self.matcher = None

    def get_matcher(self, request: SkillRequest):
        if self.matcher is None:
            self.matcher = SemanticMatcher(
                model=request.semantic_model,
                intents=NIGHT_MODE_INTENTS,
                threshold=0.55,
                margin=0.03,
            )
        return self.matcher

    async def get_settings(self) -> dict:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(NIGHT_MODE_URL)
            response.raise_for_status()

        data = response.json()
        return dict(data["result"][0])

    async def update_settings(self, patch: dict) -> dict:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.put(
                NIGHT_MODE_URL + "/1",
                json=patch,
            )
            response.raise_for_status()

        data = response.json()
        return dict(data["result"][0])

    @staticmethod
    def format_time(seconds: int) -> str:
        seconds = int(seconds)

        hour = (seconds // 3600) % 24
        minute = (seconds % 3600) // 60

        return f"{hour:02d}:{minute:02d}"

    @staticmethod
    def adjust_hour(hour: int, context: str) -> int:
        context = context.lower()

        if "вечер" in context or "дня" in context:
            if 1 <= hour <= 11:
                hour += 12

        elif "утр" in context:
            if hour == 12:
                hour = 0

        elif "ноч" in context:
            if hour == 12:
                hour = 0

        return hour

    @classmethod
    def parse_schedule_times(cls, text: str):
        matches = list(TIME_PATTERN.finditer(text))

        if len(matches) >= 2:
            result = []

            for match in matches[:2]:
                hour = int(match.group(1))
                minute = int(match.group(2) or 0)

                context = text[
                    max(0, match.start() - 15):
                    min(len(text), match.end() + 15)
                ]

                hour = cls.adjust_hour(hour, context)

                if not (0 <= hour <= 23):
                    return None

                result.append(hour * 3600 + minute * 60)

            return result

        # Запасной вариант: числа словами.
        numbers = extract_numbers(text)

        if len(numbers) >= 2:
            result = []

            parts = re.split(r"\bдо\b", text, maxsplit=1)

            for index, hour in enumerate(numbers[:2]):
                hour = int(hour)

                context = parts[index] if index < len(parts) else text
                hour = cls.adjust_hour(hour, context)

                if not (0 <= hour <= 23):
                    return None

                result.append(hour * 3600)

            return result

        return None

    async def handle_enable(
        self,
        response: Response,
    ):
        updated = await self.update_settings({
            "enabled": True,
        })

        return (
            response
            .night_mode(updated)
            .say("Ночной режим включен.")
        )

    async def handle_disable(
        self,
        response: Response,
    ):
        updated = await self.update_settings({
            "enabled": False,
        })

        return (
            response
            .night_mode(updated)
            .say("Ночной режим выключен.")
        )

    async def handle_schedule_set(
        self,
        text: str,
        response: Response,
    ):
        times = self.parse_schedule_times(text)

        if times is None:
            return response.say(
                "Укажи время начала и окончания ночного режима."
            )

        start_at, stop_at = times

        updated = await self.update_settings({
            "scheduled": True,
            "start_at": start_at,
            "stop_at": stop_at,
        })

        start = self.format_time(updated["start_at"])
        stop = self.format_time(updated["stop_at"])

        return (
            response
            .night_mode(updated)
            .say(
                f"Расписание ночного режима установлено: "
                f"с {start} до {stop}."
            )
        )

    async def handle_schedule_remove(
        self,
        response: Response,
    ):
        updated = await self.update_settings({
            "scheduled": False,
        })

        return (
            response
            .night_mode(updated)
            .say("Расписание ночного режима удалено.")
        )

    async def handle_schedule_show(
        self,
        response: Response,
    ):
        settings = await self.get_settings()

        if not settings.get("scheduled", False):
            return response.say(
                "Расписание ночного режима не задано."
            )

        start = self.format_time(settings["start_at"])
        stop = self.format_time(settings["stop_at"])

        status = (
            "включен"
            if settings.get("enabled", False)
            else "выключен"
        )

        return response.say(
            f"Ночной режим сейчас {status}. "
            f"По расписанию он работает с {start} до {stop}."
        )

    async def handle(self, request: SkillRequest):
        text = request.text.strip()
        normalized = text.lower().replace("ё", "е")

        matcher = self.get_matcher(request)
        match = matcher.classify(normalized)

        if not match:
            return Response(
                skill="night_mode",
                intent="night_mode.unknown",
                asr_text=text,
            ).say("Не поняла, что нужно сделать.")

        intent = match["intent"]

        response = Response(
            skill="night_mode",
            intent=f"night_mode.{intent}",
            asr_text=text,
        )

        handlers = {
            "enable": lambda: self.handle_enable(response),
            "disable": lambda: self.handle_disable(response),
            "schedule_set": lambda: self.handle_schedule_set(
                normalized, response
            ),
            "schedule_remove": lambda: self.handle_schedule_remove(
                response
            ),
            "schedule_show": lambda: self.handle_schedule_show(
                response
            ),
        }

        handler = handlers.get(intent)

        if handler is None:
            return response.say("Не удалось определить команду.")

        try:
            return await handler()

        except (
            httpx.HTTPError,
            KeyError,
            IndexError,
            TypeError,
            ValueError,
        ) as exc:
            print(f"[NightModeSkill] Error: {exc}")
            return response.say(
                "Не удалось изменить настройки ночного режима."
            )


SKILL = NightModeSkill.definition
SKILL.handler = NightModeSkill().handle
