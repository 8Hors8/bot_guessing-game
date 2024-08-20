"""
    Модуль для создания клавиатур (Reply и Inline) для Telegram-бота.
    Содержит классы для генерации клавиатур с различными настройками.
"""

from telebot import types


class ReplyKeyboard:
    """
        Класс для создания стандартной клавиатуры с кнопками.

        Attributes:
            markup (types.ReplyKeyboardMarkup): Объект клавиатуры для Telegram.
    """

    def __init__(self, resize_keyboard=True, one_time_keyboard=False, row_width=1):
        """
        Инициализация клавиатуры.

        :param resize_keyboard: Уменьшить клавиатуру, чтобы она соответствовала экрану.
        :param one_time_keyboard: Показывать клавиатуру только один раз.
        :param row_width: Количество кнопок в одной строке.
        """
        self.markup = types.ReplyKeyboardMarkup(
            resize_keyboard=resize_keyboard,
            one_time_keyboard=one_time_keyboard,
            row_width=row_width
        )

    def add_button(self, *buttons):
        """
        Добавление кнопок на клавиатуру.

        :param buttons: Кнопки для добавления.
        """
        self.markup.add(*buttons)

    def add_row(self, *buttons):
        """
        Добавление кнопок в одной строке.

        :param buttons: Кнопки для добавления в строку.
        """
        self.markup.add(*buttons)

    def get_markup(self):
        """
        Получение настроенной клавиатуры.

        :return: types.ReplyKeyboardMarkup
        """
        return self.markup


class InlineKeyboard:
    """
        Класс для создания инлайн клавиатуры с кнопками.

        Attributes:
            markup (types.InlineKeyboardMarkup): Объект инлайн клавиатуры для Telegram.
    """

    def __init__(self, row_width=1):
        """
        Инициализация инлайн клавиатуры.

        :param row_width: Количество кнопок в одной строке.
        """
        self.markup = types.InlineKeyboardMarkup(row_width=row_width)

    def add_button(self, text, callback_data):
        """
        Добавление инлайн кнопки.

        :param text: Текст кнопки.
        :param callback_data: Данные, которые будут отправлены при нажатии на кнопку.
        """
        button = types.InlineKeyboardButton(text=text, callback_data=callback_data)
        self.markup.add(button)

    def add_row(self, *buttons):
        """
        Добавление кнопок в одной строке на инлайн клавиатуре.

        :param buttons: Кнопки для добавления в строку.
        """
        self.markup.add(*buttons)

    def get_markup(self):
        """
        Получение настроенной инлайн клавиатуры.

        :return: types.InlineKeyboardMarkup
        """
        return self.markup
