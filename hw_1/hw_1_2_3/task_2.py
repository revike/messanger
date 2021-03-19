"""
2. Написать функцию host_range_ping() для перебора ip-адресов из заданного диапазона.
Меняться должен только последний октет каждого адреса.
По результатам проверки должно выводиться соответствующее сообщение.
"""
from ipaddress import ip_address
from socket import gethostbyname
from task_1 import host_ping


def host_range_ping():
    while True:
        ip = input('Введите первоночальный адрес: ')
        if ip == 'q':
            return 'Exit'
        try:
            ip = ip_address(ip)
            break
        except ValueError:
            try:
                ip_addr = gethostbyname(ip)
                ip = ip_address(ip_addr)
                break
            except:
                print('\n\tНеобходимо ввести адрес!\n')

    while True:
        try:
            quantity_ip = int(input('Сколько адресов проверить?: '))
            break
        except ValueError:
            print('\n\tНеобходимо ввести количество адресов для проверки!\n')

    list_address = []
    for addr in range(quantity_ip):
        addr_ip = ip + addr
        octet_end = int(str(addr_ip).split('.')[-1])

        if octet_end > 254:
            break
        else:
            list_address.append(addr_ip)

    result = host_ping(list_address)
    return result


if __name__ == '__main__':
    result = host_range_ping()
    print(result)
