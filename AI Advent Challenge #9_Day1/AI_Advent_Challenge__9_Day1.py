# -*- coding: utf-8 -*-
"""Минимальный консольный клиент для LLM через OpenAI-совместимый API.

Ключ читается из файла (по умолчанию ~/.secrets/ai-public), чтобы не
светить его в коде и в истории консоли.
"""
import os
import sys
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("Не установлена библиотека openai.")
    print("Установите её командой:")
    print(f'    "{sys.executable}" -m pip install openai')
    input("\nНажмите Enter для выхода...")
    sys.exit(1)

BASE_URL = "https://ai-public.a101.ru/api"
DEFAULT_MODEL = "openai/gpt-4.1"

# Файл с ключом. Можно переопределить переменной окружения AI_PUBLIC_KEY_FILE.
KEY_FILE = Path(os.getenv("AI_PUBLIC_KEY_FILE") or Path.home() / ".secrets" / "ai-public")

# Маркер завершения ответа: модели велено закончить им, а API обязано
# остановить генерацию, как только маркер встретится (stop sequence).
STOP_MARKER = "[[END]]"

# Режимы формата ответа: явное описание формата + лимит длины.
MODES = {
    "1": {
        "name": "краткий",
        "max_tokens": 150,
        "format": (
            "ФОРМАТ ОТВЕТА: строго 1-3 предложения простым текстом. "
            "Без списков, без заголовков, без markdown, без вступлений "
            "вида «Конечно» или «Хороший вопрос». "
            "Сразу суть, максимум 60 слов."
        ),
    },
    "2": {
        "name": "развёрнутый",
        "max_tokens": 900,
        "format": (
            "ФОРМАТ ОТВЕТА: ровно три секции, каждая с заголовком на своей строке:\n"
            "Кратко: один абзац из 1-2 предложений с главным выводом.\n"
            "Подробно: 3-6 пунктов списка, каждый пункт начинается с '- '.\n"
            "Итог: одно предложение с практической рекомендацией.\n"
            "Не добавляй других секций и не меняй названия заголовков."
        ),
    },
}


def build_system_prompt(mode):
    """Собирает system-инструкцию: роль + формат + длина + условие завершения."""
    return (
        "Ты полезный ассистент. Отвечай на русском языке.\n\n"
        f"{mode['format']}\n\n"
        f"ОГРАНИЧЕНИЕ ДЛИНЫ: не превышай {mode['max_tokens']} токенов. "
        "Если материала много — сокращай, но не обрывай мысль на середине.\n\n"
        f"УСЛОВИЕ ЗАВЕРШЕНИЯ: закончив ответ, поставь на новой строке маркер "
        f"{STOP_MARKER} и не пиши ничего после него. "
        "Не задавай встречных вопросов и не предлагай продолжить."
    )


def read_api_key():
    """Ключ: файл -> переменная окружения -> ручной ввод."""
    if KEY_FILE.is_file():
        # utf-8-sig снимает BOM, если файл сохранён Блокнотом
        key = KEY_FILE.read_text(encoding="utf-8-sig").strip()
        if key:
            print(f"Ключ загружен из {KEY_FILE} (…{key[-4:]})")
            return key
        print(f"Файл {KEY_FILE} пуст.")
    else:
        print(f"Файл с ключом не найден: {KEY_FILE}")

    key = (os.getenv("AI_PUBLIC_API_KEY") or "").strip()
    if key:
        print("Ключ загружен из переменной окружения AI_PUBLIC_API_KEY.")
        return key

    return input("Введите API-ключ вручную: ").strip()


def choose_model(client):
    """Показывает доступные модели, выбор номером или именем."""
    try:
        available = sorted(m.id for m in client.models.list().data)
    except Exception as e:
        print(f"Не удалось получить список моделей: {e}")
        available = []

    if available:
        print(f"\nДоступно моделей: {len(available)}")
        for i, name in enumerate(available, 1):
            print(f"  {i:2}. {name}")

    choice = input(f"\nНомер или название модели (Enter = {DEFAULT_MODEL}): ").strip()
    if not choice:
        return DEFAULT_MODEL
    if choice.isdigit() and available and 1 <= int(choice) <= len(available):
        return available[int(choice) - 1]
    if available and choice not in available:
        print(f"Предупреждение: модели '{choice}' нет в списке, но пробуем.")
    return choice


def choose_mode(current=None):
    """Выбор формата ответа."""
    print("\nФормат ответа:")
    for key, mode in MODES.items():
        print(f"  {key}. {mode['name']} (лимит {mode['max_tokens']} токенов)")

    default = "1" if current is None else current
    choice = input(f"Выберите 1 или 2 (Enter = {MODES[default]['name']}): ").strip()
    return choice if choice in MODES else default


def ask(client, model, messages, mode):
    """Один запрос к LLM с ограничением длины и stop-последовательностью."""
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=mode["max_tokens"],   # ограничение на длину ответа
        stop=[STOP_MARKER],              # условие завершения ответа
        temperature=0.7,
    )
    choice = response.choices[0]
    text = (choice.message.content or "").strip()

    # Если провайдер проигнорировал stop — убираем маркер сами.
    if text.endswith(STOP_MARKER):
        text = text[: -len(STOP_MARKER)].strip()

    return text, choice.finish_reason, response.usage


def main():
    print("=== Консольный клиент для LLM ===")

    api_key = read_api_key()
    if not api_key:
        print("Ключ не получен. Завершение.")
        return

    client = OpenAI(base_url=BASE_URL, api_key=api_key)
    model = choose_model(client)
    mode_key = choose_mode()
    mode = MODES[mode_key]

    # Проверка подключения
    try:
        client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5,
        )
    except Exception as e:
        print(f"\nОшибка подключения: {e}")
        print("Проверьте ключ, название модели и доступность сервиса.")
        return

    print(f"\nПодключено. Модель: {model}. Формат: {mode['name']}.")
    print("Команды: 'mode' — сменить формат, 'exit' — выход.\n")

    # История диалога: system-инструкция + все реплики
    messages = [{"role": "system", "content": build_system_prompt(mode)}]

    while True:
        try:
            user_input = input("Вы: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nДо свидания!")
            break

        if not user_input:
            continue

        low = user_input.lower()
        if low in ("exit", "quit", "выход"):
            print("До свидания!")
            break

        if low in ("mode", "формат"):
            mode_key = choose_mode(mode_key)
            mode = MODES[mode_key]
            # Обновляем system-инструкцию, история диалога сохраняется
            messages[0] = {"role": "system", "content": build_system_prompt(mode)}
            print(f"Формат переключён на «{mode['name']}».\n")
            continue

        messages.append({"role": "user", "content": user_input})

        try:
            text, finish_reason, usage = ask(client, model, messages, mode)
            messages.append({"role": "assistant", "content": text})

            print(f"\nМодель ({mode['name']}):\n{text}")
            if finish_reason == "length":
                print(f"\n[ответ обрезан лимитом {mode['max_tokens']} токенов]")
            if usage:
                print(f"[токенов: {usage.total_tokens}, стоп: {finish_reason}]")
            print()
        except Exception as e:
            messages.pop()  # не храним в истории неудачный запрос
            print(f"Ошибка при отправке запроса: {e}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
    finally:
        try:
            input("\nНажмите Enter для выхода...")
        except (EOFError, KeyboardInterrupt):
            pass
