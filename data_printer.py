import logging
import time

import sf_database
import df_database
import html_builder
import keywords as kw
import tools

from tools import hash_md5

save_path = 'result/AdmHelper'
source_path = 'patterns'

# admlist_task = []


def get_universities(df_conn):
    cursor = df_conn.cursor()

    universities_request = \
        'SELECT ' \
        'universities.id, ' \
        'cities.name, ' \
        'universities.name ' \
        'FROM ' \
        'universities ' \
        'INNER JOIN cities ON cities.id = universities.city_id ' \
        'ORDER BY cities.name ASC, ' \
        'universities.name ASC; '

    universities = cursor.execute(universities_request).fetchall()
    return universities


def make_universities_table(df_conn, universities):
    cursor = df_conn.cursor()
    table = {}

    for university in universities:
        id = university[0]
        city = university[1]
        name = university[2]

        info_request = \
            f'SELECT ' \
            f'COUNT(*), ' \
            f'COUNT(DISTINCT student_id), ' \
            f'SUM(consent), ' \
            f'SUM(CASE WHEN type IS 0 THEN 1 ELSE 0 END), ' \
            f'SUM(CASE WHEN type IS 1 THEN 1 ELSE 0 END), ' \
            f'SUM(CASE WHEN type IS 2 THEN 1 ELSE 0 END), ' \
            f'SUM(CASE WHEN type IS 3 THEN 1 ELSE 0 END) ' \
            f'FROM ' \
            f'admissions ' \
            f'WHERE ' \
            f'admissions.university_id={id};'
        info = cursor.execute(info_request).fetchone()

        if city not in table.keys():
            table[city] = {}

        table[city][name] = {
            'id': id,
            'info': info
        }

    return table


def get_specialities(df_conn, university_id):
    cursor = df_conn.cursor()

    specialities_request = \
        f'SELECT ' \
        f'specialities.id, ' \
        f'faculties.name, ' \
        f'specialities.name, ' \
        f'specialities.date_fetched, ' \
        f'specialities.source ' \
        f'FROM ' \
        f'specialities ' \
        f'INNER JOIN faculties ON faculties.id = specialities.faculty_id ' \
        f'WHERE ' \
        f'specialities.university_id={university_id}; '

    specialities = cursor.execute(specialities_request).fetchall()
    return specialities


def make_specialities_table(df_conn, university_id, specialities):
    cursor = df_conn.cursor()
    table = {}

    for speciality in specialities:
        id = speciality[0]
        faculty = speciality[1]
        name = speciality[2]

        info_request = \
            f'SELECT ' \
            f'COUNT(*), ' \
            f'COUNT(DISTINCT student_id), ' \
            f'SUM(consent), ' \
            f'SUM(CASE WHEN type IS 0 THEN 1 ELSE 0 END), ' \
            f'SUM(CASE WHEN type IS 1 THEN 1 ELSE 0 END), ' \
            f'SUM(CASE WHEN type IS 2 THEN 1 ELSE 0 END), ' \
            f'SUM(CASE WHEN type IS 3 THEN 1 ELSE 0 END) ' \
            f'FROM ' \
            f'admissions ' \
            f'WHERE ' \
            f'admissions.university_id={university_id} ' \
            f'AND admissions.speciality_id={id}; '
        info = cursor.execute(info_request).fetchone()

        if faculty not in table.keys():
            table[faculty] = {}

        table[faculty][name] = {
            'id': id,
            'info': info,
        }

    return table


def get_extra_overlaps(sf_conn, student_name):
    name_tag = hash_md5(student_name)
    cursor = sf_conn.cursor()

    result = []

    byte_map = int(name_tag[0:3] + name_tag[30:32], 16)

    cursor.execute("""SELECT hashes FROM map WHERE byte_map=? LIMIT 1""", (byte_map,))
    record = cursor.fetchone()

    if record is None:
        return []

    hashes_ids = record[0].split(':')

    found = False

    for hash_id in hashes_ids:
        cursor.execute("""SELECT admissions, hash FROM hashes WHERE id=? LIMIT 1""", (hash_id,))
        record = cursor.fetchone()

        if record[1] == name_tag:
            found = True
            break

    if not found:
        return []

    admissions = record[0]

    if len(admissions) == '':
        return []

    admissions_ids = admissions.split(':')

    for admission_id in admissions_ids:
        info_request = \
            f'SELECT ' \
            f'universities.name, ' \
            f'faculties.name, ' \
            f'specialities.name,' \
            f'specialities.link, ' \
            f'admissions.consent, ' \
            f'admissions.extra_data ' \
            f'FROM ' \
            f'admissions ' \
            f'INNER JOIN universities ON universities.id = admissions.university_id ' \
            f'INNER JOIN faculties ON faculties.id = admissions.faculty_id ' \
            f'INNER JOIN specialities ON specialities.id = admissions.speciality_id ' \
            f'WHERE ' \
            f'admissions.id=? ' \
            f'LIMIT 1'
        cursor.execute(info_request, (admission_id,))
        adm = cursor.fetchone()

        result.append(adm)

    return result


def make_students_table(df_conn, sf_conn, university_id, speciality_id):
    cursor = df_conn.cursor()
    table = {}

    # fetch_extra_overlaps = speciality_id in admlist_task

    students_request = \
        f'SELECT ' \
        f'students.name, ' \
        f'students.admissions, ' \
        f'admissions.student_id, ' \
        f'admissions.consent, ' \
        f'admissions.type, ' \
        f'admissions.subject1, ' \
        f'admissions.subject2, ' \
        f'admissions.subject3, ' \
        f'admissions.achievement, ' \
        f'admissions.extra_data ' \
        f'FROM ' \
        f'admissions ' \
        f'INNER JOIN students ON students.id = admissions.student_id ' \
        f'WHERE ' \
        f'admissions.university_id={university_id} ' \
        f'AND admissions.speciality_id={speciality_id}; '

    students = cursor.execute(students_request).fetchall()

    consents_position = 1

    for student in students:
        name = student[0]
        adms = student[1].split(':')
        id = student[2]
        consent = student[3]
        type = student[4]
        subject1 = student[5]
        subject2 = student[6]
        subject3 = student[7]
        achievement = student[8]
        extra_data = student[9]

        overlaps = []

        for adm in adms:
            info_request = \
                f'SELECT ' \
                f'universities.name, ' \
                f'faculties.name, ' \
                f'specialities.id, ' \
                f'specialities.name, ' \
                f'admissions.type, ' \
                f'admissions.consent ' \
                f'FROM ' \
                f'admissions ' \
                f'INNER JOIN universities ON universities.id = admissions.university_id ' \
                f'INNER JOIN faculties ON faculties.id = admissions.faculty_id ' \
                f'INNER JOIN specialities ON specialities.id = admissions.speciality_id ' \
                f'WHERE ' \
                f'admissions.id=? ' \
                f'AND admissions.speciality_id<>? ' \
                f'LIMIT 1'

            overlaps.extend(cursor.execute(info_request, (adm, speciality_id)).fetchall())

        extra_overlaps = get_extra_overlaps(sf_conn, name)

        if name in table:
            table[name]["counter"] += 1
            name += f' ({table[name]["counter"]})'

        table[name] = {
            'counter': 0,
            'info': [
                consents_position,
                consent,
                type_to_str(type),
                [subject1, subject2, subject3, achievement],
                extra_data
            ],
            'overlaps': overlaps,
            'extra_overlaps': extra_overlaps
        }

        if consent == 1:
            consents_position += 1

    return table


def type_to_str(type):
    type_str = '?'

    if type == kw.SPECIAL_RIGHT:
        type_str = 'ОП'
    elif type == kw.TARGET_RECRUITMENT:
        type_str = 'Ц'
    elif type == kw.NO_ENROLLMENT_TESTS:
        type_str = 'БВИ'
    elif type == kw.COMMON_CONTEST:
        type_str = 'ОК'

    return type_str


def main():

    # students_fetcher.main()

    logging.info('*** Создание HTML страниц ***')

    universities_config = tools.load_json_config(kw.UNIVERSITIES_FN)
    _un_config = {}

    for university_config in universities_config:
        _un_config[university_config['name']] = university_config

    df_conn = df_database.open_database()
    sf_conn = sf_database.open_database()

    universities = get_universities(df_conn)
    universities_table = make_universities_table(df_conn, universities)

    html_builder.try_prepare_conditions()
    html_builder.generate_universities_page(universities_table)

    for university in universities:
        university_id = university[0]
        city = university[1]
        university_name = university[2]

        specialities = get_specialities(df_conn, university_id)
        specialities_table = make_specialities_table(df_conn, university_id, specialities)

        table_info = {
            'university_id': university_id,
            'university_name': university_name,
            'statistics': universities_table[city][university_name]['info']
        }

        if university_name in _un_config:
            config = _un_config[university_name]

            if 'enroll_link' in config:
                table_info['enroll_link'] = config['enroll_link']


        html_builder.generate_specialities_page(table_info, specialities_table)

        for speciality in specialities:
            speciality_id = speciality[0]
            faculty_name = speciality[1]
            speciality_name = speciality[2]
            date_fetched = speciality[3]
            source = speciality[4]

            table_info = {
                'university_id': university_id,
                'university_name': university_name,
                'faculty_name': faculty_name,
                'speciality_id': speciality_id,
                'speciality_name': speciality_name,
                'statistics': specialities_table[faculty_name][speciality_name]['info'],
                'date_fetched': date_fetched,
                'source': source
            }

            students_table = make_students_table(df_conn, sf_conn, university_id, speciality_id)
            html_builder.generate_students_page(table_info, students_table)

    df_database.close_database(df_conn)
    sf_database.close_database(sf_conn)
    html_builder.clean_temp()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f'Не удалось создать HTML страницы: {e}')

    tools.wait_for_exit()

