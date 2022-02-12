import hashlib
import sys
import msvcrt as m

import requests
import logging
import keywords as kw
import json


def hash_md5(string):
    utf8_str = string.encode('utf-8')
    hashed_str = hashlib.md5(utf8_str)

    return hashed_str.hexdigest()


def create_acronym(line):
    words = line.split()
    result = ''

    next_is_reference = False

    for word in words:
        if len(word) == 1:
            result += word[0]
        else:
            if (word == 'им.') or (word == 'г.'):
                result += f' {word} '
                next_is_reference = True
            elif next_is_reference:
                result += word
            else:
                result += word[0].upper()

    return result


def load_json_config(filename):
    try:
        logging.info(f'Загрузка конфигурационного файла {filename}...')
        file_content = open(filename, 'rb').read().decode('utf-8')
        file_content = remove_comments(file_content)
        json_obj = json.loads(file_content)
        logging.info('Файл загружен!')

        return json_obj

    except Exception as e:
        logging.error(f'Не удалось загрузить файл: {e}')
        sys.exit(kw.CRITICAL_EXCEPTION_MESSAGE)


# https://gist.github.com/WizKid/1170297
def remove_comments(s):
    inCommentSingle = False
    inCommentMulti = False
    inString = False

    t = []
    l = len(s)

    i = 0
    fromIndex = 0
    while i < l:
        c = s[i]

        if not inCommentMulti and not inCommentSingle:
            if c == '"':
                slashes = 0
                for j in range(i - 1, 0, -1):
                    if s[j] != '\\':
                        break

                    slashes += 1

                if slashes % 2 == 0:
                    inString = not inString

            elif not inString:
                if c == '#':
                    inCommentSingle = True
                    t.append(s[fromIndex:i])
                elif c == '/' and i + 1 < l:
                    cn = s[i + 1]
                    if cn == '/':
                        inCommentSingle = True
                        t.append(s[fromIndex:i])
                        i += 1
                    elif cn == '*':
                        inCommentMulti = True
                        t.append(s[fromIndex:i])
                        i += 1

        elif inCommentSingle and (c == '\n' or c == '\r'):
            inCommentSingle = False
            fromIndex = i

        elif inCommentMulti and c == '*' and i + 1 < l and s[i + 1] == '/':
            inCommentMulti = False
            i += 1
            fromIndex = i + 1

        i += 1

    if not inCommentSingle and not inCommentMulti:
        t.append(s[fromIndex:len(s)])

    return "".join(t)


def get_html(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/77.0.3865.90 Safari/537.36 '
    }

    try:
        logging.info(f'Получение страницы по адресу {url}...')
        html = requests.get(url, headers=headers).content
        logging.info('Страница получена!')
        return html

    except Exception as e:
        logging.warning(f'Не удалось получить страницу: {e}')
        return None


def wait_for_exit():
    print('-------------------------------')
    print("Нажмите любую клавишу для выхода...")
    m.getch()
    exit()
