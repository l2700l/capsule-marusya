from __future__ import annotations

import asyncio
import logging
import re

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from classifier.base import SkillDefinition, BaseSkill
from classifier.util import SemanticMatcher
from protocol import Response
from skills.base import SkillRequest


logger = logging.getLogger(__name__)


class TranslationSkill(BaseSkill):
    definition = SkillDefinition(
        name="translation",
        rules=[
            r"\bкак будет\b",
            r"\bкак сказать\b",
            r"\bпереведи\b",
            r"\bперевод\b",
            r"\bпереведи фразу\b",
        ],
        examples=[
            "переведи hello на русский",
            "как будет спасибо по английски",
            "переведи эту фразу на немецкий",
            "переведи фразу",
            "переведи с",
        ],
        priority=10,
    )

    LANGUAGES = {
        "английский": "en",
        "английском": "en",
        "английски": "en",
        "русский": "ru",
        "русском": "ru",
        "русски": "ru",
        "немецкий": "de",
        "немецком": "de",
        "немецки": "de",
        "французский": "fr",
        "французском": "fr",
        "французски": "fr",
        "испанский": "es",
        "испанском": "es",
        "испански": "es",
    }

    LANGUAGE_NAMES = {
        "en": "английский",
        "ru": "русский",
        "de": "немецкий",
        "fr": "французский",
        "es": "испанский",
    }

    @staticmethod
    def translate_sync(source: str, target: str, phrase: str) -> str:
        if len(phrase.encode("utf-8")) > 500:
            raise ValueError("Translation text exceeds 500 bytes")

        params = urlencode({
            "q": phrase,
            "langpair": f"{source}|{target}",
            "mt": 1,
        })

        request = Request(
            f"https://api.mymemory.translated.net/get?{params}",
            headers={
                "User-Agent": "CapsuleMarusya/1.0",
            },
        )

        with urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))

        if data.get("quotaFinished"):
            raise RuntimeError("MyMemory daily quota exceeded")

        if data.get("responseStatus") != 200:
            raise RuntimeError(
                data.get("responseDetails", "Translation failed")
            )

        result = data.get("responseData", {}).get("translatedText")

        if not result:
            raise RuntimeError("Empty translation result")

        return result

    @staticmethod
    def detect_source(text: str) -> str:
        """
        Простая эвристика для определения исходного языка.
        Кириллица -> русский, латиница -> английский.
        """
        cyrillic = len(re.findall(r"[а-яё]", text, re.IGNORECASE))
        latin = len(re.findall(r"[a-z]", text, re.IGNORECASE))

        if cyrillic > latin:
            return "ru"

        return "en"

    def parse_request(self, text: str):
        target = None
        source = None

        # Определяем целевой язык:
        # "на английский", "по-английски" и т.д.
        target_pattern = (
            r"(?:на|по-)"
            r"(английский|английском|английски|"
            r"русский|русском|русски|"
            r"немецкий|немецком|немецки|"
            r"французский|французском|французски|"
            r"испанский|испанском|испански)"
        )

        target_match = re.search(target_pattern, text)

        if target_match:
            target = self.LANGUAGES[target_match.group(1)]
            text = text[:target_match.start()] + text[target_match.end():]

        # Определяем явно указанный исходный язык:
        # "с английского", "с русского" и т.д.
        source_pattern = (
            r"\bс\s+"
            r"(английского|русского|немецкого|французского|испанского)\b"
        )

        source_languages = {
            "английского": "en",
            "русского": "ru",
            "немецкого": "de",
            "французского": "fr",
            "испанского": "es",
        }

        source_match = re.search(source_pattern, text)

        if source_match:
            source = source_languages[source_match.group(1)]
            text = text[:source_match.start()] + text[source_match.end():]

        # Убираем команды и вводные фразы, оставляя сам текст.
        text = re.sub(
            r"^\s*(?:"
            r"переведи|перевести|перевод|"
            r"как будет|как сказать"
            r")\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"^\s*(?:эту\s+)?(?:фразу|слово|текст)\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = text.strip(" \t\n.,!?«»\"'")

        return text, source, target

    async def handle(self, request: SkillRequest):
        text = request.text.strip().lower().replace("ё", "е")

        response = Response(
            skill="translation",
            intent="translation",
            asr_text=text,
        )

        phrase, source, target = self.parse_request(text)

        if not target:
            return response.say(
                "На какой язык перевести?"
            )

        if not phrase:
            return response.say(
                "Какую фразу перевести?"
            )

        if not source:
            source = self.detect_source(phrase)

        if source == target:
            return response.say(
                f"Это уже {self.LANGUAGE_NAMES[target]} язык."
            )

        try:
            result = await asyncio.to_thread(
                self.translate_sync,
                source,
                target,
                phrase,
            )

            if not result:
                return response.say("Не удалось получить перевод.")

            return response.say(str(result))

        except Exception:
            logger.exception("Translation failed")
            return response.say("Не удалось выполнить перевод.")


SKILL = TranslationSkill.definition
SKILL.handler = TranslationSkill().handle