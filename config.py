"""
    Модуль для настройки конфигурации проекта.
    Содержит функции для загрузки токенов и настройки логирования.
"""
import logging
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path='./token.env')

TELEBOT_TOKEN = os.getenv('BOT_API_TOKEN')
dbname = os.getenv('dbname')
dbuser = os.getenv('dbuser')
password = os.getenv('password')
DB_PATH = {'dbname': dbname,
           'user': dbuser,
           'password': password
           }


def config_logging(level=logging.INFO):
    """
        Настройка логирования для приложения.
        :param level: Уровень логирования. По умолчанию - INFO.
    """
    logging.basicConfig(
        level=level,
        datefmt="%Y-%m-%d %H:%M:%S",
        format="[%(asctime)s.%(msecs)03d] %(module)s:%(lineno)d %(levelname)7s - %(message)s"

    )


def disable_custom_logging():
    """
    Отключение настроенного логирования и возврат к классическим логам.
    """
    logging.getLogger().handlers.clear()  # Удаляем все обработчики
    logging.basicConfig(level=logging.CRITICAL)  # Устанавливаем уровень логирования на ERROR
