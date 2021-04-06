from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QDialog, QPushButton, QTableView


class StatWindow(QDialog):
    """Класс - окно со статистикой пользователей"""
    def __init__(self, database):
        super().__init__()
        self.database = database
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Статистика клиентов')
        self.setFixedSize(600, 700)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.close_button = QPushButton('Закрыть', self)
        self.close_button.move(250, 650)
        self.close_button.clicked.connect(self.close)

        self.stat_table = QTableView(self)
        self.stat_table.move(10, 10)
        self.stat_table.setFixedSize(580, 620)

        self.create_stat_model()

    def create_stat_model(self):
        """Метод реализующий заполнение таблицы статистикой сообщений."""
        stat_list = self.database.message_history()
        list_q = QStandardItemModel()
        list_q.setHorizontalHeaderLabels(
            ['Имя Клиента', 'Последний раз входил',
             'Сообщений отправлено', 'Сообщений получено']
        )
        for row in stat_list:
            user, last_seen, sent, recv_d = row
            user = QStandardItem(user)
            user.setEditable(False)
            last_seen = QStandardItem(str(last_seen.replace(microsecond=0)))
            last_seen.setEditable(False)
            sent = QStandardItem(str(sent))
            sent.setEditable(False)
            recv_d = QStandardItem(str(recv_d))
            recv_d.setEditable(False)
            list_q.appendRow([user, last_seen, sent, recv_d])
        self.stat_table.setModel(list_q)
        self.stat_table.resizeColumnsToContents()
        self.stat_table.resizeRowsToContents()
