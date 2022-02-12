from modules.base_module import BaseModule
from bs4 import BeautifulSoup
from df_database import AdmissionInfo
import keywords as kw
import tools
import logging
import json

urfu_api = 'https://urfu.ru/api/ratings/departmental/18/{0}/1/'
urfu_main = 'https://urfu.ru'
source = 'https://urfu.ru/ru/ratings/'

class UrfuModule(BaseModule):

    # cache heavy pages to speed up program
    def __init__(self, university_name, city_name):
        super().__init__(university_name, city_name)

        self.cached_html_soup = {}

    def process_source(self, source):
        identifiers = source.split(':')

        types = [
            kw.SPECIAL_RIGHT,
            kw.TARGET_RECRUITMENT,
            kw.COMMON_CONTEST
        ]

        html_soup = None

        if identifiers[0] in self.cached_html_soup:
            html_soup = self.cached_html_soup[identifiers[0]]

        else:

            api_response = tools.get_html(urfu_api.format(identifiers[0]))
            url = urfu_main + json.loads(api_response)['url']

            html = tools.get_html(url)

            if html is None:
                return

            logging.info('Кэширование страницы...')

            # cache heavy pages to speed up program
            self.cached_html_soup[identifiers[0]] = BeautifulSoup(html, 'html.parser')

            html_soup = self.cached_html_soup[identifiers[0]]

        logging.info('Парсинг направления...')
        for i in range(1, 4):
            if identifiers[i] == '-':
                continue

            self.parse_html(html_soup=html_soup, table_id=identifiers[i], enroll_type=types[i - 1])

    def parse_html(self, html_soup, table_id, enroll_type):

        general = {}
        scores = {}

        table_header = html_soup.find('table', id=table_id)

        if table_header is None:
            logging.warning(f'Таблица для типа {enroll_type} не найдена')

        info_block = table_header.find('b').text.split(', ')

        self.set_faculty_name(info_block[0])
        self.set_speciality_name(info_block[1], source)

        contest_table = table_header.find_next_sibling("table").find_next_sibling("table")

        rows = contest_table.find_all('tr')

        for row in rows:
            columns = row.find_all('td')

            if len(columns) == 0:
                continue

            general['name'] = columns[0].text.split(' (')[0]
            general['type'] = enroll_type
            general['consent'] = True if columns[2].text == 'Да' else False

            sr_test = row.find(colspan=3)

            if (sr_test is not None) and (enroll_type == kw.COMMON_CONTEST):
                if sr_test.text == 'Без вступительных испытаний':
                    general['type'] = kw.NO_ENROLLMENT_TESTS

            if general['type'] == kw.NO_ENROLLMENT_TESTS:
                scores['subj1'] = -1
                scores['subj2'] = -1
                scores['subj3'] = -1
                scores['achievement'] = -1
            else:
                scores['subj1'] = 0 if columns[3].text == '' else columns[3].text.split(' (')[0]
                scores['subj2'] = 0 if columns[4].text == '' else columns[4].text.split(' (')[0]
                scores['subj3'] = 0 if columns[5].text == '' else columns[5].text.split(' (')[0]
                scores['achievement'] = 0 if columns[6].text == '\xa0' else columns[6].text

            if_enrolled_group = enroll_type == kw.SPECIAL_RIGHT \
                          or enroll_type == kw.NO_ENROLLMENT_TESTS \
                          or enroll_type == kw.TARGET_RECRUITMENT

            if if_enrolled_group and general['consent']:
                extra_data = 'зачислен?'
            else:
                extra_data = ''

            admission = AdmissionInfo(general=general, scores=scores, extra_data=extra_data)
            self.write_admission(admission)

            #if general['name'] == self.student_name:
                #break

    def work_done(self):
        super().work_done()

        self.cached_html_soup = None
