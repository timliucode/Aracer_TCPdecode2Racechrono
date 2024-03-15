from twisted.internet import reactor, protocol, defer
from twisted.internet.protocol import DatagramProtocol

import decoode


# 讀取 config.txt 檔案
def read_config(config):
    with open(config, 'r') as f:
        lines = f.readlines()

    # 將 watchdog 的值設為變數並轉換成 bytes
    watchdog = bytes.fromhex(lines[1].strip())

    # 將 init 內容設為陣列並轉換成 bytes
    init = [bytes.fromhex(line.strip()) for line in lines[4:]]

    return watchdog, init


# 這個class是用來處理ECU UDP發現的
class EcuUDPdiscover(DatagramProtocol):
    def __init__(self):
        self.timeout_deferred = None  # 初始化timeout_deferred屬性

    # 連線成功後執行
    def startProtocol(self):
        self.timeout_deferred = reactor.callLater(10, self.timeout)  # 設定10秒的超時時間

    # 接收數據
    def datagramReceived(self, datagram, address):
        if b'aRacer' in datagram:  # 如果收到了aracer的關鍵字
            print(f"Received a packet containing 'aRacer' from {address}")  # 打印收到的數據
            ecuConnect(address[0])  # 連接ECU
            self.transport.stopListening()  # 停止監聽
            if self.timeout_deferred.active():  # 如果收到了期望的關鍵字，取消超時操作
                self.timeout_deferred.cancel()

    # 超時操作
    def timeout(self):
        print("Timeout")
        self.transport.stopListening()  # 停止監聽
        ecuConnect("192.168.88.88")  # 連接預設ECU IP位置


# 建立新的UDP接收器
def ecuUDPdiscoverStart():
    udp = EcuUDPdiscover()
    reactor.listenUDP(8888, udp)
    print("Listening for UDP packets...")


# 連接ECU
def ecuConnect(ecu_ip):
    print('connect ip:', ecu_ip)
    reactor.connectTCP(ecu_ip, ecu_port, EcuClientFactory())  # 連接ECU


# 這個class是用來處理ECU通訊的
class EcuClient(protocol.Protocol):
    # 初始化config.txt的內容
    def __init__(self):
        self.watchdog, self.init = read_config('config.txt')

    # 連線成功後執行
    def connectionMade(self):
        print("Connected to the server.")
        self.transport.setTcpNoDelay(True)  # 關閉 Nagle 算法
        self.send_init()  # 發送初始化數據
        reactor.callLater(1, self.send_watchdog)  # 每1秒發送一次 watchdog

    # 發送初始化數據
    def send_init(self):
        if self.init:
            item = self.init.pop(0)
            self.transport.write(item)
            reactor.callLater(0.01, self.send_init)

    # 發送 watchdog
    def send_watchdog(self):
        self.transport.write(self.watchdog)
        reactor.callLater(1, self.send_watchdog)

    # 接收數據
    def dataReceived(self, data):
        # 使用 Deferred 將接收到的數據轉交給外部函數處理
        rc3 = defer.Deferred()  # 創建一個Deferred對象
        rc3.addCallback(decoode.convert)  # 添加一個外部decode回調函數
        rc3.addCallback(broadcast)  # 添加一個向server發送數據的回調函數
        rc3.callback(data)  # 調用callback方法，將數據傳遞給回調函數


# 這個class是用來創建EcuClient的
class EcuClientFactory(protocol.ReconnectingClientFactory):
    protocol = EcuClient  # 設置protocol屬性為EcuClient

    # 創建protocol
    def buildProtocol(self, addr):
        print("Building protocol...")
        self.resetDelay()  # 重置延遲
        return self.protocol()

    def clientConnectionFailed(self, connector, reason):
        if self.continueTrying:
            self.connector = connector
            self.retry()

    def clientConnectionLost(self, connector, unused_reason):
        if self.continueTrying:
            self.connector = connector
            self.retry()


# 這個class是用來處理RC3server通訊的
class RC3server(protocol.Protocol):
    # 連線成功後執行
    def connectionMade(self):
        print("Client connected")
        if hasattr(self, 'factory'):  # 如果有factory屬性
            self.factory.clients.append(self)  # 將自己添加到clients列表中

    # 連線失敗後執行
    def connectionLost(self, reason):
        print("Connection lost")
        if hasattr(self, 'factory'):  # 如果有factory屬性
            self.factory.clients.remove(self)  # 將自己從clients列表中移除


# 這個class是用來創建RC3server的
class RC3serverFactory(protocol.Factory):
    # 初始化
    def __init__(self):
        self.clients = []  # 創建一個空的clients列表

    # 創建protocol
    def buildProtocol(self, addr):
        protocol_instance = RC3server()  # 創建一個RC3server實例
        protocol_instance.factory = self  # 设置factory属性
        return protocol_instance  # 返回protocol實例


# 向所有客戶端廣播數據
def broadcast(message):
    clients = factory.clients  # 獲取clients列表
    for client in clients:  # 遍歷clients列表
        client.transport.write(message.encode())  # 向每個客戶端發送數據


if __name__ == '__main__':
    ecu_port = 6666
    ecuUDPdiscoverStart()  # 啟動ECU UDP發現

    factory = RC3serverFactory()  # 創建RC3serverFactory實例
    ports = range(7777, 7781)  # 服務器端口範圍，這麼做的原因是方便racechrono選擇僅RC3還是RC3+NMEA
    for port in ports:
        reactor.listenTCP(port, factory)
    print(f"Server listening on port {ports}")

    reactor.run()
