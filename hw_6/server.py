from PyQt5.QtCore import Qt
from logging import getLogger
from argparse import ArgumentParser
from configparser import ConfigParser
from sys import argv

from PyQt5.QtWidgets import QApplication

from common.decos import log
from common.variables import DEFAULT_PORT
from os.path import dirname, realpath, join

from server.core import MassageProcessor
from server.server_database import ServerDB
from server.main_window import MainWindow

logger = getLogger('server')


@log
def arg_parser(port, ip):
    logger.debug(f'Инициализация парсера {argv}')
    parser = ArgumentParser()
    parser.add_argument('-p', default=port, type=int, nargs='?')
    parser.add_argument('-a', default=ip, nargs='?')
    parser.add_argument('--no_gui', action='store_true')
    namespace = parser.parse_args(argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p
    gui_flag = namespace.no_gui
    logger.debug('Аргументы загружены')
    return listen_address, listen_port, gui_flag


@log
def config_load():
    config = ConfigParser()
    way = dirname(realpath(__file__))
    dir_path = join(way, 'databases/server')
    config.read(f'{dir_path}/server.ini')
    if 'SETTINGS' in config:
        return config
    config.add_section('SETTINGS')
    config.set('SETTINGS', 'Default_port', str(DEFAULT_PORT))
    config.set('SETTINGS', 'Listen_Address', '')
    config.set('SETTINGS', 'Database_path', '')
    config.set('SETTINGS', 'Database_file', 'server_database.db3')
    return config


@log
def main():
    global main_window
    config = config_load()
    ip, port, gui_flag = arg_parser(
        config['SETTINGS']['Default_port'],
        config['SETTINGS']['Listen_Address']
    )
    database = ServerDB(join(
        config['SETTINGS']['Database_path'],
        config['SETTINGS']['Database_file']
    ))

    server = MassageProcessor(ip, port, database)
    server.daemon = True
    server.start()

    if gui_flag:
        while True:
            command = input('Введите "q" для завершения работы сервера')
            if command == 'q':
                server.running = False
                server.join()
                break

    server_app = QApplication(argv)
    server_app.setAttribute(Qt.AA_DisableWindowContextHelpButton)
    main_window = MainWindow(database, server, config)

    server_app.exec_()
    server.running = False


if __name__ == '__main__':
    main()
