
import re

from classifier.base import SkillDefinition, BaseSkill
from classifier.util import SemanticMatcher

from protocol import Response
from skills.base import SkillRequest
from skills.calculator.operations import OPERATIONS, OPERATION_PATTERNS
from skills.calculator.engine import calculate
from utils.num_parser import extract_numbers


class CalculatorSkill(BaseSkill):

    definition = SkillDefinition(
        name="calculator",

        rules=[
            r"\bсколько будет\b",
            r"\bпосчитай\b",
            r"\bвычисли\b",
            r"\bприбавь\b",
            r"\bвычти\b",
            r"\bумножь\b",
            r"\bраздели\b",
            r"\bквадратный корень\b",
            r"\bсколько процентов\b",
        ],

        examples=[
            "Сколько будет пять плюс три?",
            "Посчитай двадцать минус семь",
            "Умножь шесть на восемь",
            "Раздели сто на четыре",
            "Сколько будет двадцать процентов от двухсот?",
            "Найди остаток от деления десяти на три",
            "Возведи два в квадрат",
            "Сколько будет три в кубе?",
            "Извлеки квадратный корень из ста",
        ],

        priority=10,
    )

    def __init__(self):
        self.operation_matcher = None

    def detect_operation(self, text, request):

      for operation, patterns in OPERATION_PATTERNS.items():
          if any(re.search(pattern, text) for pattern in patterns):
              return operation

      match = self.get_operation_matcher(request).classify(text)

      if match:
          return match["intent"]

      return None

    def get_operation_matcher(self, request: SkillRequest):
        if self.operation_matcher is None:
            self.operation_matcher = SemanticMatcher(
                model=request.semantic_model,
                intents=OPERATIONS,
                threshold=0.55,
                margin=0.05,
            )

        return self.operation_matcher

    def format_result(self, result: float) -> str:
        if result == int(result):
            return str(int(result))

        return f"{result:.10f}".rstrip("0").rstrip(".")

    async def handle(self, request: SkillRequest):

        text = request.text.strip()
        normalized = text.lower().replace("ё", "е")
        operation = self.detect_operation(normalized, request)

        if not operation:
            return (
                Response(
                    skill="calculator",
                    intent="calculator.unknown_operation",
                    asr_text=text,
                )
                .say("Не удалось определить математическую операцию")
            )

        operation
        print(operation)
        numbers = extract_numbers(normalized)

        if not numbers:
            return (
                Response(
                    skill="calculator",
                    intent="calculator.no_numbers",
                    asr_text=text,
                )
                .say("Не удалось распознать числа")
            )

        # Обратный порядок аргументов:
        # «вычти семь из двадцати» -> 20 - 7
        if operation == "subtract" and re.search(r"\bиз\b", normalized):
            numbers.reverse()

        try:
            result = calculate(operation, numbers)

        except ValueError as error:
            return (
                Response(
                    skill="calculator",
                    intent="calculator.calculation_error",
                    asr_text=text,
                )
                .say(str(error))
            )

        result_text = self.format_result(result)

        return (
            Response(
                skill="calculator",
                intent=f"calculator.{operation}",
                asr_text=text,
            )
            .say(result_text)
        )


SKILL = CalculatorSkill.definition
SKILL.handler = CalculatorSkill().handle
