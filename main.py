def read_config():
    # 讀取 config.txt 檔案
    with open('config.txt', 'r') as f:
        lines = f.readlines()

    # 將 ip 和 watchdog 的值設為變數
    ip = lines[1].strip()
    watchdog = lines[4].strip()

    # 將 init 內容設為陣列
    init = [line.strip() for line in lines[7:]]

    return ip, watchdog, init


def checksum(cs):  # 計算NMEA0183校驗和
    checksum = 0
    for s in cs:
        checksum ^= ord(s)
    return '{:02X}'.format(checksum)


if __name__ == '__main__':
    ip, watchdog, init = read_config()
    print('ip:', ip)
    print('watchdog:', watchdog)
    print('init:', init)
