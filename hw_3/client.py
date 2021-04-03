import json
import logging
import sys

from argparse import ArgumentParser
from socket import socket, AF_INET, SOCK_STREAM
from threading import Thread
from time import time, sleep
from common.utils import send_message, get_message
from common.variables import ACTION, EXIT, TIME, ACCOUNT_NAME, MESSAGE, SENDER, DESTINATION, MESSAGE_TEXT, PRESENCE, \
    USER, RESPONSE, ERROR, DEFAULT_IP_ADDRESS, DEFAULT_PORT
from decos import log
from errors import IncorrectDataRecivedError, ServerError, ReqFieldMissingError
from metaclasses import ClientVerifier

logger = logging.getLogger('client')


def print_help():
    print('Поддерживаемые команды:')
    print('m - отправить сообщение. Кому и текст будет запрошены отдельно.')
    print('h - вывести подсказки по командам')
    print('q - выход из программы')


class Client(Thread, metaclass=ClientVerifier):

    def __init__(self, account_name, sock):
        self.account_name = account_name
        self.sock = sock
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

        try:
            send_message(self.sock, messages)
            logger.info(f'Отправленно сообщение пользователю {to}')
        except:
            logger.critical('Потеряно соодинение с сервером')
            exit(1)

    def run(self):
        print_help()
        while True:
            command = input('Введите команду: ')
            if command == 'm':
                self.create_message()
            elif command == 'h':
                print_help()
            elif command == 'q':
                try:
                    send_message(self.sock, self.create_message_exit())
                except:
                    pass
                logger.info('Завершение работы')
                break
            else:
                print('\nВведите "h" для справки!\n')


class ClientReader(Thread, metaclass=ClientVerifier):
    def __init__(self, account_name, sock):
        self.account_name = account_name
        self.sock = sock
        super().__init__()

    def run(self):
        while True:
            try:
                message = get_message(self.sock)
                if ACTION in message and message[ACTION] == MESSAGE and SENDER in message and DESTINATION in message \
                        and MESSAGE_TEXT in message and message[DESTINATION] == self.account_name:
                    print(f'\nПолучено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                    logger.info(f'Получено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                else:
                    logger.error(f'Некорректное сообщение с сервера {message}')
            except IncorrectDataRecivedError:
                logger.error(f'Не удалось декодировать полученное сообщение.')
            except (OSError, ConnectionError, ConnectionAbortedError, ConnectionResetError, json.JSONDecodeError):
                logger.critical(f'Потеряно соединение с сервером.')
                break


@log
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


@log
def process_response_ans(message):
    logger.debug(f'Разбор приветственного сообщения от сервера: {message}')
    if RESPONSE in message:
        if message[RESPONSE] == 200:
            return '200 : OK'
        elif message[RESPONSE] == 400:
            raise ServerError(f'400 : {message[ERROR]}')
    raise ReqFieldMissingError(RESPONSE)


@log
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
        module = ClientReader(client_name, transport)
        module.daemon = True
        module.start()

        module_sender = Client(client_name, transport)
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
