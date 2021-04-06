import sys
from argparse import ArgumentParser
from os import urandom, getcwd
from os.path import dirname, realpath, join, exists
from sys import argv

from Cryptodome.PublicKey.RSA import generate, import_key
from PyQt5.QtWidgets import QApplication, QMessageBox

from client_database import ClientDatabase
from main_window import ClientMainWindow
from start_dialog import UserNameDialog
from transport import ClientTransport
from common.decos import log
from common.variables import *
from common.errors import ServerError

logger = logging.getLogger('client')


@log
def arg_parser():
    """Парсер аргументов командной строки"""
    parser = ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, nargs='?')
    parser.add_argument('-p', '--password', default='', nargs='?')
    namespace = parser.parse_args(argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_name = namespace.name
    client_password = namespace.password

    if not 1023 < server_port < 65536:
        logger.critical(
            f'Невозможен запуск клиента с неподходящим '
            f'номером порта: {server_port}.')
        sys.exit(1)

    return server_address, server_port, client_name, client_password


if __name__ == '__main__':
    logger.warning('start')
    server_address, server_port, client_name, client_password = arg_parser()
    client_app = QApplication(argv)

    start_dialog = UserNameDialog()
    if not client_name or not client_password:
        client_app.exec_()

        if start_dialog.ok_pressed:
            client_name = start_dialog.client_name.text()
            client_password = start_dialog.client_passwd.text()
        else:
            sys.exit(0)

    logger.info(
        f'Запущен клиент с парамертами: адрес сервера: {server_address} ,'
        f'порт: {server_port}, имя пользователя: {client_name}'
    )

    # dir_path = dirname(realpath(__file__))
    dir_path = getcwd()
    key_file = join(dir_path, f'{client_name}.key')
    if not exists(key_file):
        keys = generate(2048, urandom)
        with open(key_file, 'wb') as key:
            key.write(keys.export_key())
    else:
        with open(key_file, 'rb') as key:
            keys = import_key(key.read())

    database = ClientDatabase(client_name)

    try:
        transport = ClientTransport(
            server_port, server_address, database,
            client_name, client_password, keys)
    except ServerError as err:
        message = QMessageBox()
        message.critical(start_dialog, 'Ошибка сервера', err.text)
        sys.exit(1)

    transport.setDaemon(True)
    transport.start()

    del start_dialog

    main_window = ClientMainWindow(database, transport, keys)
    main_window.make_connection(transport)
    main_window.setWindowTitle(f'Чат - {client_name}')
    client_app.exec_()

    transport.transport_shutdown()
    transport.join()
