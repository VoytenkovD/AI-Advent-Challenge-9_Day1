# -*- coding: utf-8 -*-
import sys

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


def choose_model(client):
    """Показывает список доступных моделей и даёт выбрать номером или именем."""
    try:
        available = sorted(m.id for m in client.models.list().data)
    except Exception as e:
        print(f"Не удалось получить список моделей: {e}")
        available = []

    if available:
        print(f"\nДоступно моделей: {len(available)}")
        for i, name in enumerate(available, 1):
            print(f"  {i:2}. {name}")

    prompt = f"\nНомер или название модели (Enter = {DEFAULT_MODEL}): "
    choice = input(prompt).strip()

    if not choice:
        return DEFAULT_MODEL
    if choice.isdigit() and available and 1 <= int(choice) <= len(available):
        return available[int(choice) - 1]
    if available and choice not in available:
        print(f"Предупреждение: модели '{choice}' нет в списке, но пробуем.")
    return choice


def main():
    print("=== Консольный клиент для LLM ===")

    api_key = input("Введите ваш API-ключ: ").strip()
    if not api_key:
        print("Ключ не может быть пустым. Завершение.")
        return

    client = OpenAI(base_url=BASE_URL, api_key=api_key)
    model = choose_model(client)

    # Проверка подключения выбранной модели
    try:
        client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5,
        )
        print(f"\nПодключено. Модель: {model}. Можно общаться.\n")
    except Exception as e:
        print(f"Ошибка подключения: {e}")
        print("Проверьте ключ, название модели и доступность сервиса.")
        return

    # История диалога — модель помнит предыдущие сообщения
    messages = [{"role": "system", "content": "Ты полезный ассистент. Отвечай на русском."}]

    while True:
        try:
            user_input = input("Вы (или 'exit' для выхода): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nДо свидания!")
            break

        if user_input.lower() in ("exit", "quit", "выход"):
            print("До свидания!")
            break
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})

        try:
            response = client.chat.completions.create(model=model, messages=messages)
            answer = response.choices[0].message.content
            messages.append({"role": "assistant", "content": answer})
            print(f"\nМодель: {answer}\n")
        except Exception as e:
            messages.pop()  # не сохраняем в историю неудачный запрос
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
