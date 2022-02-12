import json
import re
import warnings

import requests

from modules.base_module import BaseModule
from bs4 import BeautifulSoup
from df_database import AdmissionInfo
import keywords as kw
import logging
import tabula
import slate3k


def parse_document(filename):
    with open(filename, 'rb') as f:
        doc = slate3k.PDF(f)

    keywords = {
        'keys': ['Списки поступающих', 'Уровень подготовки - Бакалавр'],
        'speciality': r'Направление подготовки\/специальность - [\w,\- ]+',
        'type': r'Категория приема - [\w()-, ]+',
        'extra_type': r'Основание поступления - [\w()-, ]+',
        'direction': r'Профиль -[\w()-, ]*'
    }

    types = {
        'Без вступительных испытаний': kw.NO_ENROLLMENT_TESTS,
        'На общих основаниях': kw.COMMON_CONTEST,
        'Имеющие особое право': kw.SPECIAL_RIGHT
    }

    # На общих основаниях - дополнительно
    extra_types = {
        'Целевой прием': kw.TARGET_RECRUITMENT,
        'Бюджетная основа': kw.COMMON_CONTEST,
        'Полное возмещение затрат': kw.PAID
    }

    result = {}

    prev_speciality = ''
    prev_type = -1

    for i in range(0, len(doc)):
        content = doc[i]

        is_pass = True

        for key in keywords['keys']:
            search = re.search(key, content)

            if search is None:
                is_pass = False
                break

        if not is_pass:
            continue

        speciality = re.search(keywords['speciality'], content)[0].split(' - ')[1].strip()
        en_type = re.search(keywords['type'], content)[0].split(' - ')[1].strip()
        extra_type = re.search(keywords['extra_type'], content)[0].split(' - ')[1].strip()

        r_type = types[en_type]

        if r_type == kw.COMMON_CONTEST:
            r_type = extra_types[extra_type]

        direction = re.search(keywords['direction'], content)[0].split(' - ')

        if len(direction) == 2:
            speciality += f' ({direction[1].strip()})'

        if speciality not in result:
            result[speciality] = {}

        if (r_type not in result[speciality]) and (i > 0) and (prev_type != kw.PAID):
            result[prev_speciality][prev_type]['page_end'] = i

        prev_speciality = speciality
        prev_type = r_type

        if r_type == kw.PAID:
            continue

        info = {
            'page_start': i + 1,
            'page_end': i + 1 if i + 1 == len(doc) else -1
        }

        result[speciality][r_type] = info

    _r = dict(result)
    for key, value in _r.items():
        if len(value) == 0:
            del result[key]

    return result


doc_filename = 'temp/kgasu-spisok-budj.pdf'
source = 'http://www.kgasu.ru/applicant/priem2020/files/stat/spisokbudj.pdf'


def download_document():
    logging.info(f'Скачивание документа по адресу {source}...')
    r = requests.get(source)

    with open(doc_filename, 'wb') as f:
        f.write(r.content)


class KgasuModule(BaseModule):

    def __init__(self, university_name, city_name):
        super().__init__(university_name, city_name)

        self.doc_structure = {}
        self.is_downloaded = False

    def process_source(self, source):
        if not self.is_downloaded:
            download_document()
            logging.info('Анализ документа...')

            logging.getLogger("pdfminer").setLevel(logging.ERROR)
            self.doc_structure = parse_document(doc_filename)
            logging.getLogger("pdfminer").setLevel(logging.WARNING)

            self.is_downloaded = True

        self.parse_pdf(source, self.doc_structure[source])

    def parse_pdf(self, name, info):
        logging.info('Парсинг направления...')

        general = {}
        scores = {}

        self.set_faculty_name('-')

        type_keys = [
            kw.NO_ENROLLMENT_TESTS,
            kw.SPECIAL_RIGHT,
            kw.TARGET_RECRUITMENT,
            kw.COMMON_CONTEST
        ]

        speciality_set = False

        for type_key in type_keys:
            if type_key not in info:
                continue

            page = info[type_key]
            start = page['page_start']
            end = page['page_end']

            if not speciality_set:
                self.set_speciality_name(name, source + '#page=' + str(start))
                speciality_set = True

            if start == end:
                pages = start
            else:
                pages = f'{start}-{end}'

            tables = tabula.read_pdf(doc_filename, pages=pages, multiple_tables=False, output_format="json",
                                     lattice=True)

            header_pass = False

            for table in tables:
                rows = table['data']

                for row in rows:
                    if not header_pass:
                        header_pass = True
                        continue

                    general['type'] = type_key

                    general['name'] = row[1]['text']
                    general['consent'] = '✓' in row[8]['text']

                    scores['subj1'] = row[4]['text'] if row[4]['text'] != '' else 0
                    scores['subj2'] = row[5]['text'] if row[5]['text'] != '' else 0
                    scores['subj3'] = row[6]['text'] if row[6]['text'] != '' else 0
                    scores['achievement'] = row[7]['text'] if row[7]['text'] != '' else 0

                    if_enrolled_group = type_key == kw.SPECIAL_RIGHT \
                                        or type_key == kw.NO_ENROLLMENT_TESTS \
                                        or type_key == kw.TARGET_RECRUITMENT

                    if if_enrolled_group and general['consent']:
                        extra_data = 'зачислен?'
                    else:
                        extra_data = ''

                    admission = AdmissionInfo(general=general, scores=scores, extra_data=extra_data)
                    self.write_admission(admission)
