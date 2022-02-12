import json
import logging
import math
import os
import shutil
import time
from threading import Thread
import requests
import sf_database
import tools
from modules.admlist_module import parse_title

requestURL = 'http://admlist.ru/fio/{0}.json?nocache=1'

SAVE_PATH = 'admlist/students'
SAVE_NAME = SAVE_PATH + '/{0}.json'

logging.basicConfig(format='[%(asctime)s] [%(levelname)s]: %(message)s', level=logging.INFO)


def check_conditions():
    try:
        logging.info('Подготовка рабочей области students_fetcher...')

        if os.path.exists(SAVE_PATH):
            shutil.rmtree(SAVE_PATH)

        time.sleep(0.2)
        os.mkdir(SAVE_PATH)

    except Exception as e:
        logging.error(f'Не удалось подготовить рабочую область: {e}')
        raise e


def try_prepare_conditions():
    successful = False
    repeats = 0

    while not successful:
        try:
            check_conditions()
            successful = True

        except Exception as e:
            repeats += 1

            if repeats >= 5:
                raise e
            else:
                logging.warning(f'Повтор ({repeats}/5)...')

            time.sleep(2)


def clean_temp():
    try:
        logging.info('*** Очистка временных файлов Admlist.ru ***')

        if os.path.exists(SAVE_PATH):
            shutil.rmtree(SAVE_PATH)

    except Exception as e:
        logging.error(f'Не удалось очистить временные файлы: {e}')
        raise e


def format_admissions(admissions):
    result = []

    for admission in admissions:
        info = {}

        title = admission[1]

        if '<b>' in title:
            title = title.replace('<b>', '').replace('</b>', '')
            info['consent'] = True
        else:
            info['consent'] = False

        parsed = parse_title(title)

        speciality_name = ''
        codes = parsed['speciality_code']
        names = parsed['speciality_name']
        edu_program = parsed['edu_program']

        for i in range(0, len(codes)):
            speciality_name += codes[i] + ' ' + names[i]

            if i != len(codes) - 1:
                speciality_name += ' / '

        if edu_program != '-':
            speciality_name += ' (' + edu_program + ')'

        info['university_name'] = parsed['university_name']
        info['faculty_name'] = parsed['faculty_name']
        info['speciality_name'] = speciality_name
        info['extra_data'] = parsed['other_stuff']
        info['speciality_link'] = admission[0]

        result.append(info)

    return result


class DownloadThread(Thread):

    def __init__(self, num, start_pos, end_pos):
        Thread.__init__(self)

        self.num = num
        self.start_pos = start_pos
        self.end_pos = end_pos

    def run(self):

        logging.info(f'Поток #{self.num} запущен!')
        workload = self.end_pos - self.start_pos
        # connection = sf_database.open_database()

        msg_step = 15
        curr_line = msg_step

        for i in range(self.start_pos, self.end_pos + 1):
            json_name = "%x" % i

            if len(json_name) == 1:
                json_name = '0' + json_name

            url = requestURL.format(json_name)

            successful = False
            repeats = 0

            filename = SAVE_NAME.format(json_name)

            while not successful:
                try:
                    r_json = requests.get(url).json()
                    new_json = {}

                    for student_hash, admissions in r_json.items():
                        try:
                            form_admissions = format_admissions(admissions)
                        except Exception as e:
                            logging.info(admissions)
                            raise e

                        new_json[student_hash] = form_admissions

                        #hash_info = sf_database.HashInfo(student_hash, form_admissions)
                        #sf_database.write_to_database(connection, hash_info)

                    with open(filename, 'w') as file:
                        json.dump(new_json, file)

                    successful = True

                except Exception as e:
                    repeats += 1
                    # connection.rollback()

                    if os.path.isfile(filename):
                        os.remove(filename)

                    if repeats >= 5:
                        logging.error(f'Поток #{self.num} - не удалось выполнить задачу: {e}')
                        return
                    else:
                        logging.warning(f'Поток #{self.num} - не удалось загрузить и сохранить файл ({repeats}/5). '
                                        f'Причина: {e}')

                    time.sleep(2)

            # calculate current progress
            curr = i - self.start_pos
            curr_percentage = round((curr * 100) / workload)

            if curr_percentage >= curr_line:
                logging.info(f'Поток #{self.num} - обработано {curr_percentage}%')
                curr_line += msg_step

        # sf_database.close_database(connection)
        logging.info(f'Поток #{self.num} - готово!')


def download_students():
    logging.info('*** Загрузка базы студентов с Admlist.ru ***')

    thread_count = 8
    workload = math.floor(255 / thread_count)

    threads = []

    for i in range(thread_count):
        if i == 0:
            start_pos = workload * i
        else:
            start_pos = workload * i + 1

        end_pos = workload * (i + 1)

        if end_pos > 255:
            end_pos = 255

        thread = DownloadThread(i + 1, start_pos, end_pos)
        thread.start()

        threads.append(thread)

    for thread in threads:
        thread.join()

    logging.info('Загрузка файлов с admlist.ru завершена!')


def process_students():
    logging.info('*** Обработка файлов ***')

    sf_database.check_database()
    sf_database.create_database()
    connection = sf_database.open_database()

    msg_step = 15
    curr_line = msg_step

    for i in range(0, 255):
        json_name = "%x" % i

        if len(json_name) == 1:
            json_name = '0' + json_name

        filename = SAVE_NAME.format(json_name)

        if not os.path.isfile(filename):
            continue

        with open(filename, 'rb') as json_file:
            data = json.loads(json_file.read().decode('utf-8'))

            for hash, admissions in data.items():
                hash_info = sf_database.HashInfo(hash, admissions)
                sf_database.write_to_database(connection, hash_info)

        # calculate current progress
        curr = i - 0
        curr_percentage = round((curr * 100) / 255)

        if curr_percentage >= curr_line:
            logging.info(f'Обработано {curr_percentage}%')
            curr_line += msg_step

        connection.commit()

    logging.info('Обработка завершена!')
    sf_database.close_database(connection)


def main():
    try_prepare_conditions()
    download_students()
    process_students()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f'Не удалось загрузить базу студентов с admlist.ru: {e}')

    tools.wait_for_exit()
