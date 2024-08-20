"""
    Основной файл для запуска Telegram-бота.
    Запускает бот и инициализирует обработчики.
"""
import logging
import telebot

from handlers import Handlers
from config import TELEBOT_TOKEN, config_logging
from utils import DatabaseUtils
from time import sleep

config_logging()
logger = logging.getLogger('main')


class Bot_star:
    """
        Класс для управления запуском и работой Telegram-бота.

        Attributes:
            bot (telebot.TeleBot): Объект бота для взаимодействия с Telegram API.
            handlers (Handlers): Обработчик для работы с командами бота.
    """

    def __init__(self, api_token):
        """
            Инициализация бота и обработчиков.

            :param api_token (str): Токен API для подключения к Telegram.
        """

        self.bot = telebot.TeleBot(api_token)
        self.handlers = Handlers(self.bot)

    def run(self):
        """
            Запуск бота и обработка сообщений.
            В случае ошибки повторяет попытку подключения.
        """

        logger.info('Запуск бота')
        DatabaseUtils().add_tabl()
        while True:
            try:
                logger.info('Попытка подключения к Telegram...')
                self.bot.polling(none_stop=True)

            except Exception as e:
                logger.error(f'{e}', exc_info=True)
                sleep(10)


if __name__ == '__main__':
    bot = Bot_star(TELEBOT_TOKEN)
    bot.run()
