import logging
from ipaddress import ip_address

logger = logging.getLogger('server')


class Port:
    def __set_name__(self, owner, name):
        self.name = name

    def __set__(self, instance, value):
        if not 1023 < value < 65536:
            logger.critical(
                f'Попытка запуска сервера с указанием неподходящего порта {value}.'
            )
            exit(1)
        instance.__dict__[self.name] = value


class Address:
    def __set_name__(self, owner, name):
        self.name = name

    def __set__(self, instance, value):
        if value:
            try:
                ip_address(value)
            except ValueError:
                logger.critical(f'Неверный ip адресс {value}')
                exit(1)
        instance.__dict__[self.name] = value
