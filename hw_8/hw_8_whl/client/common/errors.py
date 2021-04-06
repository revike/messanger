class ServerError(Exception):
    """
    Класс - исключение, для обработки ошибок сервера.
    При генерации требует строку с описанием ошибки,
    полученную с сервера.
    """
    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text


class NonDictInputError(Exception):
    """исключение - аргумент функции не словарь"""
    def __str__(self):
        return 'Аргумент функции должен быть словарём.'

