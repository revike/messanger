from datetime import datetime
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, \
    String, DateTime, Text
from sqlalchemy.orm import mapper, sessionmaker
from common.variables import CLIENT_DATABASE
from sqlalchemy.sql import default_comparator
from sqlalchemy.ext import baked
from sqlite3 import dbapi2 as sqlite


class ClientDatabase:
    """
    Класс - оболочка для работы с базой данных клиента.
    Использует SQLite базу данных, реализован с помощью
    SQLAlchemy ORM и используется классический подход.
    """
    class KnownUsers:
        """Класс - отображение для таблицы всех пользователей"""
        user = None

        def __init__(self, user):
            self.id = None
            self.user = user

    class MessageHistory:
        """Класс - отображение для таблицы статистики переданных сообщений"""

        def __init__(self, contact, direction, message):
            self.id = None
            self.contact = contact
            self.direction = direction
            self.message = message
            self.date = datetime.now()

    class Contacts:
        """Класс - отображение для таблицы контактов"""
        name = None

        def __init__(self, name):
            self.id = None
            self.name = name

    def __init__(self, name):
        self.database_engine = create_engine(
            f'{CLIENT_DATABASE}{name}.db3',
            echo=False, pool_recycle=7200,
            connect_args={'check_same_thread': False}
        )
        self.metadata = MetaData()

        users = Table(
            'known_users', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('user', String)
        )

        message_history = Table(
            'message_history', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('contact', String),
            Column('direction', String),
            Column('message', Text),
            Column('date', DateTime)
        )

        contacts = Table(
            'contacts', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('name', String, unique=True)
        )

        self.metadata.create_all(self.database_engine)

        mapper(self.KnownUsers, users)
        mapper(self.MessageHistory, message_history)
        mapper(self.Contacts, contacts)

        session = sessionmaker(bind=self.database_engine)
        self.session = session()

        self.session.query(self.Contacts).delete()
        self.session.commit()

    def add_contact(self, contact):
        """Метод добавляющий контакт в базу данных"""
        if not self.session.query(
                self.Contacts).filter_by(name=contact).count():
            contact_row = self.Contacts(contact)
            self.session.add(contact_row)
            self.session.commit()

    def del_contact(self, contact):
        """Метод удаляющий определённый контакт"""
        self.session.query(self.Contacts).filter_by(name=contact).delete()

    def add_users(self, users_list):
        """Метод заполняющий таблицу известных пользователей"""
        self.session.query(self.KnownUsers).delete()
        for user in users_list:
            user_row = self.KnownUsers(user)
            self.session.add(user_row)
        self.session.commit()

    def save_message(self, contact, direction, message):
        """Метод сохраняющий сообщение в базе данных"""
        message_row = self.MessageHistory(contact, direction, message)
        self.session.add(message_row)
        self.session.commit()

    def get_contacts(self):
        """Метод возвращающий список всех контактов"""
        contacts = [contact[0] for contact in self.session.query(
            self.Contacts.name).all()]
        return contacts

    def get_users(self):
        """Метод возвращающий список всех известных пользователей"""
        users = [user[0] for user in self.session.query(
            self.KnownUsers.user).all()]
        return users

    def check_user(self, user):
        """Метод проверяющий существует ли пользователь"""
        if self.session.query(self.KnownUsers).filter_by(user=user).count():
            return True
        return False

    def check_contact(self, contact):
        """Метод проверяющий существует ли контакт"""
        if self.session.query(self.Contacts).filter_by(name=contact).count():
            return True
        return False

    def get_history_message(self, contact):
        """Метод возвращающий историю сообщений с определённым пользователем"""
        query = self.session.query(
            self.MessageHistory).filter_by(contact=contact)
        history = [(history_row.contact,
                    history_row.direction,
                    history_row.message,
                    history_row.date) for history_row in query.all()]
        return history

    def contacts_clear(self):
        """Метод очищающий таблицу со списком контактов"""
        self.session.query(self.Contacts).delete()
