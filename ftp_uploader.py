import logging
import os
import time
from ftplib import FTP, error_perm

import tools

logging.basicConfig(format='[%(asctime)s] [%(levelname)s]: %(message)s', level=logging.INFO)


def try_place_file(ftp, name, localpath):
    successful = False
    repeats = 0

    while not successful:
        try:
            print("STOR", name, localpath)
            ftp.storbinary('STOR ' + name, open(localpath, 'rb'))
            successful = True

        except Exception as e:
            repeats += 1

            if repeats >= 5:
                raise e
            else:
                logging.warning(f'Не удалось загурзить файл ({repeats}/5). Причина: {e}. Повтор...')

            time.sleep(2)


def place_files(ftp, path):
    for name in os.listdir(path):
        localpath = os.path.join(path, name)

        if os.path.isfile(localpath):
            try_place_file(ftp, name, localpath)

        elif os.path.isdir(localpath):
            print("MKD", name)

            try:
                ftp.mkd(name)

            # ignore "directory already exists"
            except error_perm as e:
                if not e.args[0].startswith('550'):
                    raise

            print("CWD", name)
            ftp.cwd(name)

            place_files(ftp, localpath)

            print("CWD", "..")
            ftp.cwd("..")


def try_connect():
    successful = False
    repeats = 0

    host = 'host'
    port = 21
    login = 'username'
    password = 'pass'

    while not successful:
        try:
            logging.info('Подключение к FTP..')
            ftp = FTP()
            ftp.connect(host, port)
            ftp.login(login, password)
            successful = True

            return ftp

        except Exception as e:
            repeats += 1

            if repeats >= 5:
                raise e
            else:
                logging.warning(f'Не удалось подключиться к FTP ({repeats}/5). Причина: {e}. Повтор...')

            time.sleep(2)

def main():
    logging.info('*** Загрузка HTML страниц на FTP сервер ***')

    try:
        ftp = try_connect()

    except Exception as e:
        logging.error(f'Не удалось подключиться к FTP: {e}')
        tools.wait_for_exit()

    directory = os.path.abspath("result/AdmHelper")
    ftp_directory = "site/wwwroot/admhelper"

    ftp.cwd(ftp_directory)

    logging.info('Загрузка файлов:')
    place_files(ftp, directory)
    ftp.quit()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f'Не удалось загрузить HTML страницы на FTP сервер: {e}')
        
    tools.wait_for_exit()