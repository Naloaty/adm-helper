import logging
import os
import sqlite3
from exceptions import WrongUsage
from exceptions import WriteException
from datetime import datetime
import pytz

main_db = 'result/database.db'

example_extra_data = ''

example_general = {
    'name': 'Иванов Иван Иванович',
    'university_id': 1,
    'city_id': 1,
    'faculty_id': 1,
    'speciality_id': 1,
    'consent': False,
    'type': 3
}

example_scores = {
    "subj1": 42,
    "subj2": 42,
    "subj3": 42,
    "achievement": 0
}


class AdmissionInfo:

    def __init__(self, general, scores, extra_data):
        self.general = general
        self.scores = scores
        self.extra_data = extra_data

    def validate(self):

        if not isinstance(self.general, dict):
            raise WrongUsage('в AdmissionInfo передан параметр general, не являющийся словарём')

        if not isinstance(self.scores, dict):
            raise WrongUsage('в AdmissionInfo передан параметр score, не являющийся словарём')

        for key in example_general.keys():
            if not (key in self.general):
                raise WrongUsage(f'в AdmissionInfo передан словарь general, не содержащий ключ {key}')

        for key in example_scores.keys():
            if not (key in self.scores):
                raise WrongUsage(f'в AdmissionInfo передан словарь scores, не содержащий ключ {key}')

        if not isinstance(self.extra_data, str):
            self.extra_data = ''


def write_city(connection, city_name):
    cursor = connection.cursor()
    params = (city_name,)
    cursor.execute("""SELECT * FROM cities WHERE name=? LIMIT 1""", params)
    record = cursor.fetchone()

    try:
        if record is not None:
            city_id = record[0]
        else:
            cursor.execute("""INSERT INTO cities(name) VALUES (?)""", params)
            city_id = cursor.lastrowid

    except Exception:
        city_id = -1

    return city_id


def write_university(connection, city_id, university_name):
    cursor = connection.cursor()
    params = (city_id, university_name)
    cursor.execute("""SELECT * FROM universities WHERE city_id=? AND name=? LIMIT 1""", params)
    record = cursor.fetchone()

    try:
        if record is not None:
            university_id = record[0]
        else:
            cursor.execute("""INSERT INTO universities(city_id, name) VALUES (?, ?)""",
                           params)
            university_id = cursor.lastrowid

    except Exception:
        university_id = -1

    return university_id


def write_faculty(connection, university_id, faculty_name):
    cursor = connection.cursor()
    params = (faculty_name, university_id)
    cursor.execute("""SELECT * FROM faculties WHERE name=? AND university_id=? LIMIT 1""", params)
    record = cursor.fetchone()

    try:
        if record is not None:
            faculty_id = record[0]
        else:
            cursor.execute("""INSERT INTO faculties(name, university_id) VALUES (?, ?)""", params)
            faculty_id = cursor.lastrowid

    except Exception:
        faculty_id = -1

    return faculty_id


def write_speciality(connection, university_id, faculty_id, speciality_name, source):
    cursor = connection.cursor()

    moscow = pytz.timezone('Europe/Moscow')
    now = datetime.now(moscow)
    date_fetched = now.strftime("%Y-%m-%d %H:%M:%S")

    params = (faculty_id, university_id, speciality_name)
    cursor.execute("""SELECT * FROM specialities WHERE faculty_id=? AND university_id=? AND name=? LIMIT 1""", params)
    record = cursor.fetchone()

    params = (faculty_id, university_id, speciality_name, date_fetched, source)

    try:
        if record is not None:
            speciality_id = record[0]
        else:
            cursor.execute("""INSERT INTO specialities(faculty_id, university_id, name, date_fetched, source) 
            VALUES (?, ?, ?, ?, ?)""", params)

            speciality_id = cursor.lastrowid

    except Exception:
        speciality_id = -1

    return speciality_id


# use this method to write AdmissionInfo to database
def write_to_database(connection, info):
    if not (isinstance(info, AdmissionInfo)):
        raise WrongUsage('попытка записи в базу данных не экземпляра класса AdmissionInfo')

    info.validate()
    cursor = connection.cursor()

    # =============== STUDENTS ===============
    cursor.execute("""SELECT * FROM students WHERE name=? LIMIT 1""", (info.general['name'],))
    record = cursor.fetchone()
    first_record = True

    if record is not None:
        student_id = record[0]
        first_record = False

    else:
        cursor.execute("""INSERT INTO students(admissions, name) VALUES (?, ?)""", ('', info.general['name']))
        student_id = cursor.lastrowid

    for i in range(1, 3):
        if not ('subj' + str(i) in info.scores):
            raise WriteException('subj' + str(i))

    if not ('achievement' in info.scores):
        raise WriteException('achievement')

    # =============== ADMISSIONS ===============

    params = (student_id, info.general['university_id'], info.general['faculty_id'], info.general['speciality_id'],
              info.general['consent'], info.general['type'], info.scores['subj1'], info.scores['subj2'],
              info.scores['subj3'], info.scores['achievement'], info.extra_data)

    cursor.execute("""INSERT INTO admissions(student_id, university_id, faculty_id, speciality_id, consent, type, 
                   subject1, subject2, subject3, achievement, extra_data) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
                   , params)

    if first_record:
        updated_adms = cursor.lastrowid
    else:
        updated_adms = f"{record[1]}:{cursor.lastrowid}"

    cursor.execute("""UPDATE students SET admissions=? WHERE id=?""", (updated_adms, student_id))


# use this method to open database
def open_database():
    try:
        logging.info('Подключение к базе данных data_fetcher...')
        conn = sqlite3.connect(main_db)
        return conn

    except Exception as e:
        logging.error(f'Не удалось подключиться к базе данных ({e}).')


# use this method to close database
def close_database(connection):
    try:
        logging.info('Отключение от базы данных data_fetcher...')
        connection.close()

    except Exception as e:
        logging.error(f'Не удалось отключиться от базы данных ({e}).')


def check_database():
    if os.path.exists(main_db):
        try:
            logging.info('Удаление предыдущей базы данных...')
            os.remove(main_db)
            logging.info('База данных удалена!')
        except Exception as e:
            logging.error(
                f'Не удалось удалить предудущую базу данных ({e}). Удалите файл вручную и повторите попытку.')
    else:
        logging.info('Предудыщая база данных не обнаружена!')


def create_database():
    logging.info('*** Создание новой базы данных ***')

    conn = sqlite3.connect(main_db)
    cursor = conn.cursor()

    logging.debug('Создание таблицы студентов...')
    cursor.execute(f'CREATE TABLE students ('
                   f'id INTEGER PRIMARY KEY,'
                   f'admissions TEXT NOT NULL,'
                   f'name TEXT NOT NULL)')

    logging.debug('Создание таблицы факультетов...')
    cursor.execute(f'CREATE TABLE faculties ('
                   f'id INTEGER PRIMARY KEY,'
                   f'university_id INTEGER ,'
                   f'name TEXT NOT NULL)')

    logging.debug('Создание таблицы городов...')
    cursor.execute(f'CREATE TABLE cities ('
                   f'id INTEGER PRIMARY KEY,'
                   f'name TEXT NOT NULL)')

    logging.debug('Создание таблицы университетов...')
    cursor.execute(f'CREATE TABLE universities ('
                   f'id INTEGER PRIMARY KEY,'
                   f'city_id INTEGER,'
                   f'name TEXT NOT NULL)')

    logging.debug('Создание таблицы специальностей...')
    cursor.execute(f'CREATE TABLE specialities ('
                   f'id INTEGER PRIMARY KEY,'
                   f'faculty_id INTEGER,'
                   f'university_id INTEGER,'
                   f'name TEXT NOT NULL,'
                   f'date_fetched TEXT NOT NULL,'
                   f'source TEXT NOT NULL)')

    # types:
    # 0 - ОП (особое право)
    # 1 - Ц (целевой набор)
    # 2 - БВИ (олимпиадники/Без Вступительных Испытаний)
    # 3 - ОК (общий конкурс)
    logging.debug('Создание таблицы заявлений...')
    cursor.execute(f'CREATE TABLE admissions ('
                   f'id INTEGER PRIMARY KEY,'
                   f'student_id INTEGER,'
                   f'university_id INTEGER,'
                   f'faculty_id INTEGER,'
                   f'speciality_id INTEGER,'
                   f'consent BIT,'
                   f'type INTEGER,'
                   f'subject1 INTEGER,'
                   f'subject2 INTEGER,'
                   f'subject3 INTEGER,'
                   f'achievement INTEGER,'
                   f'extra_data)')

    conn.commit()
    conn.close()

    logging.info('База данных успешно создана!')


def main():
    check_database()
    create_database()

    subjects = {
        "subj1": 78,
        "subj2": 77,
        "subj3": 96
    }

    conn = open_database()

    info = AdmissionInfo(general=example_general, scores=example_scores, extra_data='')

    write_to_database(conn, info)

    conn.commit()
    close_database(conn)


if __name__ == "__main__":
    main()
