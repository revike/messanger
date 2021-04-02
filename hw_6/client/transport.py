from binascii import hexlify, b2a_base64
from hashlib import pbkdf2_hmac
from hmac import new
from json import JSONDecodeError
from socket import socket, AF_INET, SOCK_STREAM
from threading import Thread, Lock
from time import time, sleep
from PyQt5.QtCore import pyqtSignal, QObject
from common.utils import send_message, get_message
from common.variables import *
from common.errors import ServerError

logger = logging.getLogger('client')
socket_lock = Lock()


class ClientTransport(Thread, QObject):
    new_message = pyqtSignal(dict)
    connection_lost = pyqtSignal()
    message_205 = pyqtSignal()

    def __init__(self, port, ip, database, user, password, keys):
        Thread.__init__(self)
        QObject.__init__(self)
        self.database = database
        self.user = user
        self.password = password
        self.keys = keys
        self.transport = None
        self.connection_init(port, ip)

        try:
            self.user_list_update()
            self.contacts_list_update()
        except OSError as err:
            if err.errno:
                logger.critical('Потеряно соединение с сервером!')
                raise ServerError('Потеряно соединение с сервером!')
        except JSONDecodeError:
            logger.critical('Потеряно соединение с сервером!')
            raise ServerError('Потеряно соединение с сервером!')
        self.running = True

    def connection_init(self, port, ip):
        self.transport = socket(AF_INET, SOCK_STREAM)
        self.transport.settimeout(5)

        connected = False
        for i in range(5):
            logger.info(f'Попытка подключения №{i + 1}')
            try:
                self.transport.connect((ip, port))
            except (OSError, ConnectionRefusedError):
                pass
            else:
                connected = True
                break
            sleep(1)

        if not connected:
            logger.critical('Не удалось установить соединение с сервером')
            raise ServerError('Не удалось установить соединение с сервером')
        logger.debug('Установлено соединение с сервером')

        password_bytes = self.password.encode('utf-8')
        salt = self.user.lower().encode('utf-8')
        password_hash = pbkdf2_hmac('sha512', password_bytes, salt, 10000)
        password_hash_str = hexlify(password_hash)

        pubkey = self.keys.publickey().export_key().decode('ascii')

        with socket_lock:
            presence = {
                ACTION: PRESENCE,
                TIME: time(),
                USER: {
                    ACCOUNT_NAME: self.user,
                    PUBLIC_KEY: pubkey
                }
            }

        try:
            send_message(self.transport, presence)
            ans = get_message(self.transport)
            if RESPONSE in ans:
                if ans[RESPONSE] == 400:
                    raise ServerError(ans[ERROR])
                elif ans[RESPONSE] == 511:
                    ans_data = ans[DATA]
                    hash_client = new(password_hash_str, ans_data.encode('utf-8'), 'MD5')
                    digest = hash_client.digest()
                    my_ans = RESPONSE_511
                    my_ans[DATA] = b2a_base64(digest).decode('ascii')
                    send_message(self.transport, my_ans)
                    self.process_server_ans(get_message(self.transport))
        except (OSError, JSONDecodeError):
            logger.critical('Потеряно соединение с сервером!')
            raise ServerError('Потеряно соединение с сервером!')

    def create_presence(self):
        out = {
            ACTION: PRESENCE,
            TIME: time(),
            USER: {
                ACCOUNT_NAME: self.user
            }
        }
        logger.debug(f'Сформировано {PRESENCE} сообщение для пользователя {self.user}')
        return out

    def process_server_ans(self, message):
        logger.debug(f'Разбор приветственного сообщения от сервера: {message}')
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                return
            elif message[RESPONSE] == 400:
                raise ServerError(f'{message[ERROR]}')
            elif message[RESPONSE] == 205:
                self.user_list_update()
                self.contacts_list_update()
                self.message_205.emit()
            else:
                logger.debug('Неизвестная ошибка')

        elif ACTION in message and message[ACTION] == MESSAGE and SENDER in message and DESTINATION in message \
                and MESSAGE_TEXT in message and message[DESTINATION] == self.user:
            logger.debug(f'Получено сообщение от пользователя {message[SENDER]}:{message[MESSAGE_TEXT]}')
            self.new_message.emit(message)

    def contacts_list_update(self):
        self.database.contacts_clear()

        reg = {
            ACTION: GET_CONTACTS,
            TIME: time(),
            USER: self.user
        }

        with socket_lock:
            send_message(self.transport, reg)
            ans = get_message(self.transport)

        if RESPONSE in ans and ans[RESPONSE] == 202:
            for contact in ans[LIST_INFO]:
                self.database.add_contact(contact)
        else:
            logger.error('Не удалось обновить список контактов')

    def user_list_update(self):
        req = {
            ACTION: USERS_REQUEST,
            TIME: time(),
            ACCOUNT_NAME: self.user
        }

        with socket_lock:
            send_message(self.transport, req)
            ans = get_message(self.transport)
        if RESPONSE in ans and ans[RESPONSE] == 202:
            self.database.add_users(ans[LIST_INFO])
        else:
            logger.error('Не удалось обновить список известных пользователей')

    def add_contact(self, contact):
        logger.debug(f'Создание контакта {contact}')
        req = {
            ACTION: ADD_CONTACT,
            TIME: time(),
            USER: self.user,
            ACCOUNT_NAME: contact
        }
        with socket_lock:
            send_message(self.transport, req)
            self.process_server_ans(get_message(self.transport))

    def remove_contact(self, contact):
        logger.debug(f'Удаление контакта {contact}')
        req = {
            ACTION: REMOVE_CONTACT,
            TIME: time(),
            USER: self.user,
            ACCOUNT_NAME: contact
        }
        with socket_lock:
            send_message(self.transport, req)
            self.process_server_ans(get_message(self.transport))

    def transport_shutdown(self):
        self.running = False

        msg = {
            ACTION: EXIT,
            TIME: time(),
            ACCOUNT_NAME: self.user
        }

        with socket_lock:
            try:
                send_message(self.transport, msg)
            except OSError:
                pass
        sleep(0.5)

    def send_message(self, to, message):
        msg = {
            ACTION: MESSAGE,
            SENDER: self.user,
            DESTINATION: to,
            TIME: time(),
            MESSAGE_TEXT: message
        }

        with socket_lock:
            send_message(self.transport, msg)
            self.process_server_ans(get_message(self.transport))
            logger.info(f'Отправлено сообщение для пользователя {to}')

    def key_request(self, user):
        req = {
            ACTION: PUBLIC_KEY_REQUEST,
            TIME: time(),
            ACCOUNT_NAME: user
        }

        with socket_lock:
            send_message(self.transport, req)
            ans = get_message(self.transport)
        if RESPONSE in ans and ans[RESPONSE] == 511:
            return ans[DATA]
        else:
            logger.error(f'Не удалось получить ключ от {user}')

    def run(self):
        while self.running:
            sleep(1)
            message = None
            with socket_lock:
                try:
                    self.transport.settimeout(0.5)
                    message = get_message(self.transport)
                except OSError as err:
                    if err.errno:
                        logger.critical('Потеряно соединение с сервером!')
                        self.running = False
                        self.connection_lost.emit()
                except (
                        ConnectionError, ConnectionAbortedError, ConnectionResetError, JSONDecodeError, TypeError):
                    logger.debug('Потеряно соединение с сервером')
                    self.running = False
                    self.connection_lost.emit()
                finally:
                    self.transport.settimeout(5)

            if message:
                logger.debug(f'Принято сообщение с сервера: {message}')
                self.process_server_ans(message)
