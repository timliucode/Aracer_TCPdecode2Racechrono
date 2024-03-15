"""
aracer tcp raw data format:
實際上就是經過包裝的標準CANBUS包，每個包的格式如下：
每包19byte
ex:f801c00e00000182000801043a2a01f419012f
扣掉f801c00e0000 標頭
CAN包的範圍
"
CAN ID:01 82
DLC:08
data:01 04 3a 2a 01 f4 19 01
"
checksum:2f

經過研究，data的第一個byte是index
data00 index
data01~07 數據實際內容
按照實際數據的不同，占用位數也不一樣

checksum是LRC校驗碼

"""
ID = '0182'  # CAN ID (這是monitor的ID)
length = 19  # 1個CAN包加上前綴及checksum的長度


def convert(args):
    clients, data = args
    buffer = b""  # 用於存放不完整的數據
    buffer += data  # 將收到的數據添加到 buffer 中
    while len(buffer) >= length:  # 如果 buffer 中的數據大於等於一條數據的長度
        message = buffer[:length]  # 獲取一條數據
        buffer = buffer[length:]  # 從 buffer 中刪除這條數據
        if message[6:8] == bytes.fromhex(ID):  # 如果這條數據的ID是我們需要的
            if message[10] == 1:  # index:1
                gps_utc_hh = message[11]
                gps_utc_mm = message[12]
                gps_utc_ss = message[13]
                gps_utc_ms = int.from_bytes(message[14:16], byteorder='big')
                gps_lat_deg = message[16]
                gps_lat_min = message[17]
            elif message[10] == 2:
                gps_lat_sec = int.from_bytes(message[11:13], byteorder='big')
                gps_lat_ns = chr(message[13])
                gps_lon_deg = message[14]
                gps_lon_min = message[15]
                gps_lon_sec = int.from_bytes(message[16:18], byteorder='big')
            elif message[10] == 3:
                gps_lon_ew = chr(message[11])
                gps_valid = message[12]
                gps_speed = int.from_bytes(message[13:15], byteorder='big') * 0.539956803
            elif message[10] == 4:
                rpm = int.from_bytes(message[14:16], byteorder='big')
                tps = message[16] / 255 * 100
                vss1 = message[17]
            elif message[10] == 5:
                vss2 = message[11]
                tc_lean_angle = message[12] - 127
                tc_vss_fr_rate = message[13] * 0.78
                volt_batt = message[14] / 10
                t_eng = message[15] - 28
                t_air = message[16] - 28
                afr_wbo2_1 = message[17]
            elif message[10] == 6:
                afr_wbo2_2 = message[11]
                cyl1_eng_ap = message[12]
                cyl1_eng_ap_decimal = message[13]
                racelanuh_en = message[14]
                tc_status = message[15]

                




def checksum(cs):  # 計算NMEA0183校驗和
    checksum = 0
    for s in cs:
        checksum ^= ord(s)
    return '{:02X}'.format(checksum)
