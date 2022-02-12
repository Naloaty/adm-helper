import logging
import os
import sqlite3
from exceptions import WrongUsage
from exceptions import WriteException

hash_db = 'admlist/hashdb.db'

example_hash = '32c002d9df95a8c7ee04ed87d9277305'

example_admission = {
    'university_name': 'ЮУрГУ',
    'faculty_name': 'Факультет',
    'speciality_name': 'Специальность',
    'consent': True,
    'extra_data': 'шонибудь',
    'speciality_link': 'hse/sisdsadjhajsdjsaks'
}

example_admissions = [
    example_admission
]


def validate_admission(admission):
    if not isinstance(admission, dict):
        raise WrongUsage('список admissions содержит объект, не являющийся словарём')

    for key in example_admission.keys():
        if not (key in admission):
            raise WrongUsage(f'список admissions содержит словарь, не содержащий ключ {key}')


class HashInfo:

    def __init__(self, hash, admissions):
        self.hash = hash
        self.admissions = admissions

    def validate(self):

        if not isinstance(self.admissions, list):
            raise WrongUsage('в HashInfo передан параметр admissions, не являющийся списком')

        if not isinstance(self.hash, str):
            raise WrongUsage(f'в HashInfo передан параметр hash, не являющийся строкой')

        if self.hash == '':
            raise WrongUsage(f'в HashInfo передан пустой параметр hash')


def write_university(connection, university_name):
    cursor = connection.cursor()
    params = (university_name,)
    cursor.execute("""SELECT * FROM universities WHERE name=? LIMIT 1""", params)
    record = cursor.fetchone()

    try:
        if record is not None:
            university_id = record[0]
        else:
            cursor.execute("""INSERT INTO universities(name) VALUES (?)""",
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


def write_speciality(connection, university_id, faculty_id, speciality_name, link):
    cursor = connection.cursor()

    params = (faculty_id, university_id, speciality_name)
    cursor.execute("""SELECT * FROM specialities WHERE faculty_id=? AND university_id=? AND name=? LIMIT 1""", params)
    record = cursor.fetchone()

    params = (faculty_id, university_id, speciality_name, link)

    try:
        if record is not None:
            speciality_id = record[0]
        else:
            cursor.execute("""INSERT INTO specialities(faculty_id, university_id, name, link) VALUES (?, ?, ?, ?)""",
                           params)

            speciality_id = cursor.lastrowid

    except Exception:
        speciality_id = -1

    return speciality_id


# use this method to write HashInfo to database
def write_to_database(connection, info):
    if not (isinstance(info, HashInfo)):
        raise WrongUsage('попытка записи в базу данных не экземпляра класса HashInfo')

    info.validate()
    cursor = connection.cursor()

    # insert hash to db
    cursor.execute("""INSERT INTO hashes(admissions, hash) VALUES (?, ?)""", ('', info.hash))
    hash_id = cursor.lastrowid

    hash_admissions = []

    for admission in info.admissions:
        validate_admission(admission)

        university_id = write_university(connection, admission['university_name'])
        if university_id == -1:
            raise WriteException('не удалось записать университет в базу данных')

        faculty_id = write_faculty(connection, university_id, admission['faculty_name'])
        if faculty_id == -1:
            raise WriteException('не удалось записать факультет в базу данных')

        speciality_id = write_speciality(connection, university_id, faculty_id, admission['speciality_name'],
                                         admission['speciality_link'])
        if speciality_id == -1:
            raise WriteException('не удалось записать специальность в базу данных')

        params = (hash_id, university_id, faculty_id, speciality_id, admission['consent'], admission['extra_data'])

        try:
            cursor.execute("""INSERT INTO admissions(hash_id, university_id, faculty_id, speciality_id, consent, 
            extra_data) VALUES (?, ?, ?, ?, ?, ?)""", params)
            admission_id = cursor.lastrowid

        except Exception:
            raise WriteException('не удалось записать заявление в базу данных')

        hash_admissions.append(admission_id)

    str_admissions = ':'.join(map(str, hash_admissions))
    cursor.execute("""UPDATE hashes SET admissions=? WHERE id=?""", (str_admissions, hash_id))

    byte_map = int(info.hash[0:3] + info.hash[30:32], 16)

    cursor.execute("""SELECT hashes FROM map WHERE byte_map=? LIMIT 1""", (byte_map,))
    hashes = cursor.fetchone()

    if hashes is None:
        updated = str(hash_id)

        cursor.execute("""INSERT INTO map(byte_map, hashes) VALUES (?, ?)""", (byte_map, updated))
    else:
        updated = hashes[0] + ':' + str(hash_id)

        cursor.execute("""UPDATE map SET hashes=? WHERE byte_map=?""", (updated, byte_map))


# use this method to open database
def open_database():
    try:
        logging.info('Подключение к базе данных students_fetcher...')
        conn = sqlite3.connect(hash_db)
        #conn = sqlite3.connect(hash_db, isolation_level=None)
        #conn.execute('pragma journal_mode=wal')
        return conn

    except Exception as e:
        logging.error(f'Не удалось подключиться к базе данных ({e}).')


# use this method to close database
def close_database(connection):
    try:
        logging.info('Отключение от базы данных students_fetcher...')
        connection.close()

    except Exception as e:
        logging.error(f'Не удалось отключиться от базы данных ({e}).')


def check_database():
    if os.path.exists(hash_db):
        try:
            logging.info('Удаление предыдущей базы данных...')
            os.remove(hash_db)
            logging.info('База данных удалена!')
        except Exception as e:
            logging.error(
                f'Не удалось удалить предудущую базу данных ({e}). Удалите файл вручную и повторите попытку.')
    else:
        logging.info('Предудыщая база данных не обнаружена!')


def create_database():
    logging.info('*** Создание новой базы данных ***')

    conn = sqlite3.connect(hash_db)
    cursor = conn.cursor()

    logging.debug('Создание таблицы хешей...')
    cursor.execute(f'CREATE TABLE hashes ('
                   f'id INTEGER PRIMARY KEY,'
                   f'admissions TEXT NOT NULL,'
                   f'hash TEXT NOT NULL)')

    logging.debug('Создание таблицы факультетов...')
    cursor.execute(f'CREATE TABLE faculties ('
                   f'id INTEGER PRIMARY KEY,'
                   f'university_id INTEGER ,'
                   f'name TEXT NOT NULL)')

    logging.debug('Создание таблицы университетов...')
    cursor.execute(f'CREATE TABLE universities ('
                   f'id INTEGER PRIMARY KEY,'
                   f'name TEXT NOT NULL)')

    logging.debug('Создание таблицы специальностей...')
    cursor.execute(f'CREATE TABLE specialities ('
                   f'id INTEGER PRIMARY KEY,'
                   f'faculty_id INTEGER,'
                   f'university_id INTEGER,'
                   f'name TEXT NOT NULL,'
                   f'link TEXT NOT NULL)')

    logging.debug('Создание таблицы заявлений...')
    cursor.execute(f'CREATE TABLE admissions ('
                   f'id INTEGER PRIMARY KEY,'
                   f'hash_id INTEGER,'
                   f'university_id INTEGER,'
                   f'faculty_id INTEGER,'
                   f'speciality_id INTEGER,'
                   f'consent BIT,'
                   f'extra_data)')

    logging.debug('Создание таблицы маппинга...')
    cursor.execute(f'CREATE TABLE map ('
                   f'byte_map INTEGER PRIMARY KEY,'
                   f'hashes TEXT NOT NULL)')

    conn.commit()
    conn.close()

    logging.info('База данных успешно создана!')


def main():
    check_database()
    create_database()

    conn = open_database()
    info = HashInfo(hash=example_hash, admissions=example_admissions)
    write_to_database(conn, info)

    conn.commit()
    close_database(conn)


if __name__ == "__main__":
    main()
