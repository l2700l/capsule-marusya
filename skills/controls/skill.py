from __future__ import annotations

import re

import httpx

from config.settings import SERVER_URL
from classifier.base import SkillDefinition, BaseSkill
from classifier.util import SemanticMatcher
from protocol import Response
from skills.base import SkillRequest
from utils.num_parser import extract_numbers

GENERAL_SETTINGS_URL = f"{SERVER_URL}/device/settings/v1/id/general"


CONTROL_INTENTS = {
    "volume_up": [
        "сделай громче",
        "прибавь громкость",
        "увеличь громкость",
        "громче",
    ],
    "volume_down": [
        "сделай тише",
        "уменьши громкость",
        "убавь громкость",
        "тише",
    ],
    "volume_set": [
        "установи громкость на 30",
        "громкость 3",
        "громкость 50",
        "поставь громкость на максимум",
        "сделай громкость 70",
    ],
    "next": [
        "следующий",
        "следующий трек",
        "переключи на следующий",
        "включи следующую песню",
    ],
    "previous": [
        "предыдущий",
        "предыдущий трек",
        "переключи на предыдущий",
        "верни предыдущую песню",
    ],
    "pause": [
        "пауза",
        "поставь на паузу",
        "останови музыку",
        "выключи музыку",
        "стоп",
        "замолчи",
        "заткнись",
        "молчи",
    ],
    "resume": [
        "продолжи",
        "продолжи воспроизведение",
        "включи обратно",
        "сними с паузы",
    ],
    "repeat": [
        "повтори",
        "включи повтор",
        "повторяй эту песню",
        "репит",
    ],
    "repeat_playlist": [
        "повторяй плейлист",
        "повтор всего плейлиста",
        "зацикли плейлист",
    ],
    "shuffle": [
        "перемешай музыку",
        "включи случайный порядок",
        "перемешай плейлист",
        "включи перемешивание",
    ],
    "rewind": [
        "перемотай назад",
        "перемотай песню в начало",
        "начни сначала",
    ],
}


class ControlsSkill(BaseSkill):
    definition = SkillDefinition(
        name="controls",
        rules=[
            r"\bгромкост\w*\b",
            r"\bсделай громче\b",
            r"\bсделай тише\b",
            r"\bвыключи музыку\b",
            r"\bостанови музыку\b",
            r"\bзаткнись\b",
            r"\bзамолчи\b",
            r"\bмолчи\b",
            r"\bследующ\w*\b",
            r"\bпредыдущ\w*\b",
            r"\bпереключи\b",
            r"\bпродолжи\b",
            r"\bвключи обратно\b",
            r"\bпауз\w*\b",
            r"\bрепит\b",
            r"\bповтор\w*\b",
            r"\bперемешай\b",
            r"\bслучайн\w*\s+поряд\w*\b",
            r"\bперемотай\b",
        ],
        examples=[
            example
            for examples in CONTROL_INTENTS.values()
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
                intents=CONTROL_INTENTS,
                threshold=0.55,
                margin=0.05,
            )
        return self.matcher

    async def get_volume(self) -> int:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(GENERAL_SETTINGS_URL)
            response.raise_for_status()

        data = response.json()
        settings = data["result"][0]

        return int(settings["master_volume"])

    async def set_volume(self, level: int) -> None:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.put(
                GENERAL_SETTINGS_URL+"/1",
                json={"master_volume": level},
            )
            response.raise_for_status()

    async def handle_volume(
        self,
        intent: str,
        text: str,
        response: Response,
    ):
        if intent == "volume_set":
            numbers = extract_numbers(text)

            if not numbers:
                return response.say("Укажи уровень громкости.")

            level = int(numbers[0])

            # Значения от 1 до 10 трактуем как шкалу 1–10.
            if 1 <= level <= 10:
                level *= 10

        else:
            current = await self.get_volume()

            if intent == "volume_up":
                level = current + 10
            else:
                level = current - 10

        level = max(0, min(100, level))

        await self.set_volume(level)

        return response.control("volume", level=level)

    async def handle(self, request: SkillRequest):
        text = request.text.strip()
        normalized = text.lower().replace("ё", "е")

        matcher = self.get_matcher(request)
        match = matcher.classify(normalized)

        if not match:
            return Response(
                skill="controls",
                intent="controls.unknown",
                asr_text=text,
            ).say("Не поняла, что нужно сделать.")

        intent = match["intent"]

        response = Response(
            skill="controls",
            intent=f"controls.{intent}",
            asr_text=text,
        )

        if intent.startswith("volume_"):
            try:
                return await self.handle_volume(intent, normalized, response)
            except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
                print(f"[ControlsSkill] Volume error: {exc}")
                return response.say("Не удалось изменить громкость.")

        actions = {
            "next": "next",
            "previous": "previous",
            "pause": "pause",
            "resume": "resume",
            "repeat": "repeat",
            "repeat_playlist": "repeat_playlist",
            "shuffle": "shuffle",
            "rewind": "rewind",
        }

        action = actions.get(intent)

        if action:
            return response.control(action)

        return response.say("Не удалось определить команду.")


SKILL = ControlsSkill.definition
SKILL.handler = ControlsSkill().handle