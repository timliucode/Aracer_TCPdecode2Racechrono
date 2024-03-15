import threading
import tkinter as tk

from twisted.internet import protocol
from twisted.internet import reactor
from twisted.python import log


def aracerChecksum(data):
    bytes_data = bytes.fromhex(data)
    lrc_byte = (sum(bytes_data) & 0xff)
    lrc_byte = ((~lrc_byte) + 1) & 0xff
    lrc_byte = lrc_byte - 7 if lrc_byte >= 7 else lrc_byte + 249  # 适当调整有符号数的值
    return "{:02X}".format(lrc_byte)


class HexadecimalInputWindow:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("packet input")

        self.inputs = []
        self.create_inputs()

        send_button = tk.Button(self.window, text="Send", command=self.print_inputs)
        send_button.grid(row=3, column=4)

        clear_button = tk.Button(self.window, text="Clear", command=self.clear_inputs)
        clear_button.grid(row=3, column=5)

        self.window.mainloop()

    def create_inputs(self):
        tk.Label(self.window, text=" ").grid(row=0, column=0)
        for i in range(8):
            tk.Label(self.window, text=str(i)).grid(row=1, column=i + 1)
            input_var = tk.StringVar()
            input_var.set("00")
            input_entry = tk.Entry(self.window, textvariable=input_var, width=3)
            input_entry.grid(row=2, column=i + 1)
            self.inputs.append(input_var)

    def print_inputs(self):
        global values
        values = [input_var.get().upper() for input_var in self.inputs]
        joinValues = "f801c00e000001820008" + "".join(values)
        AracerjoinValues = joinValues + aracerChecksum(joinValues)
        print(AracerjoinValues)

    def clear_inputs(self):
        for input_var in self.inputs:
            input_var.set("00")


class Proxy(protocol.Protocol):
    noisy = True

    peer = None

    def setPeer(self, peer):
        self.peer = peer

    def connectionLost(self, reason):
        if self.peer is not None:
            self.peer.transport.loseConnection()
            self.peer = None
        elif self.noisy:
            log.msg(f"Unable to connect to peer: {reason}")

    def dataReceived(self, data):
        global strr
        global stre
        global values
        # self.peer.transport.write(data)
        datae = data.hex()
        if datae[0:16] != "f801c00e00000182":
            self.peer.transport.write(data)
        elif datae[0:16] == "f801c00e00000182":
            self.peer.transport.write(stre)


class ProxyClient(Proxy):
    def connectionMade(self):
        self.peer.setPeer(self)

        # Wire this and the peer transport together to enable
        # flow control (this stops connections from filling
        # this proxy memory when one side produces data at a
        # higher rate than the other can consume).
        self.transport.registerProducer(self.peer.transport, True)
        self.peer.transport.registerProducer(self.transport, True)

        # We're connected, everybody can read to their hearts content.
        self.peer.transport.resumeProducing()


class ProxyClientFactory(protocol.ClientFactory):
    protocol = ProxyClient

    def setServer(self, server):
        self.server = server

    def buildProtocol(self, *args, **kw):
        prot = protocol.ClientFactory.buildProtocol(self, *args, **kw)
        prot.setPeer(self.server)
        return prot

    def clientConnectionFailed(self, connector, reason):
        self.server.transport.loseConnection()


class ProxyServer(Proxy):
    clientProtocolFactory = ProxyClientFactory
    reactor = None

    def connectionMade(self):
        # Don't read anything from the connecting client until we have
        # somewhere to send it to.
        self.transport.pauseProducing()

        client = self.clientProtocolFactory()
        client.setServer(self)

        if self.reactor is None:
            from twisted.internet import reactor

            self.reactor = reactor
        self.reactor.connectTCP(self.factory.host, self.factory.port, client)


class ProxyFactory(protocol.Factory):
    """
    Factory for port forwarder.
    """

    protocol = ProxyServer

    def __init__(self, host, port):
        self.host = host
        self.port = port


def start():
    app = HexadecimalInputWindow()


t = threading.Thread(target=start)
t.start()

source = ("192.168.1.13", 6666)
destination = ("192.168.1.13", 6667)

# 創建代理工廠
factory = ProxyFactory(*destination)

# 啟動代理
reactor.listenTCP(source[1], factory)

# 開始事件循環
reactor.run()

app = HexadecimalInputWindow()
