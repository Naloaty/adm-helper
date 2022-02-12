import logging

import data_fetcher
import students_fetcher
import data_printer
import ftp_uploader
import tools


def main():
    try:
        data_fetcher.main()

    except Exception as e:
        logging.error(f'Не удалось загрузить ранжированные списки: {e}')
        tools.wait_for_exit()
        
    try:
        students_fetcher.main()

    except Exception as e:
        logging.error(f'Не удалось загрузить базу admlist.ru: {e}')
        tools.wait_for_exit()

    try:
        data_printer.main()

    except Exception as e:
        logging.error(f'Не удалось создать HTML страницы: {e}')
        tools.wait_for_exit()

    try:
        ftp_uploader.main()

    except Exception as e:
        logging.error(f'Не удалось загрузить файлы на FTP сервер: {e}')
        tools.wait_for_exit()

    logging.info('Ранжированные списки загружены, HTML страницы сгенерированы и загружены на FTP сервер!')
    tools.wait_for_exit()


if __name__ == "__main__":
    main()
