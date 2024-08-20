"""
    Модуль для создания различных кнопок для Telegram-бота.
    Содержит функции для генерации кнопок с помощью классов клавиатур.
"""
import random

from keyboard import ReplyKeyboard
from telebot import types
from btn_text import BTN_STAR_GEME, VIEW_RATING


def start_button():
    """
        Функция для создания стартовой клавиатуры с кнопками.

        :return:
            ReplyKeyboard: Объект клавиатуры .
    """
    reply_keyboard = ReplyKeyboard()
    reply_keyboard.add_button(types.KeyboardButton(BTN_STAR_GEME))

    return reply_keyboard.get_markup()


def translation_buttons(text_buttons: list):
    """
        Создает клавиатуру для выбора перевода слова.

        Функция генерирует клавиатуру с вариантами перевода, случайно перемешивая
        предоставленные слова. В конце списка кнопок добавляется кнопка для
        просмотра статистики.

        :param text_buttons: list Список слов для отображения на кнопках.

        :return: Клавиатура с кнопками для выбора перевода слова и просмотра статистики.
    """
    reply_keyboard = ReplyKeyboard(row_width=2)
    random.shuffle(text_buttons)
    buttons = [types.KeyboardButton(word) for word in text_buttons]
    buttons.append(types.KeyboardButton(VIEW_RATING))
    reply_keyboard.add_button(*buttons)
    return reply_keyboard.get_markup()
