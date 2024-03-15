from twisted.internet import reactor, protocol, defer

import aracerDecoode


def read_config(config):
    # 讀取 config.txt 檔案
    with open(config, 'r') as f:
        lines = f.readlines()

    # 將 ip 和 watchdog 的值設為變數並轉換成 bytes
    ip = lines[1].strip()
    watchdog = bytes.fromhex(lines[4].strip())

    # 將 init 內容設為陣列並轉換成 bytes
    init = [bytes.fromhex(line.strip()) for line in lines[7:]]

    return ip, watchdog, init


def checksum(cs):  # 計算NMEA0183校驗和
    checksum = 0
    for s in cs:
        checksum ^= ord(s)
    return '{:02X}'.format(checksum)


# 這個class是用來與ECU通訊的
class EcuClient(protocol.Protocol):
    def __init__(self):
        self.ip, self.watchdog, self.init = read_config('config.txt')

    def connectionMade(self):
        print("Connected to the server.")
        self.transport.setTcpNoDelay(True)  # 關閉 Nagle 算法
        self.send_init()
        reactor.callLater(1, self.send_watchdog)

    def send_init(self):
        if self.init:
            item = self.init.pop(0)
            self.transport.write(item)
            reactor.callLater(0.01, self.send_init)

    def send_watchdog(self):
        self.transport.write(self.watchdog)
        reactor.callLater(1, self.send_watchdog)

    def dataReceived(self, data):
        # 使用 Deferred 將接收到的數據轉交給外部函數處理
        rc3 = defer.Deferred()
        rc3.addCallback(aracerDecoode.convert)
        rc3.addCallback(aracerDecoode.broadcast)
        rc3.callback((factory.clients, data))



class EcuClientFactory(protocol.ReconnectingClientFactory):
    protocol = EcuClient

    def buildProtocol(self, addr):
        print("Building protocol...")
        self.resetDelay()
        return self.protocol()

    def clientConnectionFailed(self, connector, reason):
        print(f"Connection failed: {reason.getErrorMessage()}")
        self.retry(connector)

    def clientConnectionLost(self, connector, reason):
        print(f"Connection lost: {reason.getErrorMessage()}")
        self.retry(connector)


class RC3server(protocol.Protocol):
    def connectionMade(self):
        print("Client connected")
        if hasattr(self, 'factory'):
            self.factory.clients.append(self)


    def connectionLost(self, reason):
        print("Connection lost")
        if hasattr(self, 'factory'):
            self.factory.clients.remove(self)


class RC3serverFactory(protocol.Factory):
    def __init__(self):
        self.clients = []

    def buildProtocol(self, addr):
        protocol_instance = RC3server()
        protocol_instance.factory = self  # 设置factory属性
        return protocol_instance



if __name__ == '__main__':
    ip, watchdog, init = read_config('config.txt')
    print('ip:', ip)

    server_ip = "192.168.1.220"
    server_port = 12345

    reactor.connectTCP(server_ip, server_port, EcuClientFactory())

    port = 6666
    factory = RC3serverFactory()
    reactor.listenTCP(port, factory)
    print(f"Server listening on port {port}")
    reactor.run()
