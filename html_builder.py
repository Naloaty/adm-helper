import os
import logging
import shutil
import time
from distutils.dir_util import copy_tree
import tools
from exceptions import WrongUsage
import data_printer
import students_fetcher

TEMP_PATH = 'result/AdmHelper/temp'
SAVE_PATH = 'result/AdmHelper'
SOURCE_PATH = 'patterns'

logging.basicConfig(format='[%(asctime)s] [%(levelname)s]: %(message)s', level=logging.INFO)


def check_conditions():
    try:
        logging.info('Подготовка рабочей области html_builder...')

        if os.path.exists(SAVE_PATH):
            shutil.rmtree(SAVE_PATH)

        time.sleep(0.2)
        os.mkdir(SAVE_PATH)
        os.mkdir(TEMP_PATH)
        os.mkdir(SAVE_PATH + '/universities')
        os.mkdir(SAVE_PATH + '/universities/specialities')

        styles = [
            {'source': f'{SOURCE_PATH}/universities/styles', 'destination': f'{SAVE_PATH}/styles'},
            {'source': f'{SOURCE_PATH}/specialities/styles', 'destination': f'{SAVE_PATH}/universities/styles'},
            {'source': f'{SOURCE_PATH}/students/styles', 'destination': f'{SAVE_PATH}/universities/specialities/styles'}
        ]

        for style in styles:
            os.mkdir(style['destination'])
            copy_tree(style['source'], style['destination'])

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
        logging.info('*** Очистка временных файлов data_printer ***')

        if os.path.exists(TEMP_PATH):
            shutil.rmtree(TEMP_PATH)

        logging.info('Готово!')
    except Exception as e:
        logging.error(f'Не удалось очистить временные файлы: {e}')
        raise e


def generate_universities_page(universities_table):
    logging.info('*** Создание html страницы с университетами ***')

    output_name = f'{SAVE_PATH}/index.html'
    temp_name = f'{TEMP_PATH}/univ_tmp_pg.html'

    try:
        logging.info('Загрузка шаблнов...')
        shell = open(f'{SOURCE_PATH}/universities/shell.html', 'rb').read().decode('utf-8')
        row_caption = open(f'{SOURCE_PATH}/universities/row_city.html', 'rb').read().decode('utf-8')
        row_data = open(f'{SOURCE_PATH}/universities/row_univ.html', 'rb').read().decode('utf-8')

    except Exception as e:
        logging.error(f'Не удалось загрузить шаблоны: {e} ')
        raise e

    try:
        logging.info('Создание временных файлов...')
        open(temp_name, 'w')

    except Exception as e:
        logging.error(f'Не удалось создать временные файлы: {e} ')
        raise e

    logging.info('Обработка таблицы...')
    with open(temp_name, 'ab') as temp_file:
        for city, universities in universities_table.items():

            args = {
                'city_name': city
            }

            rc_ = row_caption.format(**args)
            temp_file.write(rc_.encode('utf-8'))

            for university, info in universities.items():
                args = {
                    'click_link': 'universities/' + str(info['id']) + '.html',
                    'university_name': university,
                    'admissions': info['info'][0],
                    'students': info['info'][1],
                    'consents': info['info'][2],
                    'special_right': info['info'][3],
                    'target_recruitment': info['info'][4],
                    'no_enrollment_tests': info['info'][5],
                    'common_contest': info['info'][6]
                }

                rd_ = row_data.format(**args)
                temp_file.write(rd_.encode('utf-8'))

    try:
        logging.info('Обработка временных файлов...')
        body = open(temp_name, 'rb').read().decode('utf-8')

        args = {
            'table_body': body
        }
        page = shell.format(**args)

    except Exception as e:
        logging.error(f'Не удалось обработать временные файлы: {e} ')
        raise e

    try:
        logging.info('Сохранение результата...')
        with open(output_name, 'wb') as output_file:
            output_file.write(page.encode('utf-8'))

        logging.info('Готово!')

    except Exception as e:
        logging.error(f'Не удалось сохранить результат: {e} ')
        raise e


example_specialities_table_info = {
    'university_id': 1,
    'university_name': 'ЮУрГУ',
    'statistics': (1, 1, 1, 1, 1, 1, 1)
}


def generate_specialities_page(table_info, specialities_table):
    if not isinstance(table_info, dict):
        raise WrongUsage('в generate_specialities_page передан параметр table_info, не являющийся словарём')

    for key in example_specialities_table_info.keys():
        if not (key in table_info):
            raise WrongUsage(f'в generate_specialities_page передан словарь table_info, не содержащий ключ {key}')

    logging.info(f'*** Создание html страницы со специальностями для {table_info["university_name"]} ***')

    back_name = '../index.html'

    output_name = f'{SAVE_PATH}/universities/{table_info["university_id"]}.html'
    temp_name = f'{TEMP_PATH}/spec_tmp_pg - {table_info["university_id"]}.html'

    try:
        logging.info('Загрузка шаблнов...')
        shell = open(f'{SOURCE_PATH}/specialities/shell.html', 'rb').read().decode('utf-8')
        row_caption = open(f'{SOURCE_PATH}/specialities/row_faculty.html', 'rb').read().decode('utf-8')
        row_data = open(f'{SOURCE_PATH}/specialities/row_spec.html', 'rb').read().decode('utf-8')

    except Exception as e:
        logging.error(f'Не удалось загрузить шаблоны: {e} ')
        raise e

    try:
        logging.info('Создание временных файлов...')
        open(temp_name, 'w')

    except Exception as e:
        logging.error(f'Не удалось создать временные файлы: {e} ')
        raise e

    logging.info('Обработка таблицы...')
    with open(temp_name, 'ab') as temp_file:
        for faculty, specialities in specialities_table.items():

            if faculty != '-':
                args = {'faculty_name': faculty}
                rc_ = row_caption.format(**args)
                temp_file.write(rc_.encode('utf-8'))

            for speciality, info in specialities.items():
                args = {
                    'click_link': 'specialities/' + str(info['id']) + '.html',
                    'speciality_name': speciality,
                    'admissions': info['info'][0],
                    'students': info['info'][1],
                    'consents': info['info'][2],
                    'special_right': info['info'][3],
                    'target_recruitment': info['info'][4],
                    'no_enrollment_tests': info['info'][5],
                    'common_contest': info['info'][6]
                }

                rd_ = row_data.format(**args)
                temp_file.write(rd_.encode('utf-8'))

    try:
        logging.info('Обработка временных файлов...')
        body = open(temp_name, 'rb').read().decode('utf-8')

        if 'enroll_link' in table_info:
            enroll_block = '<center><h2><a href="{0}">{1}</a><h2></center>'
            enroll_block = enroll_block.format(table_info['enroll_link'], 'Приказы о зачислении')

        else:
            enroll_block = ''

        args = {
            'enroll_block': enroll_block,
            'admissions': table_info['statistics'][0],
            'students': table_info['statistics'][1],
            'consents': table_info['statistics'][2],
            'special_right': table_info['statistics'][3],
            'target_recruitment': table_info['statistics'][4],
            'no_enrollment_tests': table_info['statistics'][5],
            'common_contest': table_info['statistics'][6],
            'back_link': back_name,
            'university_name': table_info['university_name'],
            'table_body': body
        }
        page = shell.format(**args)

    except Exception as e:
        logging.error(f'Не удалось обработать временные файлы: {e} ')
        raise e

    try:
        logging.info('Сохранение результата...')
        with open(output_name, 'wb') as output_file:
            output_file.write(page.encode('utf-8'))

        logging.info('Готово!')

    except Exception as e:
        logging.error(f'Не удалось сохранить результат: {e} ')
        raise e


example_students_table_info = {
    'university_id': 1,
    'university_name': 'ЮУрГУ',
    'faculty_name': 'Высшая школа электроники и компьютерных наук',
    'speciality_id': 1,
    'speciality_name': '09.03.04 Программная инженерия',
    'statistics': (1, 1, 1, 1, 1, 1, 1),
    'date_fetched': '1970-01-01 12:00:00',
    'source': 'http://example.com/'
}

admlist_url = 'http://admlist.ru/{0}.html'


def generate_students_page(table_info, students_table):
    if not isinstance(table_info, dict):
        raise WrongUsage('в generate_students_page передан параметр table_info, не являющийся словарём')

    for key in example_students_table_info.keys():
        if not (key in table_info):
            raise WrongUsage(f'в generate_students_page передан словарь table_info, не содержащий ключ {key}')

    logging.info(
        f'*** Создание html страницы с ранжированным списоком для {table_info["university_name"]}, {table_info["speciality_name"]} ***')

    back_name = f'../{table_info["university_id"]}.html'

    output_name = f'{SAVE_PATH}/universities/specialities/{table_info["speciality_id"]}.html'
    temp_name = f'{TEMP_PATH}/stud_tmp_pg - {table_info["speciality_id"]}.html'

    try:
        logging.info('Загрузка шаблнов...')
        shell = open(f'{SOURCE_PATH}/students/shell.html', 'rb').read().decode('utf-8')
        row_data_normal = open(f'{SOURCE_PATH}/students/row_stud_norm.html', 'rb').read().decode('utf-8')
        row_data_consent = open(f'{SOURCE_PATH}/students/row_stud_cons.html', 'rb').read().decode('utf-8')
        overlap_normal = open(f'{SOURCE_PATH}/students/overlap_norm.html', 'rb').read().decode('utf-8')
        overlap_consent = open(f'{SOURCE_PATH}/students/overlap_cons.html', 'rb').read().decode('utf-8')

    except Exception as e:
        logging.error(f'Не удалось загрузить шаблоны: {e} ')
        raise e

    try:
        logging.info('Создание временных файлов...')
        open(temp_name, 'w')

    except Exception as e:
        logging.error(f'Не удалось создать временные файлы: {e} ')
        raise e

    logging.info('Обработка таблицы...')
    with open(temp_name, 'ab') as temp_file:
        i = 1
        for student_name, payload in students_table.items():

            info = payload['info']
            overlaps = payload['overlaps']
            extra_overlaps = payload['extra_overlaps']

            overlaps_html = ''

            first = True

            # 0 - university_name
            # 1 - faculty_name
            # 2 - speciality_id
            # 3 - speciality_name
            # 4 - admission type (int)
            # 5 - consent (0 or 1)
            for overlap in overlaps:
                university_name = overlap[0]
                faculty_name = overlap[1]
                speciality_id = overlap[2]
                speciality_name = overlap[3]
                adm_type = overlap[4]
                consent = overlap[5]

                if overlap[1] != '-':
                    faculty_name = faculty_name if len(faculty_name) < 10 else tools.create_acronym(faculty_name)
                    link_caption = f'{university_name}, {faculty_name}, {speciality_name}, {data_printer.type_to_str(adm_type)}'
                else:
                    link_caption = f'{university_name}, {speciality_name}, {data_printer.type_to_str(adm_type)}'

                args = {
                    'link_caption': link_caption,
                    'click_link': f'{speciality_id}.html'
                }

                # consent
                if consent == 1:
                    overlap_ = overlap_consent.format(**args)
                else:
                    overlap_ = overlap_normal.format(**args)

                if not first:
                    overlaps_html += '<br><br>'
                else:
                    first = False

                overlaps_html += overlap_ + '\n'

            # received from Admlist
            # 0 - university_name
            # 1 - faculty_name
            # 2 - speciality_name
            # 3 - speciality_link
            # 4 - consent (0 or 1)
            # 5 - extra_data
            for overlap in extra_overlaps:
                url = admlist_url.format(overlap[3])
                university_name = overlap[0]
                faculty_name = overlap[1]
                speciality_name = overlap[2]
                extra_data = overlap[5]
                consent = overlap[4]

                if faculty_name != '-':
                    faculty_name = faculty_name if len(faculty_name) < 10 else tools.create_acronym(faculty_name)
                    link_caption = f'{university_name}, {faculty_name}, {speciality_name}, {extra_data}'
                else:
                    link_caption = f'{university_name}, {speciality_name}, {extra_data}'

                args = {
                    'link_caption': link_caption,
                    'click_link': url
                }

                if consent == 1:
                    overlap_ = overlap_consent.format(**args)
                else:
                    overlap_ = overlap_normal.format(**args)

                overlaps_html += '<br><br>'
                overlaps_html += overlap_ + '\n'

            subject1 = int(info[3][0])
            subject2 = int(info[3][1])
            subject3 = int(info[3][2])
            achievement = int(info[3][3])

            score_sum = 0

            if subject1 != -1:
                score_sum += subject1

            if subject2 != -1:
                score_sum += subject2

            if subject3 != -1:
                score_sum += subject3

            if achievement != -1:
                score_sum += achievement

            args = {
                'position_table': i,
                'position_consent': info[0],
                'name': student_name,
                'consent': 'Да' if info[1] == 1 else 'Нет',
                'type': info[2],
                'subject1': subject1,
                'subject2': subject2,
                'subject3': subject3,
                'achievement': achievement,
                'score_summ': score_sum,
                'extra_data': info[4],
                'overlaps': overlaps_html
            }

            i += 1

            if info[1] == 1:
                rd_ = row_data_consent.format(**args)
            else:
                rd_ = row_data_normal.format(**args)

            temp_file.write(rd_.encode('utf-8'))

    try:
        logging.info('Обработка временных файлов...')
        body = open(temp_name, 'rb').read().decode('utf-8')

        _fn = table_info['faculty_name']
        faculty_name = _fn if len(table_info['faculty_name']) < 10 else tools.create_acronym(table_info['faculty_name'])

        if faculty_name == '-':
            title = f'{table_info["university_name"]}, {table_info["speciality_name"]}'
        else:
            title = f'{table_info["university_name"]}, {table_info["faculty_name"]}, {table_info["speciality_name"]}'

        source_block = '<center><h2><a href="{0}">{1}</a><h2></center>'
        source_block = source_block.format(table_info['source'], 'Источник')

        args = {
            'source_block': source_block,
            'title': title,
            'admissions': table_info['statistics'][0],
            'students': table_info['statistics'][1],
            'consents': table_info['statistics'][2],
            'special_right': table_info['statistics'][3],
            'target_recruitment': table_info['statistics'][4],
            'no_enrollment_tests': table_info['statistics'][5],
            'common_contest': table_info['statistics'][6],
            'date_fetched': table_info['date_fetched'],
            'back_link': back_name,
            'table_body': body
        }
        page = shell.format(**args)

    except Exception as e:
        logging.error(f'Не удалось обработать временные файлы: {e} ')
        raise e

    try:
        logging.info('Сохранение результата...')
        with open(output_name, 'wb') as output_file:
            output_file.write(page.encode('utf-8'))

        logging.info('Готово!')

    except Exception as e:
        logging.error(f'Не удалось сохранить результат: {e} ')
        raise e
