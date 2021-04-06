from dis import get_instructions


class ServerVerifier(type):
    """
    Метакласс, проверяющий что в результирующем классе нет клиентских
    вызовов таких как: connect. Также проверяется, что серверный
    сокет является TCP и работает по IPv4 протоколу.
    """
    def __init__(cls, class_name, bases, class_dict):
        methods = []
        attrs = []

        for func in class_dict:
            try:
                ret = get_instructions(class_dict[func])
            except TypeError:
                pass
            else:
                for i in ret:
                    if i.opname == 'LOAD_GLOBAL':
                        if i.argval not in methods:
                            methods.append(i.argval)
                    elif i.opname == 'LOAD_ATTR':
                        if i.argval not in attrs:
                            attrs.append(i.argval)
        if 'connect' in methods:
            raise TypeError('Error! -> Использование метода connect')
        if not ('SOCK_STREAM' in methods and 'AF_INET' in methods):
            raise TypeError('Отсутствуют методы SOCK_STREAM и AF_INET')
        super().__init__(class_name, bases, class_dict)


class ClientVerifier(type):
    """
    Метакласс, проверяющий что в результирующем классе нет серверных
    вызовов таких как: accept, listen. Также проверяется, что сокет не
    создаётся внутри конструктора класса.
    """
    def __init__(cls, class_name, bases, class_dict):
        methods = []

        for func in class_dict:
            try:
                ret = get_instructions(class_dict[func])
            except TypeError:
                pass
            else:
                for i in ret:
                    if i.opname == 'LOAD_GLOBAL':
                        if i.argval not in methods:
                            methods.append(i.argval)

                for command in ('accept', 'listen', 'socket'):
                    if command in methods:
                        raise TypeError(
                            'В классе обнаружено использование метода'
                        )
                if 'get_message' in methods or 'send_message' in methods:
                    pass
                super().__init__(class_name, bases, class_dict)
