"""
    Этот модуль содержит утилиты для игрового процесса и взаимодействия с базой данных.
    Включает классы для управления игровым процессом и базой данных, а также функции
    для работы с пользователями и словами.
"""
import csv
import logging
import random

from database import Database
from config import config_logging
from buttons import translation_buttons, start_button, universal_buttons
from btn_text import BTN_VIEW_RATING, BTN_ADD_WORD, BTN_DEL_WORD, BTN_Back

config_logging()
logger = logging.getLogger('utils')


class GameUtils:
    """
        Класс с утилитами для игрового процесса.

        Attributes:
            bot (telebot.TeleBot): Объект Telegram-бота для взаимодействия с Telegram API.
            db (DatabaseUtils): Объект для взаимодействия с базой данных.
    """

    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseUtils()

    def get_user_name(self, message):
        """
            Запрашивает имя пользователя и сохраняет его в базе данных, если оно ещё не сохранено.

            Если имя пользователя уже сохранено, начинается игра. В противном случае бот запрашивает
            имя пользователя и регистрирует следующий шаг для сохранения имени.

            :param message: Сообщение от пользователя, содержащее его идентификатор.
        """
        chat_id = message.chat.id
        user_id = message.from_user.id
        user_info = self.db.search_user(user_id)
        if user_info is None:
            self.bot.send_message(chat_id, 'Как я могу к вам обращаться?')
            self.bot.register_next_step_handler(message, self.save_user_name)
        else:
            self.bot.send_message(chat_id, 'Игра продолжается!!')
            self.start_game(message)

    def save_user_name(self, message):
        """
            Сохраняет имя пользователя в базе данных и начинает игру.

            После получения имени пользователя, оно сохраняется в базе данных, и затем
            бот начинает игровой процесс.

            :param message: Сообщение от пользователя, содержащее его имя.
        """
        chat_id = message.chat.id
        user_id = message.from_user.id
        user_name = message.text

        self.db.save_user(user_name, user_id)

        self.bot.send_message(chat_id, f"Приятно познакомиться, {user_name}!\n Да начнется игра!!")
        self.start_game(message)

    def start_game(self, message):
        """
            Начинает игру, предлагая пользователю слово для перевода и варианты перевода.

            Эта функция выбирает случайное слово, его правильный перевод и несколько
            неправильных вариантов перевода. После этого отправляет пользователю сообщение
            с предложением выбрать правильный перевод.

            :param message: Сообщение от пользователя, содержащее его идентификатор.
        """
        chat_id = message.chat.id
        word, correct_translation, text_buttons, id_word_db = self.word_generator(message)

        text_buttons.append(correct_translation)
        markup = translation_buttons(text_buttons)

        self.bot.send_message(chat_id, f"Как перевести слово '<b>{word}</b>'?",
                              reply_markup=markup, parse_mode="HTML")

        self.bot.register_next_step_handler_by_chat_id(chat_id, self.check_answer,
                                                       id_word_db, correct_translation)

    def check_answer(self, message, id_word: int, correct_translation: str):
        """
            Проверяет правильность ответа пользователя и обновляет его очки.

            Если ответ пользователя правильный, добавляются очки и начинается новый раунд.
            В случае неправильного ответа, очки отнимаются. Пользователь также может
            запросить отображение рейтинга.

            :param message: Сообщение от пользователя с его выбором.
            :param id_word: Идентификатор слова в базе данных.
            :param correct_translation: Правильный перевод слова.
        """
        chat_id = message.chat.id
        user_answer = message.text
        user_id = message.from_user.id

        if user_answer == correct_translation:
            self.bot.send_message(chat_id, "Превосходно! Вы справились! 🌟 +1 балл!")
            self.db.update_points(user_id, 1)
            self.db.update_times_shown(user_id, id_word)
            self.start_game(message)

        elif user_answer == BTN_VIEW_RATING:
            result = self.display_player_rating(user_id)
            self.bot.send_message(chat_id, result, parse_mode='HTML')
            self.bot.send_message(chat_id, 'Дя продолжения нажмите кнопку',
                                  reply_markup=start_button())

        elif user_answer == BTN_ADD_WORD:
            self.add_new_word(message)

        elif user_answer == BTN_DEL_WORD:
            self.dell_word_user(message)

        else:
            self.bot.send_message(chat_id, "Не совсем так. Но не отчаивайтесь! 💔 -3 балла!")
            self.db.update_points(user_id, 3, add=False)
            self.start_game(message)

    def add_new_word(self, message):
        """
        Инициирует процесс добавления нового слова для пользователя.

        Функция отправляет пользователю сообщение с инструкцией по добавлению
        нового слова и его перевода.
        Пользователь должен ввести слово на русском и его перевод через запятую.
        Также отображается кнопка "Назад" для возврата.

        :param message: Сообщение от пользователя.
        """
        chat_id = message.chat.id
        user_id = message.from_user.id
        self.bot.send_message(chat_id,
                              'Введите слово и его перевод через запятую (например, "кот, cat"):',
                              reply_markup=universal_buttons([BTN_Back]))
        self.bot.register_next_step_handler(message, self._save_new_word, user_id)

    def _save_new_word(self, message, user_id: int):
        """
        Сохраняет новое слово и его перевод для конкретного пользователя в базе данных.

        Функция проверяет правильность ввода (два значения через запятую), сохраняет слово
        с переводом в базу данных и отображает пользователю список всех добавленных слов
        с их статусами "изучается" или "изучено").
        Также предоставляет кнопку для продолжения игры или возврата в главное меню.

        :param message: Сообщение от пользователя с новым словом и его переводом.
        :param user_id: Идентификатор пользователя в Telegram.
        """
        chat_id = message.chat.id
        text = message.text.lower().split(',')

        if text[0].strip() == BTN_Back.lower():
            self.start_game(message)

        else:
            if len(text) == 2:
                word = text[0].strip()
                translation = text[1].strip()

                if not self.db.search_word(word, user_id):
                    self.db.save_word(word, translation, user_id)
                    self.bot.send_message(chat_id,
                                          f'Слово "{word}" с переводом "{translation}" '
                                          f'было успешно добавлено.'
                                          )

                    word_message = self._format_user_words(user_id)
                    self.bot.send_message(chat_id, word_message + '\nДя продолжения нажмите кнопку',
                                          reply_markup=start_button(), parse_mode='HTML')

                else:
                    self.bot.send_message(chat_id,
                                          f'Слово "{word}" уже существует в вашей базе данных.')
            else:
                self.bot.send_message(chat_id, 'Неверный формат. Попробуйте снова.')

    def dell_word_user(self, message):
        """
        Запрашивает у пользователя слово для удаления и отображает список добавленных слов.

        Функция запрашивает у пользователя слово, которое нужно удалить из базы данных,
        и выводит ему список ранее добавленных слов для удобства выбора.
        Также предоставляется кнопка "Назад", чтобы вернуться без удаления слова.

        :param message: Объект сообщения Telegram, используемый для взаимодействия с пользователем.
        """

        user_id = message.from_user.id
        chat_id = message.chat.id
        word_message = self._format_user_words(user_id)

        self.bot.send_message(chat_id, word_message + '\nУкажите слово которое нужно удалить',
                              reply_markup=universal_buttons([BTN_Back]), parse_mode='HTML')
        self.bot.register_next_step_handler(message, self._delete_user_word, user_id)

    def _delete_user_word(self, message, user_id: int):
        """
        Удаляет указанное пользователем слово из базы данных и уведомляет его о результате.

        Функция удаляет слово, введенное пользователем, из базы данных для конкретного пользователя.
        Если удаление прошло успешно, пользователю отправляется сообщение об успешном удалении.
        В случае неудачи или если слово не было найдено,
        отправляется сообщение с соответствующим уведомлением.

        :param message: Объект сообщения Telegram, который содержит введенное пользователем слово.
        :param user_id: int Идентификатор пользователя в базе данных.
        """
        chat_id = message.chat.id
        text = message.text.lower().strip()

        if text == BTN_Back.lower():
            self.start_game(message)
            return

        result = self.db.delete_word(text, user_id)

        if result:
            self.bot.send_message(chat_id,
                                  f'Слово <b>{text.capitalize()}</b> успешно удалено из базы данных.\n'
                                  'Для продолжения нажмите кнопку.',
                                  reply_markup=start_button(),
                                  parse_mode="HTML")
        else:
            self.bot.send_message(chat_id,
                                  f'Слово <b>{text.capitalize()}</b> не удалось удалить из базы данных.\n'
                                  'Для продолжения нажмите кнопку.',
                                  reply_markup=start_button(),
                                  parse_mode="HTML")

    def _format_user_words(self, user_id: int) -> str:
        """
        Форматирует список слов пользователя и их статус (изучается или изучено).

        :param user_id: Идентификатор пользователя в базе данных.
        :return: Строка с отформатированным списком слов.
        """
        word_dict = self.db.get_user_word(user_id)
        word_list = []

        for word, times_shown in word_dict.items():
            status = "<b>изучается</b>" if times_shown is None or times_shown < 4 else "изучено"
            word_list.append(f"{word} - {status}")

        word_message = "Слова, которые вы добавили:\n" + "\n".join(word_list)
        return word_message

    def word_generator(self, message) -> tuple[str, str, list[str], int]:
        """
        Генерирует слова для перевода и соответствующие варианты перевода.

        Эта функция выбирает случайный источник слов (из CSV-файла или базы данных),
        а затем извлекает одно слово и его перевод. Также она генерирует список
        неправильных вариантов перевода для использования в качестве кнопок выбора.

        :param message: Объект сообщения от пользователя в Telegram, используемый
                        для получения ID пользователя.

        :return: Кортеж, содержащий выбранное слово (str), его правильный перевод (str),
             список неправильных вариантов перевода (list[str]) и id слова из БД (int).
        """
        id_user = message.from_user.id
        flag = random.randint(0, 2)
        logger.debug(f'def word_generator:flag {flag}')
        if flag == 0:
            word_dict = self.read_words_csv(id_user)

        elif flag == 1:
            word_dict = self.read_words_bd_added_user(id_user)

        else:
            word_dict = self.read_words_bd(id_user)

        logger.debug(f'def word_generator:word_dict {word_dict}')

        try:
            word = list(word_dict.keys())[0]
            translation = word_dict[word][0]
            id_word = word_dict[word][1]
            text_buttons = [item[0] for item in list(word_dict.values())[1:]]
            return word, translation, text_buttons, id_word

        except Exception as e:
            logger.error(f'Ошибка при генерации слов: {e}')

            word_dict = self.get_fallback_words()
            word = list(word_dict.keys())[0]
            translation = word_dict[word]
            id_word_db = self.db.search_word(word)
            text_buttons = list(word_dict.values())[1:]
            return word, translation, text_buttons, id_word_db

    def read_words_csv(self, user_id: int, quantity: int = 4) -> dict:
        """
            Читает указанное количество уникальных слов из CSV-файла,
            проверяет их на дубликаты в базе данных, сохраняет найденные слова вместе
            с их английскими переводами в словаре и удаляет выбранные слова из CSV-файла.

            :param user_id: ID пользователя в Telegram.
            :param quantity: Необязательный параметр, определяющий требуемое количество слов
                             для чтения (по умолчанию 4).

            :return words_dict: dict Словарь, содержащий русские слова в качестве ключей
                                и их английские переводы в качестве значений.
        """
        logger.debug('запускается read_words_csv')
        words_dict = {}
        try:
            with open('russian_english_words.csv', newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                words = list(reader)

            selected_words = random.sample(words[1:],
                                           len(words[1:]) if len(words[1:]) < quantity else quantity)

            for word_list in selected_words:
                id_word = self.db.search_word(word_list[0])
                if id_word is None:
                    id_word = self.db.save_word(word_list[0], word_list[1])

                words_dict[word_list[0]] = [word_list[1], id_word]

            if len(words_dict) < quantity:
                result = self.read_words_bd(user_id, quantity - len(words_dict))
                words_dict.update(result)

            remaining_words = [word for word in words if word not in selected_words]
            with open('russian_english_words.csv', 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                for word in remaining_words:
                    writer.writerow(word)

            return words_dict

        except Exception as e:
            logger.error(f'ошибка при чтении CSV файла {e}')
            words_dict.update(self.read_words_bd(user_id, quantity))
            return words_dict

    def read_words_bd(self, user_id, quantity: int = 4) -> dict:
        """
        Запрашивает слова с переводом из базы данных.

        Эта функция запрашивает слова, которые пользователь еще не видел 4 раза,
        из базы данных. Если найденных слов меньше необходимого количества,
        оставшиеся слова выбираются из CSV-файла.

        :param user_id: ID пользователя в Telegram.
        :param quantity: Необязательный параметр, определяющий требуемое количество слов
                             для чтения (по умолчанию 4).

        :return: dict Словарь, содержащий русские слова в качестве ключей и их
                 английские переводы в качестве значений.
        """
        logger.debug('запускается read_words_bd')
        result = self.db.get_random_words_for_user(user_id, quantity)

        if len(result) < quantity:
            csv_word = self.read_words_csv(user_id, quantity - len(result))
            result.update(csv_word)
        return result

    def read_words_bd_added_user(self, user_id) -> dict:
        """
        Запрашивает слова с переводом из базы данных добавленные пользователем.

        Эта функция запрашивает слова, которые добавил пользователь и еще не видел 4 раза,
        из базы данных. Если найденных слов меньше необходимого количества,
        оставшиеся слова выбираются из CSV-файла.

        :param user_id: ID пользователя в Telegram.

        :return: dict Словарь, содержащий русские слова в качестве ключей и их
                 английские переводы в качестве значений.
        """
        logger.debug('запускается read_words_bd_added_user')
        result = self.db.get_random_words_for_user(user_id, flag=True)

        if len(result) < 4:
            bd_word = self.read_words_bd(user_id, 4 - len(result))
            result.update(bd_word)
        return result

    def display_player_rating(self, telegram_user_id) -> str:
        """
            Отображает рейтинг игроков с учетом позиции запрашивающего пользователя.

            В зависимости от позиции пользователя в рейтинге:
            - Если пользователь в топ-3, отображаются первые три места.
            - Если пользователь на 4 или 5 месте, отображаются его место и предыдущее.
            - Если пользователь на 6 месте или ниже, отображаются топ-3, многоточие и его место.

            :param telegram_user_id: Идентификатор пользователя в Telegram.

            :return: Сообщение с рейтингом для отправки пользователю.
        """
        msg = ''
        rating_data = self.db.get_player_ratings()
        user_position = None
        for idx, user in enumerate(rating_data):
            if user['telegram_user_id'] == telegram_user_id:
                user_position = idx + 1
                break

        if user_position:
            if user_position <= 3:
                for idx, user in enumerate(rating_data[:3]):
                    msg += self._format_rating_entry(user_position, idx + 1, user)

            elif user_position in [4, 5]:
                for idx, user in enumerate(rating_data[:user_position]):
                    msg += self._format_rating_entry(user_position, idx + 1, user)

            else:
                for idx, user in enumerate(rating_data[:3]):
                    msg += f'{self._get_medal(idx + 1)} {user["name"]} - "{user["points"]} очков"\n'
                msg += '...\n'
                msg += f'<b>\t{user_position}.{rating_data[user_position - 1]["name"]} - ' \
                       f'"{rating_data[user_position - 1]["points"]} очков"</b>'
        else:
            msg += 'Пользователь не найден в рейтинге.'
        return msg

    def _format_rating_entry(self, user_position: int, idx: int, user: dict) -> str:
        """
            Форматирует запись рейтинга с учетом позиции пользователя.

            :param user_position: Позиция пользователя в рейтинге.
            :param idx: Текущая обрабатываемая позиция в рейтинге.
            :param user: Словарь с данными пользователя (имя и очки).

            :return: Форматированная строка для отображения в рейтинге.
        """
        if user_position == idx:
            msg = f'<b>{self._get_medal(idx)} {user["name"]} - "{user["points"]} очков"</b>\n'
        else:
            msg = f'{self._get_medal(idx)} {user["name"]} - "{user["points"]} очков"\n'
        return msg

    def _get_medal(self, idx: int) -> str:
        """
            Возвращает соответствующий медаль-эмодзи для первых трех мест или номер позиции.

            :param idx: Позиция в рейтинге.

            :return: Эмодзи медали для первых трех мест или номер позиции.
        """
        if idx == 1:
            result = '🥇'
        elif idx == 2:
            result = '🥈'
        elif idx == 3:
            result = '🥉'
        else:
            result = f'{idx}.'
        return result

    def get_fallback_words(self, quantity: int = 4) -> dict:
        """
        Возвращает резервный набор слов из 20 русско-английских пар.

        Эта функция выбирает 4 случайных слова из этого набора, проверяет их наличие
        в базе данных,
        и, если слово отсутствует, сохраняет его в базу данных.

        :param quantity: Необязательный параметр, определяющий требуемое количество слов
                             для чтения (по умолчанию 4).

        :return: dict Словарь, содержащий русские слова в качестве ключей и их английские
                 переводы в качестве значений.
        """
        logger.debug('запуск резервного списка')
        fallback_words = {
            'кот': 'cat',
            'собака': 'dog',
            'молоко': 'milk',
            'хлеб': 'bread',
            'яблоко': 'apple',
            'машина': 'car',
            'дом': 'house',
            'окно': 'window',
            'дерево': 'tree',
            'книга': 'book',
            'ручка': 'pen',
            'стол': 'table',
            'стул': 'chair',
            'часы': 'clock',
            'зонт': 'umbrella',
            'солнце': 'sun',
            'луна': 'moon',
            'звезда': 'star',
            'рыба': 'fish',
            'птица': 'bird'
        }
        selected_words = random.sample(list(fallback_words.items()), quantity)
        words_dict = {}

        for word, translation in selected_words:
            check_word_bd = self.db.search_word(word)
            if check_word_bd is None:
                self.db.save_word(word, translation)
            words_dict[word] = translation

        return words_dict


class DatabaseUtils(Database):
    """
       Класс для управления базой данных, наследующий методы и свойства из класса Database.
    """

    def __init__(self):
        super().__init__()

    def add_tabl(self):
        """
           Создает необходимые таблицы в базе данных:
           - users: информация о пользователях.
           - word: информация о словах и их переводах.
           - users_word: связь пользователей и слов, а также количество показов каждого слова.
       """
        table_name_user = 'users'
        columns_user = [
            ('id', 'SERIAL PRIMARY KEY'),
            ('telegram_user_id', 'BIGINT NOT NULL UNIQUE'),
            ('name', 'VARCHAR(255)'),
            ('points', 'INTEGER DEFAULT 0')
        ]

        table_name_word = 'word'
        columns_word = [
            ('id', 'SERIAL PRIMARY KEY'),
            ('user_id', 'BIGINT DEFAULT NULL'),
            ('russian_words', 'VARCHAR(255)'),
            ('translation', 'VARCHAR(255)'),

        ]

        table_name_user_word = 'users_word'
        columns_user_word = [
            ('id', 'SERIAL PRIMARY KEY'),
            ('user_id', 'INTEGER REFERENCES users(id) ON DELETE CASCADE'),
            ('word_id', 'INTEGER REFERENCES word(id) ON DELETE CASCADE'),
            ('times_shown', 'INTEGER DEFAULT 0')
        ]

        self.create_table(table_name_user, columns_user)
        self.create_table(table_name_word, columns_word)
        self.create_table(table_name_user_word, columns_user_word)

    def save_user(self, name: str, tg_user_id: int):
        """
        Сохраняет информацию о пользователе в базе данных.

        Функция сохраняет имя пользователя и его уникальный идентификатор в Телеграме
        в таблицу `users` базы данных.

        :param name: str Имя пользователя, указанное в Телеграме.
        :param tg_user_id: int Идентификатор пользователя в Телеграме.
        """
        table_name = 'users'
        data = {
            'telegram_user_id': tg_user_id,
            'name': name
        }
        self.insert_data(table_name=table_name, data=data)

    def search_user(self, tg_user_id: int) -> dict:
        """
        Ищет информацию о пользователе в базе данных по его Telegram ID.

        Функция выполняет запрос в таблицу `users`, чтобы найти пользователя по его
        идентификатору в Телеграме. Если пользователь найден, возвращает словарь с
        информацией о пользователе (ID, имя, очки). В противном случае возвращает `None`.

        :param tg_user_id: int Идентификатор пользователя в Телеграме.

        :return: dict Словарь с информацией о пользователе (ID, имя, очки) или `None`,
                      если пользователь не найден.
        """
        table_name = 'users'
        columns = 'id,name,points'
        values = (tg_user_id,)
        condition = 'telegram_user_id = %s'
        result = self.select_data(table_name=table_name, columns=columns,
                                  values=values, condition=condition)
        if result:
            user_info = {
                'id': result[0][0],
                'name': result[0][1],
                'points': result[0][2]
            }
        else:
            user_info = None
        return user_info

    def search_word(self, word: str, user_id: int = None) -> int | None:
        """
        Ищет слово в базе данных.

        Функция выполняет запрос в таблицу `word`, чтобы найти слово по его русскому написанию.
        Если передан параметр `user_id`, функция будет искать слова,
            добавленные конкретным пользователем.
        Если слово найдено, возвращает его ID. В противном случае возвращает `None`.

        :param word: str Слово на русском языке, которое нужно найти.
        :param user_id: int Не обязательный параметр id пользователя в телеграмме.
                        По умолчанию None.

        :return: int Идентификатор слова в базе данных или `None`, если слово не найдено.
        """
        table_name = 'word'
        condition = 'russian_words = %s '
        values = (word,)

        if user_id is not None:
            condition += 'AND user_id = %s'
            values = (word, user_id)
        else:
            condition += 'AND user_id IS NULL'

        result = self.select_data(table_name, 'id',
                                  condition=condition, values=values)
        if result:
            answer = result[0][0]
        else:
            answer = None
        return answer

    def save_word(self, word: str, translation: str, user_id: int = None):
        """
        Сохраняет слово и его перевод в базе данных.

        Функция сохраняет переданные параметры `word` (русское слово) и
        `translation` (английский перевод) в таблицу `word` базы данных.
        Если передан необязательный параметр `user_id` (id пользователя в Telegram),
        он также будет сохранен для данной записи.

        :param word: str Слово на русском языке.
        :param translation: str Перевод слова на английский язык.
        :param user_id: int Не обязательный параметр id пользователя в телеграмме.
                        По умолчанию None.
        """
        data = {
            'russian_words': word,
            'translation': translation
        }
        if user_id is not None:
            data['user_id'] = user_id

        table_name = 'word'
        result = self.insert_data(table_name, data)
        return result

    def get_random_words_for_user(self, user_id: int, quantity: int = 4,
                                  flag: bool = False) -> dict:
        """
        Получает случайные слова для пользователя, которые показывались ему менее 4 раз,
            и возвращает их в виде словаря.

        Функция извлекает из базы данных слова, которые пользователю еще
            не показывались 4 и более раз.
        Количество выбираемых слов можно задать через параметр `quantity` (по умолчанию 4).
        Если `flag` установлен в `True`, выбираются только слова, добавленные самим пользователем.
        Если `flag` равен `False`, выбираются слова из общего списка.

        Результат возвращается в виде словаря, где ключами являются русские слова,
            а значениями — список из перевода на английский язык и id слов в БД.

        :param user_id: int Идентификатор пользователя в базе данных.
        :param quantity: int Количество случайных слов для выбора (по умолчанию 4).
        :param flag: bool Указывает, выбирать ли слова, добавленные самим пользователем (`True`),
                     или из общего списка (`False`).

        :return: dict Словарь с выбранными словами, где ключами являются русские слова,
                     а значениями — список из перевода на английский язык и id слов в БД.
        """
        user_condition = f'AND w.user_id = {user_id}' if flag else 'AND w.user_id IS NULL'

        words_dict = {}
        table_name = 'word w'
        columns = 'w.russian_words, w.translation, w.id'
        condition = f"""
            w.id NOT IN (
                SELECT uw.word_id
                FROM users_word uw
                WHERE uw.user_id = (
                        SELECT u.id
                        FROM users u
                        WHERE u.telegram_user_id = {user_id}
                    
                        )
                GROUP BY uw.word_id
                HAVING SUM(uw.times_shown) >= 4
            )
            {user_condition}
            ORDER BY RANDOM()
            LIMIT {quantity};        
        """
        result_bd_word = self.select_data(table_name=table_name,
                                          columns=columns,
                                          condition=condition
                                          )
        for words in result_bd_word:
            words_dict[words[0]] = [words[1], words[2]]
        return words_dict

    def update_points(self, user_id: int, points: int, add=True):
        """
            Обновляет количество очков пользователя.

            :param user_id: ID пользователя, для которого обновляются очки.
            :param points: Количество очков для добавления или вычитания.
            :param add: Флаг, указывающий, добавлять (True) или вычитать (False) очки.
        """
        if add:
            data = {'points': f'points + {points}'}
        else:
            data = {'points': f'points - {points}'}

        table_name = 'users'
        condition = f'users.telegram_user_id = {user_id}'
        self.update_data(table_name=table_name, data=data, condition=condition)

    def update_times_shown(self, telegram_user_id: int, word_id: int):
        """
        Обновляет количество показов слова для пользователя.

        :param telegram_user_id: ID пользователя в Telegram.
        :param word_id: ID слова.
        """
        table_name = 'users_word uw'
        columns = 'uw.id'
        condition = """ uw.word_id = %s
                            AND uw.user_id = (
                                SELECT u.id 
                                FROM users AS u
                                WHERE u.telegram_user_id = %s
                            );
                    """
        values = (word_id, telegram_user_id)
        user_word_id = self.select_data(table_name=table_name, columns=columns,
                                        condition=condition, values=values)
        if user_word_id:
            data = {'times_shown': 'times_shown + 1'}
            condition = 'id = %s'
            values = (user_word_id[0][0],)
            self.update_data(table_name=table_name[:-3], data=data,
                             condition=condition, values=values)
        else:
            user_id = self.select_data(table_name='users', columns='id',
                                       condition='telegram_user_id = %s',
                                       values=(telegram_user_id,))

            data = {
                'user_id': user_id[0][0],
                'word_id': word_id,
                'times_shown': 1
            }
            self.insert_data(table_name='users_word', data=data)

    def get_player_ratings(self) -> list:
        """
            Получает рейтинг игроков на основе их очков.

            Функция выполняет запрос к базе данных для получения списка игроков,
            отсортированного по количеству очков в порядке убывания. Возвращает
            результат в виде списка, где каждый элемент содержит идентификатор пользователя
            в Telegram, имя и количество очков.

            :return: list Список кортежей с информацией о пользователях,
                          отсортированный по убыванию очков.
        """
        table_name = 'users ORDER BY points DESC'
        columns = 'telegram_user_id, name, points'

        result = self.select_data(table_name=table_name, columns=columns)
        rating_list = [{'telegram_user_id': row[0], 'name': row[1],
                        'points': row[2]} for row in result]
        return rating_list

    def get_user_word(self, user_id: int) -> dict:
        """
        Извлекает список слов, добавленных пользователем в базу данных.

        Эта функция запрашивает слова, которые были добавлены указанным пользователем
        в базу данных, и возвращает их в виде списка.

        :param user_id: Идентификатор пользователя в Telegram.

        :return dict: Словарь слов на русском языке и количество повторений
                    добавленных пользователем в базу данных.
        """
        words = {}
        table_name = 'word w LEFT JOIN users_word uw ON w.id = uw.word_id'
        columns = 'w.russian_words, uw.times_shown'
        condition = 'w.user_id = %s'
        values = (user_id,)

        result = self.select_data(table_name=table_name, columns=columns,
                                  condition=condition, values=values)

        for word in result:
            words[word[0]] = word[1]

        return words

    def delete_word(self, word: str, user_id: int) -> bool:
        """
        Удаляет указанное слово для конкретного пользователя из базы данных.

        Эта функция удаляет слово на русском языке из таблицы `word`, если оно
        принадлежит указанному пользователю. Если удаление прошло успешно,
        функция возвращает `True`, в противном случае — `False`.

        :param word: str Слово на русском языке, которое нужно удалить.
        :param user_id: int Идентификатор пользователя, которому принадлежит слово.

        :return: bool Возвращает `True`, если слово успешно удалено, и `False` в противном случае.
        """
        table_name = 'word'
        condition = 'russian_words = %s AND user_id = %s'
        values = (word, user_id)

        result = self.delete_data(table_name=table_name, condition=condition, values=values)

        return result


if __name__ == '__main__':
    r = DatabaseUtils()
    print(r.get_player_ratings())
