
import math


def calculate(operation: str, numbers: list[float]) -> float:

    if operation in ("add", "subtract", "multiply", "divide", "modulo", "power", "percentage"):
        if len(numbers) != 2:
            raise ValueError("Для этой операции нужны два числа")

    elif operation == "sqrt":
        if len(numbers) != 1:
            raise ValueError("Для извлечения корня нужно одно число")

    else:
        raise ValueError("Неизвестная математическая операция")
    if operation == "add":
        result = numbers[0] + numbers[1]

    elif operation == "subtract":
        result = numbers[0] - (numbers[1] if numbers[1] > 0 else numbers[1] * -1)

    elif operation == "multiply":
        result = numbers[0] * numbers[1]

    elif operation == "divide":
        if numbers[1] == 0:
            raise ValueError("На ноль делить нельзя")

        result = numbers[0] / numbers[1]

    elif operation == "modulo":
        if numbers[1] == 0:
            raise ValueError("На ноль делить нельзя")

        result = numbers[0] % numbers[1]

    elif operation == "power":
        result = numbers[0] ** numbers[1]

    elif operation == "percentage":
        result = numbers[0] / 100 * numbers[1]

    elif operation == "sqrt":
        if numbers[0] < 0:
            raise ValueError("Нельзя извлечь действительный квадратный корень из отрицательного числа")

        result = math.sqrt(numbers[0])

    if not math.isfinite(result):
        raise ValueError("Результат слишком большой")

    return result
