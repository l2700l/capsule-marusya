
from __future__ import annotations

import re
import uuid

from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo

import httpx

from config.settings import SERVER_URL
from classifier.base import SkillDefinition, BaseSkill
from classifier.util import SemanticMatcher
from protocol import Response
from skills.base import SkillRequest
from utils.num_parser import extract_numbers


ALARMS_URL = f"{SERVER_URL}/device/settings/v1/id/alarms"
GENERAL_SETTINGS_URL = f"{SERVER_URL}/device/settings/v1/id/general"

DIALOG_KEY = "alarms"


ALARM_INTENTS = {
    "list_alarm": [
        "какие будильники у меня стоят",
        "покажи мои будильники",
        "какие у меня есть будильники",
        "посмотреть будильники",
        "что у меня с будильниками",
    ],
    "set_alarm": [
        "поставь будильник",
        "заведи будильник",
        "разбуди меня в восемь",
        "поставь будильник на семь утра",
        "создай будильник на завтра",
        "поставь будильник на понедельник в восемь",
        "будильник каждый день на восемь",
        "будильник по будням в семь",
    ],
    "delete_alarm": [
        "удали будильник",
        "отмени будильник",
        "убери будильник на восемь",
        "удали будильник на завтра",
        "отмени будильник на понедельник",
    ],
    "delete_all_alarm": [
        "удали все будильники",
        "отключи все будильники",
        "отмени все будильники",
        "убери все будильники",
    ],
    "enable_alarm": [
        "включи будильник",
        "активируй будильник",
        "включи будильник на восемь",
    ],
    "disable_alarm": [
        "выключи будильник",
        "отключи будильник",
        "деактивируй будильник",
        "выключи будильник на восемь",
    ],
}


WEEKDAYS = {
    "понедельник": 1,
    "вторник": 2,
    "среду": 3,
    "среда": 3,
    "четверг": 4,
    "пятницу": 5,
    "пятница": 5,
    "субботу": 6,
    "суббота": 6,
    "воскресенье": 7,
    "воскресенье": 7,
}


class AlarmsSkill(BaseSkill):

    definition = SkillDefinition(
        name="alarm",
        rules=[
            r"\bбудильник\w*\b",
            r"\bразбуди\s+меня\b",
            r"\bбуди\s+меня\b",
        ],
        examples=[
            example
            for examples in ALARM_INTENTS.values()
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
                intents=ALARM_INTENTS,
                threshold=0.55,
                margin=0.03,
            )
        return self.matcher

    # --------------------------------------------------
    # API
    # --------------------------------------------------

    async def get_alarms(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(ALARMS_URL)
            response.raise_for_status()

        return response.json()["result"]

    async def add_alarm(self, alarm: dict) -> list[dict]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                ALARMS_URL,
                json=alarm,
            )
            response.raise_for_status()

        return response.json()["result"]

    async def update_alarm(
        self,
        alarm_id: str,
        changes: dict,
    ) -> list[dict]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.put(
                f"{ALARMS_URL}/{alarm_id}",
                json=changes,
            )
            response.raise_for_status()

        return response.json()["result"]

    async def delete_alarm(self, alarm_id: str) -> list[dict]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.delete(
                f"{ALARMS_URL}/{alarm_id}",
            )
            response.raise_for_status()

        return response.json()["result"]

    async def delete_all_alarms(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.delete(ALARMS_URL)
            response.raise_for_status()

        return response.json()["result"]

    async def get_timezone(self) -> ZoneInfo:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(GENERAL_SETTINGS_URL)
            response.raise_for_status()

        settings = response.json()["result"][0]
        return ZoneInfo(settings["timezone"])

    # --------------------------------------------------
    # Dialog helpers
    # --------------------------------------------------

    def get_dialog(self, request: SkillRequest) -> dict:
        return request.context.get(request.session_id).setdefault(DIALOG_KEY, {})

    def start_dialog(
        self,
        request: SkillRequest,
        state: dict,
    ):
        context = request.context.get(request.session_id)
        context[DIALOG_KEY] = state
        request.context.set_active_skill(
            request.session_id,
            self.definition.name,
        )

    def finish_dialog(self, request: SkillRequest):
        request.context.clear_active_skill(request.session_id)

    def ask(
        self,
        request: SkillRequest,
        intent: str,
        message: str,
    ):
        return (
            Response(
                skill="alarm_ds",
                intent=f"alarm_ds.{intent}",
                asr_text=request.text,
            )
            .say(message)
            .listen(
                min_waiting_time=0.0,
                forced_listen=True,
                listen_previous_intent=f"alarm_ds.{intent}",
            )
        )

    # --------------------------------------------------
    # Time parsing
    # --------------------------------------------------

    @staticmethod
    def parse_time(text: str):
        text = text.lower().replace("ё", "е")

        # Форматы 18:00, 8:30, 18.00
        match = re.search(
            r"(?<!\d)(\d{1,2})[:.](\d{2})(?!\d)",
            text,
        )

        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))

            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return hour, minute

            return None

        numbers = extract_numbers(text)

        if not numbers:
            return None

        hour = int(numbers[0])
        minute = int(numbers[1]) if len(numbers) > 1 else 0

        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
            return None

        # Например: восемь утра, восемь вечера.
        if "вечера" in text or "вечером" in text:
            if 1 <= hour <= 11:
                hour += 12

        elif "дня" in text or "днем" in text:
            if 1 <= hour <= 11:
                hour += 12

        elif "ночи" in text or "ночью" in text:
            if hour == 12:
                hour = 0

        elif "утра" in text or "утром" in text:
            if hour == 12:
                hour = 0

        return hour, minute

    @staticmethod
    def parse_weekdays(text: str):
        text = text.lower().replace("ё", "е")

        if re.search(r"\bкаждый день\b|\bежедневно\b", text):
            return list(range(1, 8))

        if re.search(r"\bпо будням\b|\bв будни\b", text):
            return [1, 2, 3, 4, 5]

        if re.search(r"\bпо выходным\b", text):
            return [6, 7]

        result = []

        for name, number in WEEKDAYS.items():
            if re.search(rf"\b{name}\b", text):
                result.append(number)

        return sorted(set(result))

    @staticmethod
    def parse_date(text: str, timezone: ZoneInfo):
        text = text.lower().replace("ё", "е")

        today = datetime.now(timezone).date()

        if "послезавтра" in text:
            return today + timedelta(days=2)

        if "завтра" in text:
            return today + timedelta(days=1)

        if "сегодня" in text:
            return today

        for name, weekday in WEEKDAYS.items():
            if re.search(rf"\b{name}\b", text):
                delta = (weekday - today.isoweekday()) % 7

                if delta == 0:
                    delta = 7

                return today + timedelta(days=delta)

        return None

    async def build_alarm(
        self,
        text: str,
        state: dict,
    ) -> dict | None:
        timezone = await self.get_timezone()

        hour = state.get("hour")
        minute = state.get("minute")

        if hour is None:
            parsed = self.parse_time(text)

            if parsed is None:
                return None

            hour, minute = parsed

        weekdays = state.get("weekdays")

        if weekdays is None:
            weekdays = self.parse_weekdays(text)

        target_date = state.get("date")

        if target_date is None and not weekdays:
            target_date = self.parse_date(text, timezone)

        alarm_time = hour * 3600 + minute * 60

        if weekdays:
            first_time = 0

        else:
            if target_date is None:
                now = datetime.now(timezone)
                target_date = now.date()

                target = datetime.combine(
                    target_date,
                    time(hour, minute),
                    tzinfo=timezone,
                )

                if target <= now:
                    target_date += timedelta(days=1)

            target = datetime.combine(
                target_date,
                time(hour, minute),
                tzinfo=timezone,
            )

            first_time = int(target.timestamp())

        return {
            "enabled": True,
            "alarm_time": alarm_time,
            "weekdays": weekdays,
            "first_time": first_time,
        }

    # --------------------------------------------------
    # Alarm selection
    # --------------------------------------------------

    @staticmethod
    def format_time(seconds: int) -> str:
        hour = seconds // 3600
        minute = (seconds % 3600) // 60
        return f"{hour:02d}:{minute:02d}"

    def find_alarm(
        self,
        alarms: list[dict],
        text: str,
    ) -> list[dict]:
        parsed = self.parse_time(text)

        if parsed is None:
            return []

        hour, minute = parsed
        seconds = hour * 3600 + minute * 60

        return [
            alarm
            for alarm in alarms
            if alarm["enabled"]
            and alarm["alarm_time"] == seconds
        ]

    # --------------------------------------------------
    # Operations
    # --------------------------------------------------

    async def handle_list(self, request: SkillRequest):
        alarms = await self.get_alarms()

        active = [
            alarm for alarm in alarms
            if alarm["enabled"]
        ]

        response = Response(
            skill="alarm_ds",
            intent="alarm_ds.list_alarm",
            asr_text=request.text,
        )

        if not active:
            self.start_dialog(
                request,
                {"action": "confirm_create"},
            )

            return (
                response
                .say(
                    "Не нашла установленных будильников. "
                    "Хотите завести новый?"
                )
                .listen(
                    min_waiting_time=0.0,
                    forced_listen=True,
                    listen_previous_intent="alarm_ds.list_alarm",
                )
            )

        descriptions = []

        for alarm in active:
            clock = self.format_time(alarm["alarm_time"])
            weekdays = alarm.get("weekdays", [])

            if weekdays:
                if weekdays == [1, 2, 3, 4, 5]:
                    description = f"по будням в {clock}"
                elif weekdays == [6, 7]:
                    description = f"по выходным в {clock}"
                elif weekdays == list(range(1, 8)):
                    description = f"каждый день в {clock}"
                else:
                    description = f"по расписанию в {clock}"
            else:
                description = f"в {clock}"

            descriptions.append(description)

        message = (
            f"У тебя {len(active)} активных "
            f"{'будильник' if len(active) == 1 else 'будильников'}: "
            + "; ".join(descriptions)
        )

        self.finish_dialog(request)

        return (
            response
            .say(message)
            .alarm_settings(alarms)
        )

    async def handle_set(self, request: SkillRequest):
        state = {
            "action": "set_alarm",
            "hour": None,
            "minute": None,
            "date": None,
            "weekdays": None,
        }

        parsed = self.parse_time(request.text)

        if parsed:
            state["hour"], state["minute"] = parsed
        print(parsed)
        timezone = await self.get_timezone()

        state["date"] = self.parse_date(
            request.text,
            timezone,
        )

        weekdays = self.parse_weekdays(request.text)

        if weekdays:
            state["weekdays"] = weekdays

        if state["hour"] is None:
            self.start_dialog(request, state)

            return self.ask(
                request,
                "set_alarm",
                "На какое время поставить будильник?",
            )

        return await self.complete_set(request, state)

    async def complete_set(
        self,
        request: SkillRequest,
        state: dict,
    ):
        alarm = await self.build_alarm(request.text, state)

        if alarm is None:
            return self.ask(
                request,
                "set_alarm",
                "Не расслышала время. На какое время поставить будильник?",
            )

        alarms = await self.add_alarm(alarm)

        clock = self.format_time(alarm["alarm_time"])

        if alarm["weekdays"] == [1, 2, 3, 4, 5]:
            period = "по будням"
        elif alarm["weekdays"] == [6, 7]:
            period = "по выходным"
        elif alarm["weekdays"] == list(range(1, 8)):
            period = "каждый день"
        elif alarm["weekdays"]:
            period = "по выбранным дням"
        else:
            timezone = await self.get_timezone()
            target = datetime.fromtimestamp(
                alarm["first_time"],
                timezone,
            )
            period = f"на {target.strftime('%d.%m')}"

        self.finish_dialog(request)

        return (
            Response(
                skill="alarm_ds",
                intent="alarm_ds.set_alarm",
                asr_text=request.text,
            )
            .say(f"Завела будильник {period} в {clock}.")
            .alarm_settings(alarms)
        )

    async def handle_delete_all(self, request: SkillRequest):
        alarms = await self.delete_all_alarms()

        self.finish_dialog(request)

        return (
            Response(
                skill="alarm_ds",
                intent="alarm_ds.delete_all_alarm",
                asr_text=request.text,
            )
            .say("Отключила все будильники.")
            .alarm_settings(alarms)
        )

    async def handle_toggle(
        self,
        request: SkillRequest,
        enabled: bool,
    ):
        alarms = await self.get_alarms()
        matches = self.find_alarm(alarms, request.text)

        if not matches:
            return self.ask(
                request,
                "select_alarm",
                "Какой будильник нужно изменить? Назови его время.",
            )

        if len(matches) > 1:
            self.start_dialog(
                request,
                {
                    "action": "toggle",
                    "enabled": enabled,
                    "alarm_ids": [a["id"] for a in matches],
                },
            )

            return self.ask(
                request,
                "select_alarm",
                "Нашла несколько будильников на это время. Уточни, какой имеешь в виду.",
            )

        updated = await self.update_alarm(
            matches[0]["id"],
            {"enabled": enabled},
        )

        self.finish_dialog(request)

        return (
            Response(
                skill="alarm_ds",
                intent=(
                    "alarm_ds.enable_alarm"
                    if enabled else "alarm_ds.disable_alarm"
                ),
                asr_text=request.text,
            )
            .say(
                "Будильник включен."
                if enabled else "Будильник отключен."
            )
            .alarm_settings(updated)
        )

    async def handle_delete(self, request: SkillRequest):
        alarms = await self.get_alarms()
        matches = self.find_alarm(alarms, request.text)

        if not matches:
            self.start_dialog(
                request,
                {
                    "action": "delete",
                    "alarm_ids": [a["id"] for a in alarms],
                },
            )
            return self.ask(
                request,
                "delete_alarm",
                "Какой будильник удалить? Назови время.",
            )

        if len(matches) > 1:
            self.start_dialog(
                request,
                {
                    "action": "delete",
                    "alarm_ids": [a["id"] for a in matches],
                },
            )

            return self.ask(
                request,
                "select_alarm",
                "Нашла несколько будильников на это время. Уточни, какой удалить.",
            )

        updated = await self.delete_alarm(matches[0]["id"])

        self.finish_dialog(request)

        return (
            Response(
                skill="alarm_ds",
                intent="alarm_ds.delete_alarm",
                asr_text=request.text,
            )
            .say("Будильник отключен.")
            .alarm_settings(updated)
        )

    # --------------------------------------------------
    # Dialog continuation
    # --------------------------------------------------

    async def handle_dialog(self, request: SkillRequest):
        state = self.get_dialog(request)
        action = state.get("action")

        text = request.text.strip().lower().replace("ё", "е")

        if re.search(
            r"\b(нет|отмена|отбой|не надо|забудь)\b",
            text,
        ):
            self.finish_dialog(request)

            return Response(
                skill="alarm_ds",
                intent="alarm_ds.cancel",
                asr_text=request.text,
            ).say("Хорошо, отменяю.")

        if action == "confirm_create":
            if re.search(r"\b(да|ага|хочу|конечно)\b", text):
                state["action"] = "set_alarm"
                return self.ask(
                    request,
                    "set_alarm",
                    "На какое время поставить будильник?",
                )

            self.finish_dialog(request)

            return Response(
                skill="alarm_ds",
                intent="alarm_ds.cancel",
                asr_text=request.text,
            ).say("Хорошо.")

        if action == "set_alarm":
            parsed = self.parse_time(text)

            if parsed is None:
                return self.ask(
                    request,
                    "set_alarm",
                    "Не поняла время. Повтори, пожалуйста.",
                )

            state["hour"], state["minute"] = parsed

            timezone = await self.get_timezone()

            parsed_date = self.parse_date(text, timezone)
            if parsed_date:
                state["date"] = parsed_date

            weekdays = self.parse_weekdays(text)
            if weekdays:
                state["weekdays"] = weekdays

            return await self.complete_set(request, state)

        if action in ("delete", "toggle"):
            alarms = await self.get_alarms()
            matches = self.find_alarm(alarms, text)

            if not matches:
                return self.ask(
                    request,
                    "select_alarm",
                    "Не удалось определить будильник. Назови время еще раз.",
                )

            alarm = matches[0]

            if action == "delete":
                updated = await self.delete_alarm(alarm["id"])
                message = "Будильник отключен."
            else:
                enabled = state["enabled"]
                updated = await self.update_alarm(
                    alarm["id"],
                    {"enabled": enabled},
                )
                message = (
                    "Будильник включен."
                    if enabled else "Будильник отключен."
                )

            self.finish_dialog(request)

            return (
                Response(
                    skill="alarm_ds",
                    intent=f"alarm_ds.{action}",
                    asr_text=request.text,
                )
                .say(message)
                .alarm_settings(updated)
            )

        self.finish_dialog(request)

        return Response(
            skill="alarm_ds",
            intent="alarm_ds.unknown",
            asr_text=request.text,
        ).say("Не поняла ответ.")

    # --------------------------------------------------
    # Main handler
    # --------------------------------------------------

    async def handle(self, request: SkillRequest):
        text = request.text.strip()
        normalized = text.lower().replace("ё", "е")

        if "active_skill" in request.context.get(request.session_id) and request.context.get(request.session_id)["active_skill"] == self.definition.name:
            try:
                return await self.handle_dialog(request)
            except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
                print(f"[AlarmsSkill] Dialog error: {exc}")
                self.finish_dialog(request)

                return Response(
                    skill="alarm_ds",
                    intent="alarm_ds.error",
                    asr_text=text,
                ).say("Не удалось выполнить операцию с будильником.")

        matcher = self.get_matcher(request)
        match = matcher.classify(normalized)

        if not match:
            return Response(
                skill="alarm_ds",
                intent="alarm_ds.unknown",
                asr_text=text,
            ).say("Не поняла, что сделать с будильником.")

        intent = match["intent"]

        try:
            if intent == "list_alarm":
                return await self.handle_list(request)

            if intent == "set_alarm":
                return await self.handle_set(request)

            if intent == "delete_all_alarm":
                return await self.handle_delete_all(request)

            if intent == "delete_alarm":
                return await self.handle_delete(request)

            if intent == "enable_alarm":
                return await self.handle_toggle(request, True)

            if intent == "disable_alarm":
                return await self.handle_toggle(request, False)

        except (
            httpx.HTTPError,
            KeyError,
            IndexError,
            ValueError,
        ) as exc:
            print(f"[AlarmsSkill] Error: {exc}")

            return Response(
                skill="alarm_ds",
                intent=f"alarm_ds.{intent}.error",
                asr_text=text,
            ).say("Не удалось выполнить операцию с будильником.")

        return Response(
            skill="alarm_ds",
            intent="alarm_ds.unknown",
            asr_text=text,
        ).say("Не удалось определить команду.")


SKILL = AlarmsSkill.definition
SKILL.handler = AlarmsSkill().handle
