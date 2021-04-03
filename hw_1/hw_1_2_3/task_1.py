"""
1. Написать функцию host_ping(), в которой с помощью утилиты ping
будет проверяться доступность сетевых узлов.
Аргументом функции является список, в котором каждый сетевой узел
должен быть представлен именем хоста или ip-адресом.
В функции необходимо перебирать ip-адреса и проверять
их доступность с выводом соответствующего сообщения
(«Узел доступен», «Узел недоступен»). При этом ip-адрес
сетевого узла должен создаваться с помощью функции ip_address().
"""
from ipaddress import ip_address
from subprocess import Popen, PIPE


def host_ping(address: list, timeout=500, requests=1):
    result = dict()
    available = list()
    not_available = list()
    for ip_addr in address:
        try:
            ip_addr = ip_address(ip_addr)
        except ValueError:
            pass
        work = Popen(f'ping {ip_addr} -w {timeout} -n {requests}', shell=False, stdout=PIPE)
        work.wait()

        if work.returncode == 0:
            available.append(str(ip_addr))
            result['Доступные узлы'] = available
        else:
            not_available.append(str(ip_addr))
            result['Недоступные узлы'] = not_available

    try:
        if result['Доступные узлы']:
            pass
    except KeyError:
        result['Доступные узлы'] = []

    try:
        if result['Недоступные узлы']:
            pass
    except KeyError:
        result['Недоступные узлы'] = []

    return result


if __name__ == '__main__':
    address = ['192.168.0.1', '192.168.0.100', 'mail.ru', 'yandex.ru', 'vk.com']
    result = host_ping(address)
    print(result)
