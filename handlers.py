"""
    Модуль для обработки команд и сообщений Telegram-бота.
    Содержит классы и функции для взаимодействия с пользователями.
"""
import bot_msg, btn_text
from buttons import start_button
from utils import GameUtils


class Handlers:
    """
        Класс для настройки и обработки команд Telegram-бота.

        Attributes:
        bot (telebot.TeleBot): Объект бота для взаимодействия с Telegram API.
        game_utils (GameUtils): Утилиты для работы с игровыми функциями.
    """

    def __init__(self, bot):
        """
            Инициализация обработчика команд и баз данных.

            :param bot (telebot.TeleBot): Объект бота для взаимодействия с Telegram API.
        """
        self.bot = bot
        self.setup_handlers()
        self.game_utils = GameUtils(self.bot)

    def setup_handlers(self):
        """
            Настройка обработчиков команд.
        """

        @self.bot.message_handler(commands=['start'])
        def start_bot(message):
            self.handle_start(message)

        @self.bot.message_handler(commands=['help'])
        def help(message):
            self.handle_help(message)

        # обработчик кнопки btn_text.BTN_STAR_GEME
        @self.bot.message_handler(func=lambda message: message.text == btn_text.BTN_STAR_GEME)
        def start_geme(message):
            """
                Обработка нажатия кнопки BTN_STAR_GEME.

                :param message: Сообщение от пользователя.
                :type message: telebot.types.Message
            """
            self.game_utils.get_user_name(message)

        @self.bot.message_handler(func=lambda message: True)
        def all_messages(message):
            """
                Обработка всех входящих сообщений.

                :param message: Сообщение от пользователя.
                :type message: telebot.types.Message
            """
            self.handle_all_messages(message)

    def handle_start(self, message):
        """
            Обработка команды /start и отправляет приветственное сообщение.

            :param message : (telebot.types.Message) Сообщение от пользователя.
        """
        chat_id = message.chat.id
        self.bot.send_message(chat_id, bot_msg.MSG_START,
                              reply_markup=start_button(), parse_mode="HTML")

    def handle_help(self, message):
        """
           Обработка команды /help и отправляет сообщение с помощью.

           :param message : (telebot.types.Message) Сообщение от пользователя.
        """
        chat_id = message.chat.id
        self.bot.send_message(chat_id, bot_msg.MSG_HELP)

    def handle_all_messages(self, message):
        """
            Обработка всех входящих сообщений.

            Отправляет пользователю сообщение о том, что сессия прервалась.

            :param message: Сообщение от пользователя.
            :type message: telebot.types.Message
        """
        chat_id = message.chat.id
        self.bot.send_message(chat_id, 'Сессия прервалась нажмите на кнопку',
                              reply_markup=start_button())
