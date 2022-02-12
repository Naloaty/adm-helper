import re

import requests

from modules.base_module import BaseModule
from bs4 import BeautifulSoup
from df_database import AdmissionInfo
import keywords as kw
import tools
import logging


"""
functions:

1. getSTList - список абитуриентов
1.1 competition=
    <api response value>
1.2 sort=
    orig - по согласиям
    competition - конкурсный список
    rate - по рейтингу
    name - по имени 
1.3 plan=
    <api response value>
    
2. getCGList - список специальностей
2.1 type=
    bakalavr
    magistr
    aspirant
"""


nngasu_api = 'http://nngasu.ru/Abitur/information/data.php?func={0}'
source_link = 'http://www.nngasu.ru/Abitur/information/lists-of-submitted.php'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/77.0.3865.90 Safari/537.36 '
}


def request_api(function):
    url = nngasu_api.format(function)
    response = requests.get(url=url, headers=headers).json()

    return response


types_ids = {
    'Без вступительных испытаний': kw.NO_ENROLLMENT_TESTS,
    'В рамках квоты лиц, имеющих особые права': kw.SPECIAL_RIGHT,
    'Целевой прием': kw.TARGET_RECRUITMENT,
    'На общих основаниях': kw.COMMON_CONTEST
}


def request_specialities():
    json_response = request_api('getCGList&type=bakalavr')

    if 'Очная' not in json_response:
        return {}

    result = {}
    specialities = json_response['Очная']

    for speciality, edu_programs in specialities.items():
        for edu_program, types in edu_programs.items():
            result[edu_program] = {}

            for type, payment_form in types.items():
                if 'Бюджет' not in payment_form:
                    continue

                edu_level = payment_form['Бюджет']

                if 'Среднее общее или среднее профессиональное образование' not in edu_level:
                    continue

                info = edu_level['Среднее общее или среднее профессиональное образование']
                info['programs'] = info['programs'].replace('<br />', '; ')

                type_id = types_ids[type]
                result[edu_program][type_id] = info

    return result


def request_list(id, plan):
    json_response = request_api(f'getSTList&competition={id}&plan={plan}&sort=rate&listType=undefined')

    if 'abitur' not in json_response:
        return []

    result = []
    students = json_response['abitur']

    if len(students) == 0:
        return []

    for id, student_info in students.items():
        scores_raw = re.findall(r'\d{1,2}', student_info['ball'])

        scores = {
            'subj1': scores_raw[0],
            'subj2': scores_raw[1],
            'subj3': scores_raw[2],
            'achievement': student_info['individ']
        }

        general = {
            'name': student_info['fio'],
            'consent': 'Да' in student_info['accept']
        }

        info = {
            'scores': scores,
            'general': general,
            'extra_data':  '{0}; Приоритет: {1}'.format(student_info['state'], student_info['priority'])
        }

        result.append(info)

    return result


types_order = [
    kw.NO_ENROLLMENT_TESTS,
    kw.SPECIAL_RIGHT,
    kw.TARGET_RECRUITMENT,
    kw.COMMON_CONTEST
]


class NngasuModule(BaseModule):

    def __init__(self, university_name, city_name):
        super().__init__(university_name, city_name)

        logging.info('Получение списка специальностей..')
        self.specialities = request_specialities()

    def process_source(self, source):
        logging.info('Обработка ' + source)

        if source not in self.specialities:
            return

        speciality = self.specialities[source]

        for type_id in types_order:
            if type_id not in speciality:
                continue

            # id, plan, programs
            api_info = speciality[type_id]

            students_list = request_list(api_info['id'], api_info['plan'])

            if len(students_list) == 0:
                continue

            self.set_faculty_name('-')
            self.set_speciality_name('{0} ({1})'.format(source, api_info['programs']), source_link)

            self.process_list(type_id, students_list)

    def process_list(self, type, students_list):

        for student in students_list:
            general = student['general']
            scores = student['scores']
            extra_data = student['extra_data']

            general['type'] = type

            admission = AdmissionInfo(general=general, scores=scores, extra_data=extra_data)
            self.write_admission(admission)
