from twisted.internet import reactor, protocol, defer


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
        print(f"Received data: {data}")
        # 使用 Deferred 將接收到的數據轉交給外部函數處理
        # d = defer.Deferred()
        # d.addCallback(processData, self)
        # d.callback(data)


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


if __name__ == '__main__':
    ip, watchdog, init = read_config('config.txt')
    print('ip:', ip)
    print('watchdog:', watchdog)
    print('init:', init)
    for i in init:
        print(i)

    server_ip = "192.168.1.220"
    server_port = 12345

    factory = EcuClientFactory()
    reactor.connectTCP(server_ip, server_port, factory)
    reactor.run()
