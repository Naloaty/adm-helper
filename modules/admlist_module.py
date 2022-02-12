from exceptions import Unsupported
from modules.base_module import BaseModule
from bs4 import BeautifulSoup
from df_database import AdmissionInfo
import keywords as kw
import tools
import logging
import re

admlist_api = 'http://admlist.ru/{0}.html'


def format_speciality(speciality):
    border_left = speciality.find('(')
    border_right = speciality.find(')')
    name = speciality[0:border_left - 1]
    number = speciality[border_left + 1:border_right]

    return f'{number} {name}'


def extract_three_parts(delimiter, string):
    split = string.split(delimiter)

    result = {
        'start': '-',
        'middle': '-',
        'end': '-'
    }

    if len(split) == 1:
        return result

    result['start'] = split[0]

    if len(split) > 2:
        middle_part = ''

        # reassembly middle part
        for i in range(1, len(split) - 1):
            if i == 1:
                middle_part += split[i]
            else:
                middle_part += '{0}{1}'.format(delimiter, split[i])

        result['middle'] = middle_part

    result['end'] = split[len(split) - 1]

    return result


def parse_title(title):
    # example:
    # "ВАВТ, ФЭМ, Экономика (38.03.01) / Реклама и связи с общественностью (42.03.01), Экономика и управление,
    # ОК [БК], №: 1, №*: 1, №**: 1"

    result = {
        'university_name': '-',
        'faculty_name': '-',
        'speciality_code': [],
        'speciality_name': [],
        'edu_program': '-',
        'other_stuff': '-'
    }

    # find all specialities codes
    codes = re.findall(r'\d{2}\.\d{2}\.\d{2}', title)
    result['speciality_code'] = codes

    first_code_index_l = title.find(' ({0})'.format(codes[0]))

    # ============= analyze part1 =============

    # part1 includes university name, faculty name (if presented) and first speciality name
    # example: "ВАВТ, ФЭМ, Экономика"
    part1 = title[0:first_code_index_l]
    extracted = extract_three_parts(', ', part1)

    result['university_name'] = extracted['start']
    result['faculty_name'] = extracted['middle']
    result['speciality_name'].append(extracted['end'])

    # ============= analyze part2 =============

    first_code_index_r = first_code_index_l + 10

    # part2 includes other specialities names and codes, educational program and other stuff
    # example: " / Реклама и связи с общественностью (42.03.01), Экономика и управление, ОК [БК], №: 1, №*: 1, №**: 1"
    part2 = title[first_code_index_r + 1:len(title)]

    # iterate over other specialities codes
    for i in range(1, len(codes)):
        right_border = part2.find(' ({0})'.format(codes[i]))
        speciality_block = part2[0: right_border]

        words = re.findall(r'[\w()-,]+', speciality_block)

        speciality_name = ''

        # reassembly speciality name
        for j in range(0, len(words)):
            speciality_name += words[j]

            if j != len(words) - 1:
                speciality_name += ' '

        result['speciality_name'].append(speciality_name)
        part2 = part2.replace('{0} ({1})'.format(speciality_name, codes[i]), '')

    # ============= analyze end =============

    # part2 now includes study program and other stuff
    # example: "/ , Экономика и управление, ОК [БК], №: 1, №*: 1, №**: 1"

    part_end = part2.split(', №:')

    if len(part_end) > 1:
        extracted = extract_three_parts(', ', part_end[0])
    else:
        extracted = extract_three_parts(', ', part2)

    # contain educational program or other stuff
    if extracted['start'] != '-':
        result['edu_program'] = extracted['middle'] if len(part_end) > 1 else extracted['end']

        if len(part_end) > 1:
            result['edu_program'] = extracted['middle']
            result['other_stuff'] = '{0}, №:{1}'.format(extracted['end'], part_end[1])
        else:
            result['edu_program'] = extracted['end']

    return result


# print(parse_title('РАНХиГС - Сибирский институт управления, Государственное и муниципальное управление (38.03.04),
# ОК [Б], №: 55, №*: 3, №**: 41'))


class AdmlistModule(BaseModule):

    def process_source(self, source):
        url = admlist_api.format(source)
        html = tools.get_html(url)

        if html is None:
            return

        self.parse_html(html)

    def parse_html(self, html):
        logging.info('Парсинг страницы...')

        general = {}
        scores = {}

        html_soup = BeautifulSoup(html, 'html.parser')

        attr = {'class': 'tableFixHead'}
        table = html_soup.find('table', attr).find('tbody')
        rows = table.find_all('tr')

        attr = {'href': 'index.html'}
        info_block = html_soup.find('a', attr).parent

        parsed_block = parse_title(info_block.text)

        speciality_name = ''
        codes = parsed_block['speciality_code']
        names = parsed_block['speciality_name']
        edu_program = parsed_block['edu_program']

        for i in range(0, len(codes)):
            speciality_name += codes[i] + ' ' + names[i];

            if i != len(codes) - 1:
                speciality_name += ' / '

        if edu_program != '-':
            speciality_name += ' (' + edu_program + ')'

        self.set_faculty_name(parsed_block['faculty_name'])
        self.set_speciality_name(speciality_name)

        type_keys = {
            'БВИ': kw.NO_ENROLLMENT_TESTS,
            'ОП': kw.SPECIAL_RIGHT,
            'Ц': kw.TARGET_RECRUITMENT,
            'ОК': kw.COMMON_CONTEST
        }

        for row in rows:
            columns = row.find_all('td')

            category = columns[5].text

            for key in type_keys.keys():
                if key in category:
                    general['type'] = type_keys[key]
                    break

            general['name'] = columns[3].text
            general['consent'] = 'Да' in columns[4].text

            scores['subj1'] = columns[6].text
            scores['subj2'] = columns[7].text
            scores['subj3'] = columns[8].text
            scores['achievement'] = columns[10].text

            extra_data = ''

            admission = AdmissionInfo(general=general, scores=scores, extra_data=extra_data)
            self.write_admission(admission)
