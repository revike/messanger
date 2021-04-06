from binascii import hexlify, a2b_base64
from hmac import new, compare_digest
from json import JSONDecodeError
from logging import getLogger
from os import urandom
from select import select
from socket import socket, AF_INET, SOCK_STREAM
from threading import Thread

from common.decos import login_required
from common.descriptors import Port, Address
from common.utils import send_message, get_message
from common.variables import *

logger = getLogger('server')


class MassageProcessor(Thread):
    """
    Основной класс сервера. Принимает содинения, словари - пакеты
    от клиентов, обрабатывает поступающие сообщения.
    Работает в качестве отдельного потока.
    """
    port = Port()
    ip = Address()

    def __init__(self, ip, port, database):
        self.ip = ip
        self.port = port
        self.database = database
        self.sock = None
        self.clients = []
        self.listen_sockets = None
        self.error_sockets = None
        self.running = True
        self.names = {}
        super().__init__()

    def remove_client(self, client):
        """
        Метод обработчик клиента с которым прервана связь.
        Ищет клиента и удаляет его из списков и базы
        """
        logger.info(f'Клиент {client.getpeername()} отключился от сервера.')
        for name in self.names:
            if self.names[name] == client:
                self.database.user_logout(name)
                del self.names[name]
                break
        self.clients.remove(client)
        client.close()

    def service_update_lists(self):
        """Метод реализующий отправки сервисного сообщения 205 клиентам"""
        for client in self.names:
            try:
                send_message(self.names[client], RESPONSE_205)
            except OSError:
                self.remove_client(self.names[client])

    def authorize_user(self, message, sock):
        """Метод реализующий авторизцию пользователей"""
        if message[USER][ACCOUNT_NAME] in self.names.keys():
            response = RESPONSE_400
            response[ERROR] = 'Умя пользователя уже занято'
            try:
                send_message(sock, response)
            except OSError:
                logger.debug('OSError')
            self.clients.remove(sock)
            sock.close()
        elif not self.database.check_user(message[USER][ACCOUNT_NAME]):
            response = RESPONSE_400
            response[ERROR] = 'Пользователь не зарегистрирован'
            try:
                send_message(sock, response)
            except OSError:
                pass
            self.clients.remove(sock)
            sock.close()
        else:
            message_auth = RESPONSE_511
            random_str = hexlify(urandom(64))
            message_auth[DATA] = random_str.decode('ascii')
            hash_get = new(self.database.get_hash(
                message[USER][ACCOUNT_NAME]), random_str, 'MD5')
            digest = hash_get.digest()
            try:
                send_message(sock, message_auth)
                ans = get_message(sock)
            except OSError:
                sock.close()
                return
            client_digest = a2b_base64(ans[DATA])

            if RESPONSE in ans and ans[RESPONSE] == 511 and compare_digest(
                    digest, client_digest):
                self.names[message[USER][ACCOUNT_NAME]] = sock
                ip, port = sock.getpeername()
                try:
                    send_message(sock, RESPONSE_200)
                except OSError:
                    self.remove_client(message[USER][ACCOUNT_NAME])
                self.database.user_login(message[USER][ACCOUNT_NAME], ip,
                                         port, message[USER][PUBLIC_KEY])
            else:
                response = RESPONSE_400
                response[ERROR] = 'Неверный пароль'
                try:
                    send_message(sock, response)
                except OSError:
                    pass
                self.clients.remove(sock)
                sock.close()

    @login_required
    def process_client_message(self, message, client):
        """Метод отбработчик поступающих сообщений"""
        if ACTION in message and message[ACTION] == PRESENCE and \
                TIME in message and USER in message:
            self.authorize_user(message, client)

        elif ACTION in message and message[ACTION] == MESSAGE and \
                DESTINATION in message and TIME in message \
                and SENDER in message and MESSAGE_TEXT in message and \
                self.names[message[SENDER]] == client:
            if message[DESTINATION] in self.names:
                self.database.process_message(message[SENDER],
                                              message[DESTINATION])
                self.process_message(message)
                try:
                    send_message(client, RESPONSE_200)
                except OSError:
                    self.remove_client(client)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Пользователь не зарегистрирован на сервере.'
                try:
                    send_message(client, response)
                except OSError:
                    pass
            return

        elif ACTION in message and message[ACTION] == EXIT and \
                ACCOUNT_NAME in message and \
                self.names[message[ACCOUNT_NAME]] == client:
            self.remove_client(client)

        elif ACTION in message and message[ACTION] == GET_CONTACTS and \
                USER in message and self.names[message[USER]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = self.database.get_contacts(message[USER])
            try:
                send_message(client, response)
            except OSError:
                self.remove_client(client)

        elif ACTION in message and message[ACTION] == ADD_CONTACT and \
                ACCOUNT_NAME in message and USER in message \
                and self.names[message[USER]] == client:
            self.database.add_contact(message[USER], message[ACCOUNT_NAME])
            try:
                send_message(client, RESPONSE_200)
            except OSError:
                self.remove_client(client)

        elif ACTION in message and message[ACTION] == REMOVE_CONTACT and \
                ACCOUNT_NAME in message and USER in message \
                and self.names[message[USER]] == client:
            self.database.remove_contact(message[USER], message[ACCOUNT_NAME])
            try:
                send_message(client, RESPONSE_200)
            except OSError:
                self.remove_client(client)

        elif ACTION in message and message[ACTION] == USERS_REQUEST and \
                ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = \
                [user[0] for user in self.database.users_list()]
            try:
                send_message(client, response)
            except OSError:
                self.remove_client(client)

        elif ACTION in message and message[ACTION] == PUBLIC_KEY_REQUEST and \
                ACCOUNT_NAME in message:
            response = RESPONSE_511
            response[DATA] = self.database.get_pubkey(message[ACCOUNT_NAME])

            if response[DATA]:
                try:
                    send_message(client, response)
                except OSError:
                    self.remove_client(client)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Нет публичного ключа для пользователя'
                try:
                    send_message(client, response)
                except OSError:
                    self.remove_client(client)
        else:
            response = RESPONSE_400
            response[ERROR] = 'Запрос некорректен.'
            try:
                send_message(client, response)
            except OSError:
                self.remove_client(client)

    def process_message(self, message):
        """Метод отправки сообщения клиенту"""
        if message[DESTINATION] in self.names and \
                self.names[message[DESTINATION]] in self.listen_sockets:
            try:
                send_message(self.names[message[DESTINATION]], message)
                logger.info(
                    f'Отправлено сообщение пользователю {message[DESTINATION]}'
                    f'от пользователя {message[SENDER]}.'
                )
            except OSError:
                self.remove_client(message[DESTINATION])
        elif message[DESTINATION] in self.names and \
                self.names[message[DESTINATION]] not in self.listen_sockets:
            logger.error(f'Связь с {message[DESTINATION]} была потеряна')
            self.remove_client(self.names[message[DESTINATION]])
        else:
            logger.error(
                f'пользователь {message[DESTINATION]} не зарегистрирован')

    def init_socket(self):
        """Метод инициализатор сокета"""
        transport = socket(AF_INET, SOCK_STREAM)
        transport.bind((self.ip, self.port))
        transport.settimeout(0.5)

        self.sock = transport
        self.sock.listen(MAX_CONNECTIONS)

    def run(self):
        """Метод основной цикл потока"""
        self.init_socket()

        while self.running:
            try:
                client, client_address = self.sock.accept()
            except OSError:
                pass
            else:
                logger.info(f'Установлено соединение с {client_address}')
                client.settimeout(5)
                self.clients.append(client)

            recv_data_lst = []

            try:
                if self.clients:
                    recv_data_lst, self.listen_sockets, self.error_sockets = \
                        select(self.clients, self.clients, [], 0)
            except OSError:
                logger.error('Ошибка работы с сокетами')

            if recv_data_lst:
                for client_with_message in recv_data_lst:
                    try:
                        self.process_client_message(
                            get_message(client_with_message),
                            client_with_message
                        )
                    except (OSError, TypeError, JSONDecodeError):
                        self.remove_client(client_with_message)
