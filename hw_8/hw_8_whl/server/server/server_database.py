from datetime import datetime

from sqlalchemy import create_engine, Table, Column, Integer, String, \
    MetaData, ForeignKey, DateTime, Text
from sqlalchemy.orm import mapper, sessionmaker
from common.variables import SERVER_DATABASE
from sqlalchemy.sql import default_comparator
from sqlalchemy.ext import baked
from sqlite3 import dbapi2 as sqlite


class ServerDB:
    """
    Класс - оболочка для работы с базой данных сервера.
    Использует SQLite базу данных, реализован с помощью
    SQLAlchemy ORM и используется классический подход.
    """

    class AllUsers:
        """Класс - отображение таблицы всех пользователей"""
        id, user, last_login = None, None, None

        def __init__(self, user, password_hash):
            self.id = None
            self.user = user
            self.last_login = datetime.now()
            self.password_hash = password_hash
            self.pubkey = None

    class ActiveUsers:
        """Класс - отображение таблицы активных пользователей"""
        login_time, ip, port, user = None, None, None, None

        def __init__(self, user, ip, port, login_time):
            self.id = None
            self.user = user
            self.ip = ip
            self.port = port
            self.login_time = login_time

    class LoginHistory:
        """Класс - отображение таблицы истории входов"""
        date_conn, ip, port = None, None, None

        def __init__(self, user, ip, port, date_conn):
            self.id = None
            self.user = user
            self.ip = ip
            self.port = port
            self.date_conn = date_conn

    class UsersContacts:
        """Класс - отображение таблицы контактов пользователей"""
        user, contact = None, None

        def __init__(self, user, contact):
            self.id = None
            self.user = user
            self.contact = contact

    class UsersHistoryMessage:
        """Класс - отображение таблицы истории действий"""
        sent, accepted = None, None

        def __init__(self, user):
            self.id = None
            self.user = user
            self.sent = 0
            self.accepted = 0

    def __init__(self, path):
        self.database_engine = create_engine(
            f'{SERVER_DATABASE}{path}', echo=False, pool_recycle=7200,
            connect_args={'check_same_thread': False})
        self.metadata = MetaData()

        users_table = Table(
            'All_users', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('user', String, unique=True),
            Column('last_login', DateTime),
            Column('password_hash', String),
            Column('pubkey', Text)
        )

        active_users_table = Table(
            'Active_users', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('user', ForeignKey('All_users.id'), unique=True),
            Column('ip', String),
            Column('port', Integer),
            Column('login_time', DateTime)
        )

        user_login_history = Table(
            'Login_history', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('user', ForeignKey('All_users.id')),
            Column('ip', String),
            Column('port', String),
            Column('date_conn', DateTime)
        )

        contacts = Table(
            'Contacts', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('user', ForeignKey('All_users.id')),
            Column('contact', ForeignKey('All_users.id'))
        )

        users_history_message = Table(
            'History_message', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('user', ForeignKey('All_users.id')),
            Column('sent', Integer),
            Column('accepted', Integer)
        )

        self.metadata.create_all(self.database_engine)

        mapper(self.AllUsers, users_table)
        mapper(self.ActiveUsers, active_users_table)
        mapper(self.LoginHistory, user_login_history)
        mapper(self.UsersContacts, contacts)
        mapper(self.UsersHistoryMessage, users_history_message)

        session = sessionmaker(bind=self.database_engine)
        self.session = session()

        self.session.query(self.ActiveUsers).delete()
        self.session.commit()

    def user_login(self, name, ip, port, key):
        """
        Метод выполняющийся при входе пользователя, записывает в базу факт входа
        Обновляет открытый ключ пользователя при его изменении.
        """

        result = self.session.query(self.AllUsers).filter_by(user=name)

        if result.count():
            user = result.first()
            user.last_login = datetime.now()
            if user.pubkey != key:
                user.pubkey = key
        else:
            raise ValueError('пользователь не зареистрирован')

        new_active_user = self.ActiveUsers(user.id, ip, port, datetime.now())
        self.session.add(new_active_user)

        history = self.LoginHistory(user.id, ip, port, datetime.now())
        self.session.add(history)

        self.session.commit()

    def add_user(self, name, password_hash):
        """
        Метод регистрации пользователя.
        Принимает имя и хэш пароля, создаёт запись в таблице статистики
        """
        user_row = self.AllUsers(name, password_hash)
        self.session.add(user_row)
        self.session.commit()
        history_row = self.UsersHistoryMessage(user_row.id)
        self.session.add(history_row)
        self.session.commit()

    def remove_user(self, name):
        """Метод удаляющий пользователя из базы"""
        try:
            user = self.session.query(
                self.AllUsers).filter_by(user=name).first()
            self.session.query(
                self.ActiveUsers).filter_by(user=user.id).delete()
            self.session.query(
                self.LoginHistory).filter_by(user=user.id).delete()
            self.session.query(
                self.UsersContacts).filter_by(user=user.id).delete()
            self.session.query(
                self.UsersContacts).filter_by(contact=user.id).delete()
            self.session.query(self.AllUsers).filter_by(user=name).delete()
            self.session.commit()
        except AttributeError:
            pass

    def get_hash(self, name):
        """Метод получения хэша пароля пользователя"""
        user = self.session.query(self.AllUsers).filter_by(user=name).first()
        return user.password_hash

    def get_pubkey(self, name):
        """Метод получения публичного ключа пользователя"""
        user = self.session.query(self.AllUsers).filter_by(user=name).first()
        return user.pubkey

    def check_user(self, name):
        """Метод проверяющий существование пользователя"""
        if self.session.query(self.AllUsers).filter_by(user=name).count():
            return True
        return False

    def user_logout(self, name):
        """Метод фиксирующий отключения пользователя"""
        user = self.session.query(self.AllUsers).filter_by(user=name).first()
        self.session.query(self.ActiveUsers).filter_by(user=user.id).delete()
        self.session.commit()

    def users_list(self):
        """
        Метод возвращающий список известных пользователей со временем последнего входа
        """
        query = self.session.query(
            self.AllUsers.user,
            self.AllUsers.last_login,
        )
        return query.all()

    def active_users_list(self):
        """Метод возвращающий список активных пользователей"""
        query = self.session.query(
            self.AllUsers.user,
            self.ActiveUsers.ip,
            self.ActiveUsers.port,
            self.ActiveUsers.login_time
        ).join(self.AllUsers)
        return query.all()

    def login_history(self, name=None):
        """Метод возвращающий историю входов"""
        query = self.session.query(self.AllUsers.user,
                                   self.LoginHistory.date_conn,
                                   self.LoginHistory.ip,
                                   self.LoginHistory.port
                                   ).join(self.AllUsers)
        if name:
            query = query.filter(self.AllUsers.user == name)
        return query.all()

    def process_message(self, sender, recipient):
        """Метод записывающий в таблицу статистики факт передачи сообщения"""
        sender = self.session.query(
            self.AllUsers).filter_by(user=sender).first().id
        recipient = self.session.query(
            self.AllUsers).filter_by(user=recipient).first().id
        sender_sent = self.session.query(
            self.UsersHistoryMessage).filter_by(user=sender).first()
        sender_sent.sent += 1
        recipient_accepted = self.session.query(
            self.UsersHistoryMessage).filter_by(user=recipient).first()
        recipient_accepted.accepted += 1
        self.session.commit()

    def add_contact(self, user, contact):
        """Метод добавления контакта для пользователя"""
        try:
            user = self.session.query(
                self.AllUsers).filter_by(user=user).first()
            contact = self.session.query(
                self.AllUsers).filter_by(user=contact).first()

            if self.session.query(self.UsersContacts).filter_by(
                    user=user.id, contact=contact.id).count() or not contact:
                return

            contact_row = self.UsersContacts(user.id, contact.id)
            self.session.add(contact_row)
            self.session.commit()
        except AttributeError:
            pass

    def remove_contact(self, user, contact):
        """Метод удаления контакта пользователя"""
        user = self.session.query(self.AllUsers).filter_by(user=user).first()
        contact = self.session.query(
            self.AllUsers).filter_by(user=contact).first()

        if not contact:
            return

        self.session.query(self.UsersContacts).filter(
            self.UsersContacts.user == user.id,
            self.UsersContacts.contact == contact.id
        ).delete()
        self.session.commit()

    def get_contacts(self, user):
        """Метод возвращающий список контактов пользователя"""
        user = self.session.query(self.AllUsers).filter_by(user=user).one()

        query = self.session.query(
            self.UsersContacts,
            self.AllUsers.user
        ).filter_by(user=user.id).join(
            self.AllUsers, self.UsersContacts.contact == self.AllUsers.id
        )

        contacts_list = [contact[1] for contact in query.all()]
        return contacts_list

    def message_history(self):
        """Метод возвращающий статистику сообщений"""
        query = self.session.query(
            self.AllUsers.user,
            self.AllUsers.last_login,
            self.UsersHistoryMessage.sent,
            self.UsersHistoryMessage.accepted
        ).join(self.AllUsers).all()
        return query
