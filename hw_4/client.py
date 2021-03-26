import json
import sys

from argparse import ArgumentParser
from socket import socket, AF_INET, SOCK_STREAM
from threading import Thread, Lock
from time import time, sleep

from client_database import ClientDatabase
from common.utils import send_message, get_message
from common.variables import *
from errors import IncorrectDataReceivedError, ServerError, ReqFieldMissingError, NonDictInputError
from metaclasses import ClientVerifier

logger = logging.getLogger('client')
sock_lock = Lock()
database_lock = Lock()


def print_help():
    print('Поддерживаемые команды:')
    print('m - отправить сообщение. Кому и текст будет запрошены отдельно.')
    print('h - история сообщений')
    print('c - список контактов')
    print('edit - редактирование списка контактов')
    print('help - вывести подсказки по командам')
    print('q - выход из программы')


class Client(Thread, metaclass=ClientVerifier):

    def __init__(self, account_name, sock, database):
        self.account_name = account_name
        self.sock = sock
        self.database = database
        super().__init__()

    def create_message_exit(self):
        message_exit = {
            ACTION: EXIT,
            TIME: time(),
            ACCOUNT_NAME: self.account_name
        }
        return message_exit

    def create_message(self):
        to = input('Введите получателя сообщения: ')
        message = input('Сообщение: ')

        messages = {
            ACTION: MESSAGE,
            SENDER: self.account_name,
            DESTINATION: to,
            TIME: time(),
            MESSAGE_TEXT: message
        }

        with database_lock:
            if not self.database.check_user(to):
                logger.error(f'Попытка отправить сообщение незарегистрированому получателю: {to}')
                return

        with database_lock:
            self.database.save_message(self.account_name, to, message)

        with sock_lock:
            try:
                send_message(self.sock, messages)
                logger.info(f'Отправлено сообщение для пользователя {to}')
            except OSError as err:
                if err.errno:
                    logger.critical('Потеряно соединение с сервером.')
                    exit(1)
                else:
                    logger.error('Не удалось передать сообщение. Таймаут соединения')

    def run(self):
        print_help()
        while True:
            command = input('Введите команду: ')
            if command == 'm':
                self.create_message()
            elif command == 'help':
                print_help()
            elif command == 'q':
                with sock_lock:
                    try:
                        send_message(self.sock, self.create_message_exit())
                        logger.info('Завершение работы по команде пользователя.')
                    except NonDictInputError:
                        logger.error('Соединение завершено с ошибкой')
                    print('Завершение соединения.')
                break
            elif command == 'c':
                with database_lock:
                    contact_list = self.database.get_contacts()
                for contact in contact_list:
                    print(contact)
            elif command == 'edit':
                self.edit_contacts()
            elif command == 'h':
                self.print_history_message()
            else:
                print('\nВведите "h" для справки!\n')

    def print_history_message(self):
        with database_lock:
            history_list = self.database.get_history_message()
            for message in history_list:
                print(
                    f'\nОт {message[0]} -> {message[1]}\nот {message[3]}\n{message[2]}\n============='
                )

    def edit_contacts(self):
        answer = input('Для удаления введите del, для добавления add: ')
        if answer == 'del':
            edit = input('Введите имя удаляемного контакта: ')
            with database_lock:
                if self.database.check_contact(edit):
                    self.database.del_contact(edit)
                else:
                    logger.error('Попытка удаления несуществующего контакта.')
        elif answer == 'add':
            edit = input('Введите имя создаваемого контакта: ')
            if self.database.check_user(edit):
                with database_lock:
                    self.database.add_contact(edit)
                with sock_lock:
                    try:
                        add_contact(self.sock, self.account_name, edit)
                    except ServerError:
                        logger.error('Не удалось отправить информацию на сервер.')
        else:
            return


class ClientReader(Thread, metaclass=ClientVerifier):
    def __init__(self, account_name, sock, database):
        self.account_name = account_name
        self.sock = sock
        self.database = database
        super().__init__()

    def run(self):
        while True:
            sleep(1)
            with sock_lock:
                try:
                    message = get_message(self.sock)

                except IncorrectDataReceivedError:
                    logger.error(f'Не удалось декодировать полученное сообщение.')
                except OSError as err:
                    if err.errno:
                        logger.critical(f'Потеряно соединение с сервером.')
                        break
                except (ConnectionError, ConnectionAbortedError, ConnectionResetError, json.JSONDecodeError):
                    logger.critical(f'Потеряно соединение с сервером.')
                    break
                else:
                    if ACTION in message and message[ACTION] == MESSAGE and SENDER in message \
                            and DESTINATION in message \
                            and MESSAGE_TEXT in message and message[DESTINATION] == self.account_name:
                        print(f'\nПолучено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                        logger.info(f'Получено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                    else:
                        logger.error(f'Получено некорректное сообщение с сервера: {message}')


def create_presence(account_name):
    out = {
        ACTION: PRESENCE,
        TIME: time(),
        USER: {
            ACCOUNT_NAME: account_name
        }
    }
    logger.debug(f'Сформировано {PRESENCE} сообщение для пользователя {account_name}')
    return out


def process_response_ans(message):
    logger.debug(f'Разбор приветственного сообщения от сервера: {message}')
    if RESPONSE in message:
        if message[RESPONSE] == 200:
            return '200 : OK'
        elif message[RESPONSE] == 400:
            raise ServerError(f'400 : {message[ERROR]}')
    raise ReqFieldMissingError(RESPONSE)


def arg_parser():
    parser = ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_name = namespace.name

    if not 1023 < server_port < 65536:
        logger.critical(
            f'Попытка запуска клиента с неподходящим номером порта: {server_port}.')
        exit(1)

    return server_address, server_port, client_name


# Функция запрос контакт листа
def contacts_list_request(sock, name):
    logger.debug(f'Запрос контакт листа для пользователся {name}')
    req = {
        ACTION: GET_CONTACTS,
        TIME: time(),
        USER: name
    }
    logger.debug(f'Сформирован запрос {req}')
    send_message(sock, req)
    ans = get_message(sock)
    logger.debug(f'Получен ответ {ans}')
    if RESPONSE in ans and ans[RESPONSE] == 202:
        return ans[LIST_INFO]
    else:
        raise ServerError


# Функция запроса списка известных пользователей
def user_list_request(sock, username):
    logger.debug(f'Запрос списка известных пользователей {username}')
    req = {
        ACTION: USERS_REQUEST,
        TIME: time(),
        ACCOUNT_NAME: username
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 202:
        return ans[LIST_INFO]
    else:
        raise ServerError


# Добавление контакта
def add_contact(sock, username, contact):
    logger.debug(f'Создание контакта {contact}')
    req = {
        ACTION: ADD_CONTACT,
        TIME: time(),
        USER: username,
        ACCOUNT_NAME: contact
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 200:
        pass
    else:
        raise ServerError('Ошибка создания контакта')
    print('Удачное создание контакта.')


# Функция удаления пользователя из контакт листа
def remove_contact(sock, username, contact):
    logger.debug(f'Создание контакта {contact}')
    req = {
        ACTION: REMOVE_CONTACT,
        TIME: time(),
        USER: username,
        ACCOUNT_NAME: contact
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 200:
        pass
    else:
        raise ServerError('Ошибка удаления клиента')
    print('Удачное удаление')


def database_load(sock, database, username):
    try:
        users_list = user_list_request(sock, username)
    except ServerError:
        logger.error('Ошибка запроса списка известных пользователей.')
    else:
        database.add_users(users_list)

    try:
        contacts_list = contacts_list_request(sock, username)
    except ServerError:
        logger.error('Ошибка запроса списка контактов.')
    else:
        for contact in contacts_list:
            database.add_contact(contact)


def main():
    print('Консольный месседжер. Клиентский модуль.')
    server_address, server_port, client_name = arg_parser()

    if not client_name:
        client_name = input('Введите имя пользователя: ')
    else:
        print(f'Клиентский модуль запущен с именем: {client_name}')

    logger.info(
        f'Запущен клиент с парамертами: адрес сервера: {server_address}, '
        f'порт: {server_port}, имя пользователя: {client_name}')

    try:
        transport = socket(AF_INET, SOCK_STREAM)
        transport.settimeout(1)
        transport.connect((server_address, server_port))
        send_message(transport, create_presence(client_name))
        answer = process_response_ans(get_message(transport))
        logger.info(f'Установлено соединение с сервером. Ответ сервера: {answer}')
        print(f'Установлено соединение с сервером.')
    except json.JSONDecodeError:
        logger.error('Не удалось декодировать полученную Json строку.')
        exit(1)
    except ServerError as error:
        logger.error(f'При установке соединения сервер вернул ошибку: {error.text}')
        exit(1)
    except ReqFieldMissingError as missing_error:
        logger.error(f'В ответе сервера отсутствует необходимое поле {missing_error.missing_field}')
        exit(1)
    except (ConnectionRefusedError, ConnectionError):
        logger.critical(
            f'Не удалось подключиться к серверу {server_address}:{server_port},'
            f' конечный компьютер отверг запрос на подключение.')
        exit(1)
    else:
        database = ClientDatabase(client_name)
        database_load(transport, database, client_name)

        module = ClientReader(client_name, transport, database)
        module.daemon = True
        module.start()

        module_sender = Client(client_name, transport, database)
        module_sender.daemon = True
        module_sender.start()
        logger.debug('Запущены процессы')

        while True:
            sleep(1)
            if module.is_alive() and module_sender.is_alive():
                continue
            break


if __name__ == '__main__':
    main()
