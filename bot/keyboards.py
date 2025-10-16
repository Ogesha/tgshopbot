from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_kb(subscribed: bool) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="🛒 Показать товары")],
        [KeyboardButton(text="📂 Показать по категории")],
        [KeyboardButton(text="✏️ Изменить имя")],
        [KeyboardButton(text="🔁 Обновить каталог (парсинг)")],
    ]
    rows.append([KeyboardButton(text="🔕 Отписаться")]) if subscribed else rows.append([KeyboardButton(text="🔔 Подписаться")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)
