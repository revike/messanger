import subprocess


def main():
    """Функция запуска лаунчера"""
    process = []
    while True:
        action = input(
            'Выберите действие: q - выход , '
            's - запустить сервер и клиенты, '
            'x - закрыть все окна:'
        )

        if action == 'q':
            break
        elif action == 's':
            while True:
                quantity_client = input('\nСколько клиентов запустить?: ')
                if quantity_client.isnumeric():
                    break
                else:
                    pass
            process = quantity_clients(int(quantity_client))

        elif action == 'x':
            while process:
                process.pop().kill()


def quantity_clients(quantity_client):
    """
    Функция запуска клиентов
    :param quantity_client: количество клиентов для запуска
    :return: если отрицательное число, то клиент не запускается
    """
    if quantity_client >= 0:
        process = [subprocess.Popen(
            'python server.py',
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )]

        i = 0
        while i < quantity_client:
            process.append(subprocess.Popen(
                f'python client.py -n t{i+1}',
                creationflags=subprocess.CREATE_NEW_CONSOLE)
            )
            i += 1
        return process
    return


if __name__ == '__main__':
    main()
