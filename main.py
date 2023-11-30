from twisted.conch.telnet import StatefulTelnetProtocol
from twisted.internet import reactor, protocol, task
import re


ip_value, watchdog_value, init_value = 0, 0, 0  # 定義全域變數

def read_config():
    global ip_value, watchdog_value, init_value
    # 打開文本文件
    with open('config.txt', 'r') as file:
        # 讀取文件內容
        content = file.read()

        # 使用正則表達式搜尋雙引號內的內容
        matches = re.findall(r'"(.*?)"', content)

        # 將讀取到的值分別存入變數
        ip_value, watchdog_value, init_value = matches



if __name__ == '__main__':
    read_config()
    # 印出讀取到的值
    print("IP:", ip_value)
    print("Watchdog:", watchdog_value)
    print("Init:", init_value)