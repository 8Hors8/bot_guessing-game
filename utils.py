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
from buttons import translation_buttons, start_button
from btn_text import VIEW_RATING

logger = logging.getLogger('utils')
config_logging()


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
        word, correct_translation, text_buttons = self.word_generator(message)

        text_buttons.append(correct_translation)
        id_word_db = self.db.search_word(word)
        markup = translation_buttons(text_buttons)

        self.bot.send_message(chat_id, f"Как перевести слово '<b>{word}</b>'?",
                              reply_markup=markup, parse_mode="HTML")

        self.bot.register_next_step_handler_by_chat_id(chat_id, self.check_answer,
                                                       id_word_db, correct_translation)

    def check_answer(self, message, id_word, correct_translation):
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
        elif user_answer == VIEW_RATING:
            result = self.display_player_rating(user_id)
            self.bot.send_message(chat_id, result, parse_mode='HTML')
            self.bot.send_message(chat_id, 'Дя продолжения нажмите кнопку',
                                  reply_markup=start_button())
        else:
            self.bot.send_message(chat_id, "Не совсем так. Но не отчаивайтесь! 💔 -3 балла!")
            self.db.update_points(user_id, 3, add=False)
            self.start_game(message)

    def word_generator(self, message):
        """
        Генерирует слова для перевода и соответствующие варианты перевода.

        Эта функция выбирает случайный источник слов (из CSV-файла или базы данных),
        а затем извлекает одно слово и его перевод. Также она генерирует список
        неправильных вариантов перевода для использования в качестве кнопок выбора.

        :param message: Объект сообщения от пользователя в Telegram, используемый
                        для получения ID пользователя.

        :return: Кортеж, содержащий выбранное слово, его правильный перевод и
                 список неправильных вариантов перевода.
        """
        id_user = message.from_user.id
        flag = random.randint(0, 1)
        if flag == 0:
            word_dicr = self.read_words_csv(id_user)

        else:
            word_dicr = self.read_words_bd(id_user)

        word = list(word_dicr.keys())[0]
        translation = word_dicr[word]
        text_buttons = list(word_dicr.values())[1:]
        return word, translation, text_buttons

    def read_words_csv(self, user_id: int, quantity: int = 4):
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
        words_dict = {}
        try:
            with open('russian_english_words.csv', newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                words = list(reader)

            selected_words = random.sample(words[1:],
                                           len(words[1:]) if len(words[1:]) < quantity else quantity)

            for word_list in selected_words:
                check_word_bd = self.db.search_word(word_list[0])
                if check_word_bd is None:
                    self.db.save_word(word_list[0], word_list[1])

                words_dict[word_list[0]] = word_list[1]

            if len(words_dict) < quantity:
                result = self.db.get_random_words_for_user(user_id, quantity - len(words_dict))
                words_dict.update(result)

            remaining_words = [word for word in words if word not in selected_words]
            with open('russian_english_words.csv', 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                for word in remaining_words:
                    writer.writerow(word)

            return words_dict

        except Exception as e:
            logger.error(f'ошибка {e}')
            words_dict.update(self.read_words_bd(user_id))
            return words_dict

    def read_words_bd(self, user_id):
        """
        Запрашивает слова с переводом из базы данных.

        Эта функция запрашивает слова, которые пользователь еще не видел 4 раза,
        из базы данных. Если найденных слов меньше необходимого количества,
        оставшиеся слова выбираются из CSV-файла.

        :param user_id: ID пользователя в Telegram.

        :return: dict Словарь, содержащий русские слова в качестве ключей и их
                 английские переводы в качестве значений.
        """
        result = self.db.get_random_words_for_user(user_id)

        if len(result) < 4:
            csv_word = self.read_words_csv(user_id, 4 - len(result))
            result.update(csv_word)
        return result

    def display_player_rating(self, telegram_user_id):
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

    def _format_rating_entry(self, user_position, idx, user):
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

    def _get_medal(self, idx):
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

    def save_user(self, name, tg_user_id):
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

    def search_user(self, tg_user_id):
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

    def search_word(self, word):
        """
        Ищет слово в базе данных.

        Функция выполняет запрос в таблицу `word`, чтобы найти слово по его русскому написанию.
        Если слово найдено, возвращает его ID. В противном случае возвращает `None`.

        :param word: str Слово на русском языке, которое нужно найти.

        :return: int Идентификатор слова в базе данных или `None`, если слово не найдено.
        """
        table_name = 'word'
        condition = 'russian_words = %s'

        result = self.select_data(table_name, 'id',
                                  condition=condition, values=(word,))
        if result:
            answer = result[0][0]
        else:
            answer = None
        return answer

    def save_word(self, word, translation):
        """
        Сохраняет слово и его перевод в базе данных.

        Функция сохраняет русское слово и его английский перевод в таблицу `word` базы данных.

        :param word: str Слово на русском языке.
        :param translation: str Перевод слова на английский язык.
        """
        data = {
            'russian_words': word,
            'translation': translation
        }
        table_name = 'word'
        self.insert_data(table_name, data)

    def get_random_words_for_user(self, user_id: int, quantity: int = 4):
        """
            Извлекает случайные слова для указанного пользователя, которые были показаны менее
            4 раз, и возвращает их в виде словаря.

            Функция выбирает слова, которые еще не были показаны пользователю 4 и более раз,
            и ограничивает выбор указанным количеством (по умолчанию 4).
            Результаты выбираются случайным образом и возвращаются в виде словаря,
            где ключами являются слова на русском языке, а значениями их переводы на английский.

            :param user_id: int Идентификатор пользователя в базе данных.
            :param quantity: int Количество случайных слов для выбора (по умолчанию 4).

            :return: dict Словарь с выбранными словами, где ключами являются русские слова,
                   а значениями их переводы на английский.
        """

        words_dict = {}
        table_name = 'word w'
        columns = 'w.russian_words, w.translation'
        condition = f"""
            w.id NOT IN (
                SELECT uw.word_id
                FROM users_word uw
                WHERE uw.user_id = {user_id}
                GROUP BY uw.word_id
                HAVING SUM(uw.times_shown) >= 4
            )
            ORDER BY RANDOM()
            LIMIT {quantity};        
        """

        result_bd_word = self.select_data(table_name=table_name,
                                          columns=columns,
                                          condition=condition
                                          )
        for words in result_bd_word:
            words_dict[words[0]] = words[1]

        return words_dict

    def update_points(self, user_id, points: int, add=True):
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

    def update_times_shown(self, telegram_user_id, word_id: int):
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

    def get_player_ratings(self):
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
        rating_list = [{'telegram_user_id': row[0], 'name': row[1], 'points': row[2]} for row in result]
        return rating_list


if __name__ == '__main__':
    r = DatabaseUtils()
    print(r.get_player_ratings())
