import re


UNITS = {
    "ноль": 0,
    "один": 1,
    "одна": 1,
    "одно": 1,
    "одного": 1,
    "одной": 1,
    "одну": 1,
    "два": 2,
    "две": 2,
    "двух": 2,
    "квадрате": 2,
    "три": 3,
    "трех": 3,
    "трёх": 3,
    "кубе": 3,
    "четыре": 4,
    "четырех": 4,
    "четырёх": 4,
    "пять": 5,
    "пяти": 5,
    "шесть": 6,
    "шести": 6,
    "семь": 7,
    "семи": 7,
    "восемь": 8,
    "восьми": 8,
    "девять": 9,
    "девяти": 9,
}

TEENS = {
    "десять": 10,
    "десяти": 10,
    "одиннадцать": 11,
    "двенадцать": 12,
    "тринадцать": 13,
    "четырнадцать": 14,
    "пятнадцать": 15,
    "шестнадцать": 16,
    "семнадцать": 17,
    "восемнадцать": 18,
    "девятнадцать": 19,
}

TENS = {
    "двадцать": 20,
    "тридцать": 30,
    "сорок": 40,
    "пятьдесят": 50,
    "шестьдесят": 60,
    "семьдесят": 70,
    "восемьдесят": 80,
    "девяносто": 90,
    "двадцати": 20,
    "тридцати": 30,
    "сорока": 40,
    "пятидесяти": 50,
    "шестидесяти": 60,
    "семидесяти": 70,
    "восьмидесяти": 80,
    "девяноста": 90,
}

HUNDREDS = {
    "сто": 100,
    "ста": 100,
    "двести": 200,
    "двухсот": 200,
    "триста": 300,
    "трехсот": 300,
    "трёхсот": 300,
    "четыреста": 400,
    "четырехсот": 400,
    "четырёхсот": 400,
    "пятьсот": 500,
    "пятисот": 500,
    "шестьсот": 600,
    "шестисот": 600,
    "семьсот": 700,
    "семисот": 700,
    "восемьсот": 800,
    "восьмисот": 800,
    "девятьсот": 900,
    "девятисот": 900,
}

SCALES = {
    "тысяча": 1_000,
    "тысячи": 1_000,
    "тысяч": 1_000,
    "тысяче": 1_000,
    "тысячу": 1_000,
    "миллион": 1_000_000,
    "миллиона": 1_000_000,
    "миллионов": 1_000_000,
}

DECIMAL_MARKERS = {
    "десятая": 10,
    "десятых": 10,
    "десятую": 10,
    "сотая": 100,
    "сотых": 100,
    "сотую": 100,
    "тысячная": 1_000,
    "тысячных": 1_000,
    "тысячную": 1_000,
}

NUMBER_WORDS = (
    set(UNITS)
    | set(TEENS)
    | set(TENS)
    | set(HUNDREDS)
    | set(SCALES)
)

TOKEN_RE = re.compile(
    r"[+-]?\d+(?:[.,]\d+)?|[а-яё]+",
    re.IGNORECASE,
)


def parse_integer_words(words: list[str]) -> int:
    total = 0
    current = 0

    for word in words:
        if word in UNITS:
            current += UNITS[word]

        elif word in TEENS:
            current += TEENS[word]

        elif word in TENS:
            current += TENS[word]

        elif word in HUNDREDS:
            current += HUNDREDS[word]

        elif word in SCALES:
            scale = SCALES[word]
            total += (current or 1) * scale
            current = 0

    return total + current


def extract_numbers(text: str) -> list[float]:
    text = text.lower().replace("ё", "е")
    tokens = TOKEN_RE.findall(text)

    numbers = []
    i = 0

    while i < len(tokens):
        token = tokens[i]

        # Число записано цифрами.
        if re.fullmatch(r"[+-]?\d+(?:[.,]\d+)?", token):
            numbers.append(float(token.replace(",", ".")))
            i += 1
            continue

        # Ищем начало числа, записанного словами.
        if token not in NUMBER_WORDS and token != "минус":
            i += 1
            continue

        sign = 1

        if token == "минус":
            sign = -1
            i += 1

            if i >= len(tokens):
                break

            # Отрицательное число цифрами: «минус 12».
            if re.fullmatch(r"\d+(?:[.,]\d+)?", tokens[i]):
                numbers.append(
                    -float(tokens[i].replace(",", "."))
                )
                i += 1
                continue

        # Собираем целую часть.
        integer_words = []

        while i < len(tokens) and tokens[i] in NUMBER_WORDS:
            if tokens[i] in DECIMAL_MARKERS:
                break

            integer_words.append(tokens[i])
            i += 1

        if not integer_words:
            continue

        integer = parse_integer_words(integer_words)

        # Проверяем запись вида «три целых пять десятых».
        if i < len(tokens) and tokens[i] in {
            "целая",
            "целых",
            "целое",
            "целую",
        }:
            i += 1

            fractional_words = []

            while (
                i < len(tokens)
                and tokens[i] in NUMBER_WORDS
                and tokens[i] not in DECIMAL_MARKERS
            ):
                fractional_words.append(tokens[i])
                i += 1

            if (
                i < len(tokens)
                and tokens[i] in DECIMAL_MARKERS
                and fractional_words
            ):
                denominator = DECIMAL_MARKERS[tokens[i]]
                fraction = parse_integer_words(fractional_words)
                integer += fraction / denominator
                i += 1

        numbers.append(sign * integer)

    return numbers

if __name__ == "__main__":
  tests = [
      "пять плюс три",
      "двадцать минус семь",
      "умножь шесть на восемь",
      "сто разделить на четыре",
      "двадцать процентов от двухсот",
      "остаток от деления десяти на три",
      "два в квадрате",
      "корень из ста",
      "сто двадцать пять целых пять десятых",
      "минус пять плюс три",
      "минус 12 разделить на 2",
  ]

  for text in tests:
      print(text, "->", extract_numbers(text))