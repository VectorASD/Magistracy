# просто дублировал эти функции из utils.py рабочей директории нашей дисциплины

def check_connection(client):
    try:
        response = client.admin.command("ping")
        assert response == {'ok': 1.0}, response
        print("Соединение установлено!")
    except Exception as e:
        print("Ошибка соединения:", e)
        exit()
    # Изменение порта действительно приводит к:
    # Ошибка соединения: localhost:27018: [WinError 10061] Подключение не установлено, т.к. конечный компьютер отверг запрос на подключение (configured timeouts: socketTimeoutMS: 20000.0ms, connectTimeoutMS: 20000.0ms), Timeout: 30s, Topology Description: <TopologyDescription id: 691ae74fb16be12e51800d2b, topology_type: Unknown, servers: [<ServerDescription ('localhost', 27018) server_type: Unknown, rtt: None, error=AutoReconnect('localhost:27018: [WinError 10061] Подключение не установлено, т.к. конечный компьютер отверг запрос на подключение (configured timeouts: socketTimeoutMS: 20000.0ms, connectTimeoutMS: 20000.0ms)')>]>


def get_MongoDB_connection(): # shortcut
    # https://www.mongodb.com/try/download/community (756 Mb. "счастья")
    # https://www.mongodb.com/try/download/shell     (на сколько я понял, shell уже встроен в community)
    from pymongo import MongoClient # pip install pymongo[encryption]

    client = MongoClient("mongodb://localhost:27017/")
    print("client:", client)
    check_connection(client)
    return client
