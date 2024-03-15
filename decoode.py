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
            pass


def get_values(dataReceived, id, index, valueindex):
    for byte_str in dataReceived:
        if byte_str[0:2] == bytes.fromhex(id) and byte_str[4:5] == bytes.fromhex(index):
            return byte_str[valueindex[0]:valueindex[1]]
    return b'\x00'


def RC3(dataReceived):
    global GPGGA
    global GPRMC
    global RC3d
    GPS_UTC_hh = int.from_bytes(get_values(dataReceived, '0182', '01', (5, 6)), byteorder='big')
    GPS_UTC_mm = int.from_bytes(get_values(dataReceived, '0182', '01', (6, 7)), byteorder='big')
    GPS_UTC_ss = int.from_bytes(get_values(dataReceived, '0182', '01', (7, 8)), byteorder='big')
    GPS_UTC_ms = int.from_bytes(get_values(dataReceived, '0182', '01', (9, 10)), byteorder='big')
    GPS_Lat_deg = int(get_values(dataReceived, '0182', '01', (10, 11))[0] & 0x7F)
    GPS_Lat_min = int.from_bytes(get_values(dataReceived, '0182', '01', (11, 12)), byteorder='big')
    GPS_Lat_mmmm = int.from_bytes(get_values(dataReceived, '0182', '02', (5, 7)), byteorder='big')
    GPS_Lat_NS = 'S' if (get_values(dataReceived, '0182', '02', (7, 8))[0] & 0x80) else 'N'
    GPS_Lon_deg = int(get_values(dataReceived, '0182', '02', (8, 9))[0] & 0x7F)
    GPS_Lon_min = int.from_bytes(get_values(dataReceived, '0182', '02', (9, 10)), byteorder='big')
    GPS_Lon_mmmm = int.from_bytes(get_values(dataReceived, '0182', '02', (10, 12)), byteorder='big')
    GPS_Lon_EW = 'W' if (get_values(dataReceived, '0182', '03', (5, 6))[0] & 0x80) else 'E'
    GPS_Valid = 'A' if (get_values(dataReceived, '0182', '03', (6, 7))[0] & 0x80) else 'V'
    GPS_Speed = int.from_bytes(get_values(dataReceived, '0182', '03', (7, 8)), byteorder='big')
    TC_Xforce = ""
    TC_Yforce = ""
    TC_Zforce = ""
    rpm = int.from_bytes(get_values(dataReceived, '0182', '04', (8, 10)), byteorder='big')
    tps = int.from_bytes(get_values(dataReceived, '0182', '04', (10, 11)), byteorder='big')
    vss = int.from_bytes(get_values(dataReceived, '0182', '04', (11, 12)), byteorder='big')
    TC_Lean_Angle = ""
    TC_VSSFRRate = int.from_bytes(get_values(dataReceived, '0182', '05', (7, 8)), byteorder='big')
    Volt_batt = int.from_bytes(get_values(dataReceived, '0182', '05', (8, 9)), byteorder='big')
    T_eng = int.from_bytes(get_values(dataReceived, '0182', '05', (9, 10)), byteorder='big')
    T_air = int.from_bytes(get_values(dataReceived, '0182', '05', (10, 11)), byteorder='big')
    AFR_Wbo2 = int.from_bytes(get_values(dataReceived, '0182', '06', (5, 6)), byteorder='big')
    Cyl1_Eng_AP = int.from_bytes(get_values(dataReceived, '0182', '06', (6, 7)), byteorder='big')
    MGU_A = ""
    MGU_Temp = ""
    MGU_eBoostTimer = ""
    LaunchEN = ""
    TCStatus = ""
    SuspensionAD1 = ""
    SuspensionAD2 = ""

    if GPS_Valid == 'A':
        fix = '1'
    elif GPS_Valid == 'V':
        fix = '0'

    # $GPGGA,041245.800,2450.57532,N,12112.04516,E,2       ,8        ,1.08   ,311.00,M      ,    ,M      ,       ,       *7F
    # $定位 ,時間       ,緯度      ,北,經度      ,東,定位品質,可見衛星數,水平精度,海拔  ,海拔單位,高程,高程單位,差分時間,差分站ID*校驗碼
    # 定位品質說明:0=無效,1=GPS,2=DGPS,3=PPS,6=估算值
    GPGGAo = f"GNGGA,{GPS_UTC_hh}{GPS_UTC_mm}{GPS_UTC_ss}.{GPS_UTC_ms},{GPS_Lat_deg}{GPS_Lat_min}.{GPS_Lat_mmmm},{GPS_Lat_NS},{GPS_Lon_deg}{GPS_Lon_min}.{GPS_Lon_mmmm},{GPS_Lon_EW},{fix},,,,,,,,"

    # $GPRMC,041245.800,A   ,2450.57532,N,12112.04516,E,36.08       ,148.58,020122,     ,         ,       *1D
    # $定位 ,時間       ,狀態,緯度      ,北,經度       ,東,速度(knot節),方位角 ,日月年,磁偏角,磁偏角方向,模式指示*校驗碼
    # 狀態說明:A=有效定位，V=無效定位，一節=1.852公里/小時，模式指示說明:A=自動，D=差分，E=估算，N=數據無效，S=模擬
    GPRMCo = f"GNRMC,{GPS_UTC_hh}{GPS_UTC_mm}{GPS_UTC_ss}.{GPS_UTC_ms},{GPS_Valid},{GPS_Lat_deg}{GPS_Lat_min}.{GPS_Lat_mmmm},{GPS_Lat_NS},{GPS_Lon_deg}{GPS_Lon_min}.{GPS_Lon_mmmm},{GPS_Lon_EW},{GPS_Speed},,{date},,,"

    # $RC3,[time],[count],[xacc],[yacc],[zacc],[gyrox],[gyroy],[gyroz],[rpm/d1],[d2],[a1],[a2],[a3],[a4],[a5],[a6],[a7],[a8],[a9],[a10],[a11],[a12],[a13],[a14],[a15]*[checksum]
    # 只要o2及qs能分開輸出AD就可使用於suspension
    RC3do = f"RC3,{GPS_UTC_hh}{GPS_UTC_mm}{GPS_UTC_ss}.{GPS_UTC_ms},,{TC_Xforce},{TC_Yforce},{TC_Zforce},,,,{rpm},{tps},{vss},{TC_Lean_Angle},{TC_VSSFRRate},{Volt_batt},{T_eng},{T_air},{AFR_Wbo2},{Cyl1_Eng_AP},{MGU_A},{MGU_Temp},{MGU_eBoostTimer},{LaunchEN},{TCStatus},{SuspensionAD1},{SuspensionAD2}"

    GPGGA = f"${GPGGAo}*{checksum(GPGGAo)}\n"
    GPRMC = f"${GPRMCo}*{checksum(GPRMCo)}\n"
    RC3d = f"${RC3do}*{checksum(RC3do)}\n"


def checksum(cs):  # 計算NMEA0183校驗和
    checksum = 0
    for s in cs:
        checksum ^= ord(s)
    return '{:02X}'.format(checksum)
