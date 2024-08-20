"""
Модуль для подключение к бд
"""

import re
import psycopg2
from psycopg2 import sql
from config import DB_PATH


class Database:
    """
    Класс для управления подключением и операциями с базой данных.
    """

    def __init__(self, dbname=DB_PATH['dbname'], user=DB_PATH['user'], password=DB_PATH['password'], host='localhost',
                 port=5432):
        """
        Инициализация соединения с базой данных.

        :param dbname: Имя базы данных.
        :param user: Имя пользователя базы данных.
        :param password: Пароль пользователя базы данных.
        :param host: Хост базы данных (по умолчанию 'localhost').
        :param port: Порт базы данных (по умолчанию 5432).
        """
        self.conn = None
        self.cur = None
        try:
            self.conn = psycopg2.connect(dbname=dbname, user=user,
                                         password=password, host=host, port=port)
            self.cur = self.conn.cursor()
            print(f"Соединение с {dbname} успешно")
        except psycopg2.OperationalError:
            print(f"Ошибка подключения к {dbname}")

    def __del__(self):
        """Закрытие соединения и курсора при уничтожении объекта."""
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()

    def create_table(self, table_name: str, columns: list | tuple):
        """
        Создание таблицы в базе данных.

        :param table_name: Имя таблицы.
        :param columns: Список столбцов и их типов
        в формате [('название_столбца', 'тип_данных'), ...].
        """
        try:
            columns_str = ', '.join(f'{col[0]} {col[1]}' for col in columns)
            query = sql.SQL(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_str})")
            self.cur.execute(query)
            self.conn.commit()
            print(f"Таблица {table_name} успешно создана")
        except psycopg2.DatabaseError as e:
            print(f"Ошибка при создании таблицы {table_name}: {e}")

    def drop_table(self, table_name: str):
        """
        Удаление таблицы из базы данных.

        :param table_name: Имя таблицы.
        """
        try:
            query = sql.SQL(f"DROP TABLE IF EXISTS {table_name}")
            self.cur.execute(query)
            self.conn.commit()
            print(f'Таблица успешно удалена {table_name}')
        except psycopg2.DatabaseError as e:
            print(f"Ошибка при удалении таблицы {table_name}: {e}")

    def insert_data(self, table_name: str, data: dict):
        """
        Вставка данных в таблицу.

        :param table_name: Имя таблицы.
        :param data: Словарь с данными для вставки
        в формате {'column1': value1, 'column2': value2, ...}.
        :return: ID вставленной записи.
        """
        try:
            columns = data.keys()
            values = data.values()
            query = sql.SQL(
                f"INSERT INTO {table_name} ({', '.join(columns)})"
                f" VALUES ({', '.join(['%s'] * len(values))}) RETURNING id"
            )
            self.cur.execute(query, list(values))
            inserted_id = self.cur.fetchone()[0]
            self.conn.commit()
            return inserted_id
        except psycopg2.DatabaseError as e:
            print(f"Ошибка при вставке данных в таблицу {table_name}: {e}")
            return None

    def select_data(self, table_name, columns: str = '*',
                    condition: str = None, values: tuple = None):
        """
        Выполнение SELECT-запроса.

        :param table_name: Имя таблицы.
        :param columns: Список столбцов для выборки, по умолчанию '*' - все столбцы.
        :param condition: Условие WHERE для фильтрации данных, строка SQL.
        :param values: Значения для подстановки в условие WHERE, кортеж.
        :return: Список кортежей с данными.
        """
        try:
            columns_str = ', '.join(columns) if isinstance(columns, list) else columns
            query = sql.SQL(f"SELECT {columns_str} FROM {table_name}")
            if condition:
                query += sql.SQL(f" WHERE {condition}")
            self.cur.execute(query, values)
            rows = self.cur.fetchall()
            return rows
        except psycopg2.DatabaseError as e:
            print(f"Ошибка при выполнении SELECT из таблицы {table_name}: {e}")
            return []

    def update_data(self, table_name: str, data: dict, condition: str, values: tuple = None):
        """
        Обновление данных в таблице.

        :param table_name: Имя таблицы.
        :param data: Словарь с данными для обновления
        в формате {'column1': value1, 'column2': value2, ...}. Если value1 это строка,
        которая содержит арифметическое выражение (например, "column + 1"),
        то она будет использована напрямую в SQL-запросе.
        :param condition: Условие WHERE для фильтрации записей, строка SQL.
        :param values: Необязательный параметр. Значения для подстановки в условие WHERE, кортеж.
        :return: True, если обновление прошло успешно, иначе False.
        """
        try:
            set_clause = []
            query_values = []

            for column, value in data.items():
                # Проверка на арифметическое выражение
                if isinstance(value, str) and any(op in value for op in ['+', '-', '*', '/']):
                    set_clause.append(f"{column} = {value}")
                else:
                    set_clause.append(f"{column} = %s")
                    query_values.append(value)

            query = sql.SQL(f"UPDATE {table_name} SET {', '.join(set_clause)} WHERE {condition}")

            if values:
                query_values.extend(values)


            self.cur.execute(query, query_values)
            self.conn.commit()
            print(f'Обновление в таблице {table_name} прошло успешно')
            return True
        except psycopg2.DatabaseError as e:
            print(f"Ошибка при обновлении данных в таблице {table_name}: {e}")
            return False


if __name__ == '__main__':
    r = Database()
