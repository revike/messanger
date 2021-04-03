import logging
import sys

from argparse import ArgumentParser
from select import select
from socket import socket, AF_INET, SOCK_STREAM
from common.utils import send_message, get_message
from common.variables import DESTINATION, SENDER, ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, RESPONSE_200, \
    RESPONSE_400, ERROR, MESSAGE, MESSAGE_TEXT, EXIT, DEFAULT_PORT
from descriptors import Port
from metaclasses import ServerVerifier

logger = logging.getLogger('server')


class Server(metaclass=ServerVerifier):

    port = Port()

    def __init__(self, address, port):
        self.address = address
        self.port = port
        self.clients = []
        self.messages = []
        self.names = {}

    def socket(self):
        logger.info(
            f'Запущен сервер, порт для подключений: {self.port} , '
            f'адрес с которого принимаются подключения: {self.address}. '
            f'Если адрес не указан, принимаются соединения с любых адресов.')
        transport = socket(AF_INET, SOCK_STREAM)
        transport.bind((self.address, self.port))
        transport.settimeout(0.5)

        self.sock = transport
        self.sock.listen()

    def loop(self):
        self.socket()

        while True:
            try:
                client, client_address = self.sock.accept()
            except OSError:
                pass
            else:
                logger.info(f'Установлено соединение с {client_address}')
                self.clients.append(client)

            recv_data = []
            send_data = []

            try:
                if self.clients:
                    recv_data, send_data, err_data = select(self.clients, self.clients, [], 0)
            except OSError:
                pass

            if recv_data:
                for client_message in recv_data:
                    try:
                        self.client_message(get_message(client_message), client_message)
                    except:
                        logger.info(
                            f'Клиент {client_message.getpeername()} отключился от сервера.'
                        )
                        self.clients.remove(client_message)

            for message in self.messages:
                try:
                    self.process_message(message, send_data)
                except:
                    logger.info(f'Связь с клиентом {message[DESTINATION]} была потеряна')
                    self.clients.remove(self.names[message[DESTINATION]])
                    del self.names[message[DESTINATION]]
            self.messages.clear()

    def process_message(self, message, send_data):
        if message[DESTINATION] in self.names and self.names[message[DESTINATION]] in send_data:
            send_message(self.names[message[DESTINATION]], message)
            logger.info(
                f'Отправлено сообщение пользователю {message[DESTINATION]} от пользователя {message[SENDER]}.'
            )
        elif message[DESTINATION] in self.names and self.names[message[DESTINATION]] not in send_data:
            raise ConnectionError
        else:
            logger.error(
                f'Пользователь {message[DESTINATION]} не зарегистрирован на сервере.'
            )

    def client_message(self, message, client):
        if ACTION in message and message[ACTION] == PRESENCE and TIME in message and USER in message:
            if message[USER][ACCOUNT_NAME] not in self.names.keys():
                self.names[message[USER][ACCOUNT_NAME]] = client
                send_message(client, RESPONSE_200)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Имя пользователя уже занято.'
                send_message(client, response)
                self.clients.remove(client)
                client.close()
            return
        elif ACTION in message and message[ACTION] == MESSAGE and DESTINATION in message and TIME in message \
                and SENDER in message and MESSAGE_TEXT in message:
            self.messages.append(message)
            return
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message:
            self.clients.remove(self.names[ACCOUNT_NAME])
            self.names[ACCOUNT_NAME].close()
            del self.names[ACCOUNT_NAME]
            return
        else:
            response = RESPONSE_400
            response[ERROR] = 'Запрос некорректен.'
            send_message(client, response)
            return


def arg_parser():
    parser = ArgumentParser()
    parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-a', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p
    return listen_address, listen_port


def main():
    address, port = arg_parser()
    Server(address, port).loop()


if __name__ == '__main__':
    main()
