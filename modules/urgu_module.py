from modules.base_module import BaseModule
from bs4 import BeautifulSoup
from df_database import AdmissionInfo
import keywords as kw
import tools
import logging
from tools import create_acronym


urgu_api = 'https://abit.susu.ru/rating/2020/list.php?{0}/2/1'


class UrguModule(BaseModule):

    def process_source(self, source):
        url = urgu_api.format(source)
        html = tools.get_html(url)

        if html is None:
            return

        self.parse_html(html, url)

    def parse_html(self, html, source):
        logging.info('Парсинг страницы...')

        general = {}
        scores = {}

        html_soup = BeautifulSoup(html, 'html.parser')
        table = html_soup.find('tbody')
        rows = table.find_all('tr')

        info_block = html_soup.find('p')
        speciality_ = info_block.text.split('Направление/специальность ')

        self.set_faculty_name(info_block.find('b').text)
        self.set_speciality_name(speciality_[1], source)

        type_keys = {
            'Без экзаменов': kw.NO_ENROLLMENT_TESTS,
            'Квота': kw.SPECIAL_RIGHT,
            'Целевой прием': kw.TARGET_RECRUITMENT,
            'Общий конкурс': kw.COMMON_CONTEST
        }

        for row in rows:
            columns = row.find_all('td')

            if len(columns) == 0:
                continue

            category = columns[4].text

            for key in type_keys.keys():
                if key in category:
                    general['type'] = type_keys[key]
                    break

            general['name'] = columns[3].text
            general['consent'] = 'согласие' in category

            scores_block = columns[8].find_all('span')

            scores['subj1'] = scores_block[0].text if len(scores_block) > 0 else 0
            scores['subj2'] = scores_block[1].text if len(scores_block) > 1 else 0
            scores['subj3'] = scores_block[2].text if len(scores_block) > 2 else 0
            scores['achievement'] = scores_block[3].text if len(scores_block) > 3 else 0

            enrolled = 'зачислен' if 'зачислен' in category else ''
            extra_data = '({0},{1}); {2}'.format(columns[6].text, columns[7].text, enrolled)

            admission = AdmissionInfo(general=general, scores=scores, extra_data=extra_data)
            self.write_admission(admission)
