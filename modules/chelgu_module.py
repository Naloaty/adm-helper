from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging
from bs4 import BeautifulSoup
import keywords as kw
from df_database import AdmissionInfo

from modules.base_module import BaseModule


class select_has_items(object):

    def __init__(self, locator):
        self.locator = locator

    def __call__(self, driver):
        element = driver.find_element(*self.locator)  # Finding the referenced element

        try:
            select = Select(element)
        except StaleElementReferenceException:
            return False

        if len(select.options) > 1:
            return True
        else:
            return False


source_link = 'https://www.csu.ru/roles/prospective-students/2019/list.aspx'


class ChelguModule(BaseModule):

    def __init__(self, university_name, city_name):
        super().__init__(university_name, city_name)

        CHROME_PATH = r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
        CHROMEDRIVER_PATH = r'D:\SeleniumDrivers\chromedriver.exe'
        WINDOW_SIZE = "256,144"

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=%s" % WINDOW_SIZE)
        chrome_options.binary_location = CHROME_PATH

        self.driver = webdriver.Chrome(executable_path=CHROMEDRIVER_PATH, chrome_options=chrome_options)
        # self.driver.set_window_size(1920, 1080)

    def process_source(self, source):
        level = 'Бакалавр/Специалист'
        faculty = source[0]
        study_form = 'Очная форма обучения'
        speciality = source[1]
        payment_form = 'Бюджет'
        report_type = 'Общий конкурс'

        logging.info(f'Эмуляция выбора пользователя для {speciality}...')

        self.driver.get(source_link)

        params = [
            {'name': 'ctl00$ctl54$g_1eed5c56_30f9_4ab9_8c8b_f9284ed99692$ddlLevels', 'text': level},
            {'name': 'ctl00$ctl54$g_1eed5c56_30f9_4ab9_8c8b_f9284ed99692$ddlFaculty', 'text': faculty},
            {'name': 'ctl00$ctl54$g_1eed5c56_30f9_4ab9_8c8b_f9284ed99692$ddlFormOfStuds', 'text': study_form},
            {'name': 'ctl00$ctl54$g_1eed5c56_30f9_4ab9_8c8b_f9284ed99692$ddlSpecialty', 'text': speciality},
            {'name': 'ctl00$ctl54$g_1eed5c56_30f9_4ab9_8c8b_f9284ed99692$ddlPaymentForm', 'text': payment_form},
            {'name': 'ctl00$ctl54$g_1eed5c56_30f9_4ab9_8c8b_f9284ed99692$ddlSubreports', 'text': report_type}
        ]

        for param in params:
            successful = False
            repeats = 0

            while not successful:
                try:
                    wait = WebDriverWait(self.driver, 15)
                    wait.until(select_has_items((By.NAME, param['name'])))
                    select = Select(self.driver.find_element_by_name(param['name']))
                    select.select_by_visible_text(param['text'])
                    successful = True

                except Exception:
                    repeats += 1

                    if repeats >= 5:
                        logging.error(f'Ошибка эмуляции пользователя для {speciality}. Пропуск...')
                        break
                    else:
                        logging.warning(
                            f'Не уадлось сэмулировать пользователя для {speciality} ({repeats}/5). Повтор...')

        wait = WebDriverWait(self.driver, 5)
        button = wait.until(
            EC.element_to_be_clickable((By.NAME, 'ctl00$ctl54$g_1eed5c56_30f9_4ab9_8c8b_f9284ed99692$btnshowReport')))
        button.click()

        wait = WebDriverWait(self.driver, 30)
        wait.until(EC.presence_of_element_located(
            (By.NAME, 'ctl00$ctl54$g_1eed5c56_30f9_4ab9_8c8b_f9284ed99692$ReportViewer$ctl10')))

        faculty = faculty[faculty.find('(') + 1:faculty.find(')')]

        html = self.driver.page_source
        self.parse_html(faculty, speciality, html)

    def parse_html(self, faculty, speciality, html):
        logging.info('Парсинг страницы...')

        general = {}
        scores = {}

        html_soup = BeautifulSoup(html, 'html.parser')

        self.set_faculty_name(faculty)
        self.set_speciality_name(speciality, source_link)

        attr = {
            'style': 'border-collapse:collapse;',
            'cellspacing': 0,
            'cellpadding': 0,
            'border': 0
        }

        params = [
            {'cols': 8, 'type': kw.SPECIAL_RIGHT, 'consent_index': 7},
            {'cols': 10, 'type': kw.TARGET_RECRUITMENT, 'consent_index': 7},
            {'cols': 9, 'type': kw.COMMON_CONTEST, 'consent_index': 7}
        ]

        for param in params:
            attr['cols'] = param['cols']

            table = html_soup.find('table', attr)

            if table is not None:
                general['type'] = param['type']
                self.parse_table(table, general, scores, param['consent_index'])

    def parse_table(self, table, general, scores, consent_index):
        attr = {
            'valign': 'top'
        }

        rows = table.find_all('tr', attr)

        iter_rows = iter(rows)
        next(iter_rows)
        next(iter_rows)

        for row in iter_rows:
            columns = row.find_all('div')

            if len(columns) == 0:
                continue

            general['name'] = columns[1].text
            general['consent'] = True if columns[consent_index].text == 'ДА' else False
            scores['subj1'] = columns[2].text
            scores['subj2'] = columns[3].text
            scores['subj3'] = columns[4].text
            scores['achievement'] = columns[5].text

            admission = AdmissionInfo(general=general, scores=scores, extra_data='')
            self.write_admission(admission)

    def work_done(self):
        super().work_done()

        self.driver.close()
