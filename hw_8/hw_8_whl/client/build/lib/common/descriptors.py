import logging
import sys
from ipaddress import ip_address

logger = logging.getLogger('server')


class Port:
    """
    Класс - дескриптор для номера порта.
    Позволяет использовать только порты с 1023 по 65536.
    При попытке установить неподходящий номер порта генерирует исключение.
    """
    def __set_name__(self, owner, name):
        self.name = name

    def __set__(self, instance, value):
        if not 1023 < value < 65536:
            logger.critical(
                f'Попытка запуска сервера с неподходящим портом {value}.'
            )
            sys.exit(1)
        instance.__dict__[self.name] = value


class Address:
    """
    Класс - дескриптор для ip адреса.
    При попытке установить неподходящий ip адрес генерирует исключение.
    """
    def __set_name__(self, owner, name):
        self.name = name

    def __set__(self, instance, value):
        if value:
            try:
                ip_address(value)
            except ValueError:
                logger.critical(f'Неверный ip адресс {value}')
                sys.exit(1)
        instance.__dict__[self.name] = value
