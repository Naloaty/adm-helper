import importlib


class MissingModule(BaseException):
    pass


registered_modules = {}


# register your module here
def register_modules():
    # use following method:
    # register_module(<tag>, modules.<module_name>, <class_name>)

    register_module('urgu', 'modules.urgu_module', 'UrguModule')
    register_module('urfu', 'modules.urfu_module', 'UrfuModule')
    register_module('chelgu', 'modules.chelgu_module', 'ChelguModule')
    register_module('admlist', 'modules.admlist_module', 'AdmlistModule')
    register_module('kgasu', 'modules.kgasu_module', 'KgasuModule')
    register_module('nngasu', 'modules.nngasu_module', 'NngasuModule')


def register_module(tag, module_name, class_name):
    registered_modules[tag] = {
        'module': module_name,
        'class': class_name
    }


def get_appropriate_module(university):
    tag = university['tag']
    name = university['name']
    city = university['city']

    if not (tag in registered_modules):
        raise MissingModule(f'университет с тегом {tag} не зарегистрирован в module_manager')

    module_info = registered_modules[tag]

    try:
        module = importlib.import_module(module_info['module'])
        class_ = getattr(module, module_info['class'])
        instance = class_(name, city)

    except ModuleNotFoundError:
        raise MissingModule(f"модуль с именем {module_info['module']} не найден")

    except AttributeError:
        raise MissingModule(f"модуль с именем {module_info['module']} не содержит указанный Вами класс {module_info['class']}")

    return instance


