from datetime import datetime

from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime
from sqlalchemy.orm import mapper, sessionmaker

from common.variables import CLIENT_DATABASE


class ClientDatabase:
    class KnownUsers:
        user = None

        def __init__(self, user):
            self.id = None
            self.user = user

    class MessageHistory:
        def __init__(self, from_user, to_user, message):
            self.id = None
            self.from_user = from_user
            self.to_user = to_user
            self.message = message
            self.date = datetime.now()

    class Contacts:
        name = None

        def __init__(self, name):
            self.id = None
            self.name = name

    def __init__(self, name):
        self.database_engine = create_engine(f'{CLIENT_DATABASE}{name}.db3', echo=False, pool_recycle=7200,
                                             connect_args={'check_same_thread': False})
        self.metadata = MetaData()

        users = Table(
            'known_users', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('user', String)
        )

        message_history = Table(
            'message_history', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('from_user', String),
            Column('to_user', String),
            Column('message', String),
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
        if not self.session.query(self.Contacts).filter_by(name=contact).count():
            contact_row = self.Contacts(contact)
            self.session.add(contact_row)
            self.session.commit()

    def del_contact(self, contact):
        self.session.query(self.Contacts).filter_by(name=contact).delete()

    def add_users(self, users_list):
        self.session.query(self.KnownUsers).delete()
        for user in users_list:
            user_row = self.KnownUsers(user)
            self.session.add(user_row)
        self.session.commit()

    def save_message(self, from_user, to_user, message):
        message_row = self.MessageHistory(from_user, to_user, message)
        self.session.add(message_row)
        self.session.commit()

    def get_contacts(self):
        contacts = [contact[0] for contact in self.session.query(self.Contacts.name).all()]
        return contacts

    def get_users(self):
        users = [user[0] for user in self.session.query(self.KnownUsers.user).all()]
        return users

    def check_user(self, user):
        if self.session.query(self.KnownUsers).filter_by(user=user).count():
            return True
        return False

    def check_contact(self, contact):
        if self.session.query(self.Contacts).filter_by(name=contact).count():
            return True
        return False

    def get_history_message(self):
        query = self.session.query(self.MessageHistory)
        history = [(history_row.from_user, history_row.to_user, history_row.message, history_row.date)
                   for history_row in query.all()]
        return history


if __name__ == '__main__':
    test_db = ClientDatabase('test1')
    test_db.add_contact('test2')
    print(test_db.get_contacts())
    test_db.del_contact('test2')
    print(test_db.get_contacts())
