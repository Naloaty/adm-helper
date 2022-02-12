import logging
import module_manager
from exceptions import WrongUsage, CriticalException
from module_manager import MissingModule
from modules.base_module import IncompleteModule
from modules.base_module import BaseModule
import df_database
import tools
import keywords as kw

logging.basicConfig(format='[%(asctime)s] [%(levelname)s]: %(message)s', level=logging.INFO)


class WrongConfiguration(BaseException):
    pass


example_university = {
    'name': 'ЮУрГУ',
    'city': 'Челябинск',
    'tag': 'urgu',
    'sources': [
        "source1",
        "source2"
    ]
}


def process_university(university):
    for key in example_university.keys():
        if not (key in university):
            raise WrongConfiguration(key)
        elif key == 'name':
            logging.info(f'*** Обработка {university[key]} ***')

    sources = university['sources']

    module = module_manager.get_appropriate_module(university)

    if not isinstance(module, BaseModule):
        raise IncompleteModule('модуль не наследован от класса BaseModule')

    module.pull_to_database(sources)


def main():
    module_manager.register_modules()

    df_database.check_database()
    df_database.create_database()

    universities = tools.load_json_config(kw.UNIVERSITIES_FN)

    for university in universities:
        try:
            process_university(university)

        except MissingModule as e:
            logging.warning(f'Отсутствует модуль для данного университета ({e}). Пропуск...')

        except IncompleteModule as e:
            logging.warning(f'Модуль для данного университета реализован некорректно ({e}) и не может быть '
                            f'использован для обработки. Пропуск...')

        except CriticalException:
            logging.error(f'Во время обработки университета произошла критическая ошибка. Текущий университет будет '
                          f'пропущен...')

        except WrongUsage as e:
            logging.warning(f'В модуле данного университета неверно использованы стандартные инструменты: {e}')

        except WrongConfiguration as e:
            logging.warning(f'Отствует необходимый параметр {e} в конфигурационном файле. Пропуск...')


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f'Не удалось загрузить ранжированные списки: {e}')

    tools.wait_for_exit()
