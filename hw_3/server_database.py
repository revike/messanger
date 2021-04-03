from datetime import datetime

from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey, DateTime
from sqlalchemy.orm import mapper, sessionmaker

from common.variables import SERVER_DATABASE


class ServerDB:

    class AllUsers:
        user, last_login = None, None

        def __init__(self, user):
            self.id = None
            self.user = user
            self.last_login = datetime.now()

    class ActiveUsers:
        login_time, ip, port = None, None, None

        def __init__(self, user, ip, port, login_time):
            self.id = None
            self.user = user
            self.ip = ip
            self.port = port
            self.login_time = login_time

    class LoginHistory:
        date_conn, ip, port = None, None, None

        def __init__(self, user, ip, port, date_conn):
            self.id = None
            self.user = user
            self.ip = ip
            self.port = port
            self.date_conn = date_conn

    def __init__(self):
        self.database_engine = create_engine(SERVER_DATABASE, echo=False, pool_recycle=7200)
        self.metadata = MetaData()

        users_table = Table('All_users', self.metadata,
                            Column('id', Integer, primary_key=True),
                            Column('user', String, unique=True),
                            Column('last_login', DateTime)
                            )

        active_users_table = Table('Active_users', self.metadata,
                                   Column('id', Integer, primary_key=True),
                                   Column('user', ForeignKey('All_users.id'), unique=True),
                                   Column('ip', String),
                                   Column('port', Integer),
                                   Column('login_time', DateTime)
                                   )

        user_login_history = Table('Login_history', self.metadata,
                                   Column('id', Integer, primary_key=True),
                                   Column('user', ForeignKey('All_users.id')),
                                   Column('ip', String),
                                   Column('port', String),
                                   Column('date_conn', DateTime)
                                   )

        self.metadata.create_all(self.database_engine)

        mapper(self.AllUsers, users_table)
        mapper(self.ActiveUsers, active_users_table)
        mapper(self.LoginHistory, user_login_history)

        session = sessionmaker(bind=self.database_engine)
        self.session = session()

        self.session.query(self.ActiveUsers).delete()
        self.session.commit()

    def user_login(self, name, ip, port):

        rez = self.session.query(self.AllUsers).filter_by(user=name)

        if rez.count():
            user = rez.first()
            user.last_login = datetime.now()
        else:
            user = self.AllUsers(user=name)
            self.session.add(user)
            self.session.commit()

        new_active_user = self.ActiveUsers(user.id, ip, port, datetime.now())
        self.session.add(new_active_user)

        history = self.LoginHistory(user.id, ip, port, datetime.now())
        self.session.add(history)

        self.session.commit()

    def user_logout(self, name):
        user = self.session.query(self.AllUsers).filter_by(user=name).first()
        self.session.query(self.ActiveUsers).filter_by(user=user.id).delete()
        self.session.commit()

    def users_list(self):
        query = self.session.query(
            self.AllUsers.user,
            self.AllUsers.last_login,
        )
        return query.all()

    def active_users_list(self):
        query = self.session.query(
            self.AllUsers.user,
            self.ActiveUsers.login_time,
            self.ActiveUsers.ip,
            self.ActiveUsers.port
            ).join(self.AllUsers)
        return query.all()

    def login_history(self, name=None):
        query = self.session.query(self.AllUsers.user,
                                   self.LoginHistory.date_conn,
                                   self.LoginHistory.ip,
                                   self.LoginHistory.port
                                   ).join(self.AllUsers)
        if name:
            query = query.filter(self.AllUsers.user == name)
        return query.all()


if __name__ == '__main__':
    test_db = ServerDB()
    # выполняем 'подключение' пользователя
    test_db.user_login('client_1', '192.168.1.4', 8888)
    test_db.user_login('client_2', '192.168.1.5', 7777)
    # выводим список кортежей - активных пользователей
    print(test_db.active_users_list())
    # выполянем 'отключение' пользователя
    test_db.user_logout('client_1')
    # выводим список активных пользователей
    print(test_db.active_users_list())
    # запрашиваем историю входов по пользователю
    test_db.login_history('client_1')
    # выводим список известных пользователей
    print(test_db.users_list())
