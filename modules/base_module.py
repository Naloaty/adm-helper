import time

import df_database
from exceptions import CriticalException, Unsupported
from df_database import WrongUsage
from df_database import WriteException
import logging


class IncompleteModule(BaseException):
    pass


class BaseModule:

    def __init__(self, university_name, city_name):
        self.connection = df_database.open_database()
        self.university_name = university_name
        self.city_name = city_name

        city_id = df_database.write_city(self.connection, city_name)
        university_id = df_database.write_university(self.connection, city_id, university_name)

        adm_info = {
            'city_id': city_id,
            'university_id': university_id
        }

        for key, value in adm_info.items():
            if value == -1:
                df_database.close_database(self.connection)
                raise WriteException(f'ошибка записи параметра {key} в базу данных')

        self.adm_info = adm_info

    # use this method to write fetched admissions to database
    def write_admission(self, admission):
        if 'faculty_id' not in self.adm_info:
            df_database.close_database(self.connection)
            raise IncompleteModule('метод set_faculty_name не вызван')

        if 'speciality_id' not in self.adm_info:
            df_database.close_database(self.connection)
            raise IncompleteModule('метод set_speciality_name не вызван')

        admission.general['city_id'] = self.adm_info['city_id']
        admission.general['university_id'] = self.adm_info['university_id']
        admission.general['faculty_id'] = self.adm_info['faculty_id']
        admission.general['speciality_id'] = self.adm_info['speciality_id']

        try:
            df_database.write_to_database(self.connection, admission)

        except WriteException as e:
            logging.warning(f'Не удалось записать студента в базу данных ({admission.name}). Ошибка связана с '
                            f'параметром {e}.')
            df_database.close_database(self.connection)
            raise CriticalException

    def work_done(self):
        df_database.close_database(self.connection)

    def pull_to_database(self, sources):
        for source in sources:
            try:
                successful = False
                repeats = 0

                while not successful:
                    try:
                        self.process_source(source=source)
                        successful = True

                    except Exception as e:
                        repeats += 1

                        if repeats >= 5:
                            raise e
                        else:
                            logging.warning(f'Не удалось обработать источник ({repeats}/5). Причина: {e}. Повтор...')

                        time.sleep(2)

            except Exception as e:
                logging.warning(f'Не удалось обработать данный источник: {e}. Пропуск...')
                continue

            self.connection.commit()

            if 'faculty_id' not in self.adm_info:
                df_database.close_database(self.connection)
                raise IncompleteModule('метод set_faculty_name не вызван')

            if 'speciality_id' not in self.adm_info:
                df_database.close_database(self.connection)
                raise IncompleteModule('метод set_speciality_name не вызван')

            logging.info(f'Добавлено в базу данных: {self.adm_info["faculty_name"]}/{self.adm_info["speciality_name"]}')

        self.work_done()

    # override this method
    def process_source(self, source):
        df_database.close_database(self.connection)
        raise IncompleteModule('метод process_url не переопределён')

    # call this method after you fetch faculty name
    # IMPORTANT to do this BEFORE first write_admission call
    def set_faculty_name(self, faculty_name):
        faculty_id = df_database.write_faculty(self.connection, self.adm_info['university_id'], faculty_name)

        if faculty_id == -1:
            df_database.close_database(self.connection)
            raise WriteException('ошибка записи параметра faculty_id в базу данных')

        self.adm_info['faculty_name'] = faculty_name
        self.adm_info['faculty_id'] = faculty_id

    # call this method after you fetch faculty name
    # IMPORTANT to do this BEFORE first write_admission call
    # IMPORTANT to do this AFTER set_faculty_name call
    def set_speciality_name(self, speciality_name, source):

        if 'faculty_id' not in self.adm_info:
            df_database.close_database(self.connection)
            raise WrongUsage('set_speciality_name должен быть использован после вызова set_faculty_name')

        speciality_id = df_database.write_speciality(
            self.connection, self.adm_info['university_id'], self.adm_info['faculty_id'], speciality_name, source)

        if speciality_id == -1:
            df_database.close_database(self.connection)
            raise WriteException('ошибка записи параметра speciality_id в базу данных')

        self.adm_info['speciality_name'] = speciality_name
        self.adm_info['speciality_id'] = speciality_id

