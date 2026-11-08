
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from classifier.base import SkillDefinition, BaseSkill
from classifier.util import SemanticMatcher
from protocol import Response
from skills.base import SkillRequest

from config.settings import WEATHER_CITY


logger = logging.getLogger(__name__)


class WeatherSkill(BaseSkill):
    definition = SkillDefinition(
        name="weather",
        rules=[
            r"\bсколько сейчас градусов\b",
            r"\bтемператур\w*\b.*\b(?:на улице|снаружи)\b",
            r"\bпогод\w*\b",
            r"\bдожд\w*\b",
            r"\bпрогноз\b",
        ],
        examples=[
            "какая погода сегодня",
            "будет ли завтра дождь",
            "сколько сейчас градусов на улице",
            "какая погода в Москве",
            "какая температура будет вечером",
            "какая погода ожидается завтра вечером",
            "будет ли дождь сегодня ночью",
        ],
        priority=10,
    )

    GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

    WEATHER_CODES = {
        0: "ясно",
        1: "преимущественно ясно",
        2: "переменная облачность",
        3: "пасмурно",
        45: "туман",
        48: "изморозь",
        51: "небольшая морось",
        53: "умеренная морось",
        55: "сильная морось",
        56: "слабая ледяная морось",
        57: "сильная ледяная морось",
        61: "небольшой дождь",
        63: "умеренный дождь",
        65: "сильный дождь",
        66: "слабый ледяной дождь",
        67: "сильный ледяной дождь",
        71: "небольшой снег",
        73: "умеренный снег",
        75: "сильный снег",
        77: "снежная крупа",
        80: "небольшой ливень",
        81: "умеренный ливень",
        82: "сильный ливень",
        85: "небольшой снегопад",
        86: "сильный снегопад",
        95: "гроза",
        96: "гроза с небольшим градом",
        99: "гроза с сильным градом",
    }

    @staticmethod
    def http_get(url: str, params: dict) -> dict:
        query = urlencode(params)
        request = Request(
            f"{url}?{query}",
            headers={"User-Agent": "CapsuleMarusya/1.0"},
        )

        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def parse_request(text: str):
        text = text.strip()

        # Определяем период.
        day_offset = 0

        if "послезавтра" in text:
            day_offset = 2
        elif "завтра" in text:
            day_offset = 1

        period = "current"

        if "ночью" in text:
            period = "night"
        elif "вечером" in text:
            period = "evening"
        elif "утром" in text:
            period = "morning"
        elif "днем" in text or "днём" in text:
            period = "day"
        elif "сегодня" in text or "завтра" in text or "послезавтра" in text:
            period = "day"

        # Извлекаем город после предлога "в".
        location = None

        location_match = re.search(
            r"\bв\s+(.+?)"
            r"(?=\s+(?:сегодня|завтра|послезавтра|"
            r"вечером|утром|ночью|днем|днём)\b|$)",
            text,
        )

        if location_match:
            location = location_match.group(1).strip(" .,!?")

        return location, day_offset, period

    async def get_location(self, city: str):
        data = await asyncio.to_thread(
            self.http_get,
            self.GEOCODING_URL,
            {
                "name": city,
                "count": 1,
                "language": "ru",
                "format": "json",
            },
        )

        results = data.get("results") or []

        if not results:
            return None

        return results[0]

    async def get_forecast(self, location: dict):
        return await asyncio.to_thread(
            self.http_get,
            self.FORECAST_URL,
            {
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "current": (
                    "temperature_2m,"
                    "apparent_temperature,"
                    "relative_humidity_2m,"
                    "weather_code,"
                    "wind_speed_10m"
                ),
                "hourly": (
                    "temperature_2m,"
                    "precipitation_probability,"
                    "precipitation,"
                    "weather_code"
                ),
                "daily": (
                    "weather_code,"
                    "temperature_2m_max,"
                    "temperature_2m_min,"
                    "precipitation_probability_max"
                ),
                "forecast_days": 3,
                "timezone": "auto",
            },
        )

    def describe_current(self, data: dict) -> str:
        current = data["current"]

        code = int(current["weather_code"])
        description = self.WEATHER_CODES.get(code, "неизвестная погода")

        return (
            f"Сейчас {current['temperature_2m']:.0f} градусов, "
            f"{description}. "
            f"Ощущается как {current['apparent_temperature']:.0f} градусов. "
            f"Влажность {current['relative_humidity_2m']} процентов, "
            f"ветер {current['wind_speed_10m']:.0f} километров в час."
        )

    def describe_day(self, data: dict, day_offset: int) -> str:
        daily = data["daily"]

        date = daily["time"][day_offset]
        minimum = daily["temperature_2m_min"][day_offset]
        maximum = daily["temperature_2m_max"][day_offset]
        probability = daily["precipitation_probability_max"][day_offset]

        code = int(daily["weather_code"][day_offset])
        description = self.WEATHER_CODES.get(code, "переменная погода")

        day_name = {
            0: "Сегодня",
            1: "Завтра",
            2: "Послезавтра",
        }.get(day_offset, date)

        return (
            f"{day_name} ожидается {description}. "
            f"Температура от {minimum:.0f} до {maximum:.0f} градусов. "
            f"Вероятность осадков до {probability} процентов."
        )

    def describe_period(
        self,
        data: dict,
        location: dict,
        day_offset: int,
        period: str,
    ) -> str:
        hourly = data["hourly"]
        timezone = ZoneInfo(location["timezone"])

        target_date = (
            datetime.now(timezone).date()
            + timedelta(days=day_offset)
        )

        hours = {
            "morning": range(6, 12),
            "day": range(12, 18),
            "evening": range(18, 24),
            "night": range(0, 6),
        }[period]

        selected = []

        for index, value in enumerate(hourly["time"]):
            moment = datetime.fromisoformat(value)

            if moment.date() == target_date and moment.hour in hours:
                selected.append(index)

        if not selected:
            return "Не удалось получить прогноз на это время."

        temperatures = [
            hourly["temperature_2m"][i]
            for i in selected
            if hourly["temperature_2m"][i] is not None
        ]

        probabilities = [
            hourly["precipitation_probability"][i]
            for i in selected
            if hourly["precipitation_probability"][i] is not None
        ]

        precipitations = [
            hourly["precipitation"][i]
            for i in selected
            if hourly["precipitation"][i] is not None
        ]

        codes = [
            int(hourly["weather_code"][i])
            for i in selected
            if hourly["weather_code"][i] is not None
        ]

        if not temperatures:
            return "Не удалось получить прогноз на это время."

        minimum = min(temperatures)
        maximum = max(temperatures)
        probability = max(probabilities, default=0)
        precipitation = sum(precipitations)
        description = self.WEATHER_CODES.get(
            max(codes, key=lambda code: code >= 51),
            "переменная погода",
        ) if codes else "переменная погода"

        rain_text = (
            f"Вероятность осадков до {probability} процентов."
        )

        if probability >= 50 or precipitation > 0.1:
            rain_text = (
                f"Возможны осадки, вероятность до {probability} процентов."
            )
        else:
            rain_text = "Существенных осадков не ожидается."

        period_names = {
            "morning": "утром",
            "day": "днём",
            "evening": "вечером",
            "night": "ночью",
        }

        return (
            f"{period_names[period]} температура будет "
            f"от {minimum:.0f} до {maximum:.0f} градусов. "
            f"{description.capitalize()}. {rain_text}"
        )

    async def handle(self, request: SkillRequest):
        text = request.text.strip().lower().replace("ё", "е")

        response = Response(
            skill="weather",
            intent="weather",
            asr_text=text,
        )

        city, day_offset, period = self.parse_request(text)
        city = city or WEATHER_CITY

        if not city:
            return response.say(
                "Для какого города узнать погоду?"
            )

        try:
            location = await self.get_location(city)

            if not location:
                return response.say(
                    f"Не удалось найти город {city}."
                )

            data = await self.get_forecast(location)

            if period == "current" and day_offset == 0:
                result = self.describe_current(data)
            elif period == "day":
                result = self.describe_day(data, day_offset)
            else:
                result = self.describe_period(
                    data,
                    location,
                    day_offset,
                    period,
                )

            city_name = location["name"]
            return response.say(f"{city_name}. {result}")

        except Exception:
            logger.exception("Weather request failed")
            return response.say(
                "Не удалось получить прогноз погоды."
            )


SKILL = WeatherSkill.definition
SKILL.handler = WeatherSkill().handle
