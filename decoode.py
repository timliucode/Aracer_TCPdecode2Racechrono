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
import timeit
import ast
import datetime
import inspect
import math


ID = '0182'  # CAN ID (這是monitor的ID)
length = 19  # 1個CAN包加上前綴及checksum的長度


def convert(data):
    # 計數
    if not hasattr(convert, 'count'):
        convert.count = 0
    convert.count += 1
    if convert.count > 65535:
        convert.count = 0

    buffer = b""  # 用於存放不完整的數據
    buffer += data  # 將收到的數據添加到 buffer 中
    while len(buffer) >= length:  # 如果 buffer 中的數據大於等於一條數據的長度
        message = buffer[:length]  # 獲取一條數據
        buffer = buffer[length:]  # 從 buffer 中刪除這條數據
        if message[6:8] == bytes.fromhex(ID):  # 如果这条数据的ID是我们需要的
            match message[10]:
                case 1:  # index:1
                    gps_utc_hh = f"{message[11]:02d}"
                    gps_utc_mm = f"{message[12]:02d}"
                    gps_utc_ss = f"{message[13]:02d}"
                    gps_utc_ms = f"{int.from_bytes(message[14:16], byteorder='big'):03d}"
                    gps_lat_deg = f"{message[16]:02d}"
                    gps_lat_min = f"{message[17]:02d}"
                case 2:
                    gps_lat_sec = f"{int.from_bytes(message[11:13], byteorder='big'):04d}"
                    gps_lat_ns = chr(message[13])
                    gps_lon_deg = f"{message[14]:02d}"
                    gps_lon_min = f"{message[15]:02d}"
                    gps_lon_sec = f"{int.from_bytes(message[16:18], byteorder='big'):04d}"
                case 3:
                    gps_lon_ew = chr(message[11])
                    gps_valid = chr(message[12])
                    gps_speed = f"{int.from_bytes(message[13:15], byteorder='big') * 0.539956803:.3f}"
                case 4:
                    rpm = int.from_bytes(message[14:16], byteorder='big')
                    tps = message[16] / 255 * 100
                    vss1 = message[17]
                case 5:
                    vss2 = message[11]
                    tc_lean_angle = message[12] - 127
                    tc_vss_fr_rate = message[13] * 0.78
                    volt_batt = message[14] / 10
                    t_eng = message[15] - 28
                    t_air = message[16] - 28
                    afr_wbo2_1 = message[17]
                case 6:
                    afr_wbo2_2 = message[11]
                    cyl1_eng_ap = message[12]
                    cyl1_eng_ap_decimal = message[13]
                    racelanuh_en = message[14]
                    tc_status = message[15]
                case _:
                    if gps_valid == "A":
                        quality = 1
                    else:  # 如果GPS無效
                        quality = 0

                    date = datetime.datetime.now(datetime.UTC).strftime('%d%m%y')

                    bearingcalc = BearingCalculator()
                    bearing = bearingcalc.calculate_bearing(gps_lat_sec, gps_lon_sec)

                    # $GNGGA,041245.800,2450.57532,N,12112.04516,E,2       ,8        ,1.08   ,311.00,M      ,    ,M      ,       , *7F
                    # $定位 ,時間       ,緯度      ,北,經度      ,東,定位品質,可見衛星數,水平精度,海拔  ,海拔單位,高程,高程單位,差分時間,差分站ID*校驗碼
                    # 定位品質說明:0=無效,1=GPS,2=DGPS,3=PPS,6=估算值
                    GGA = f"GNGGA,{gps_utc_hh}{gps_utc_mm}{gps_utc_ss}.{gps_utc_ms},{gps_lat_deg}{gps_lat_min}.{gps_lat_sec},{gps_lat_ns},{gps_lon_deg}{gps_lon_min}.{gps_lon_sec},{gps_lon_ew},{quality},,,,M,,M,,"

                    # $GNRMC,041245.800,A   ,2450.57532,N,12112.04516,E,36.08       ,148.58,020122,     ,         ,       *1D
                    # $定位 ,時間       ,狀態,緯度      ,北,經度       ,東,速度(knot節),方位角 ,日月年,磁偏角,磁偏角方向,模式指示*校驗碼
                    # 狀態說明:A=有效定位，V=無效定位，一節=1.852公里/小時，模式指示說明:A=自動，D=差分，E=估算，N=數據無效，S=模擬
                    RMC = f"GNRMC,{gps_utc_hh}{gps_utc_mm}{gps_utc_ss}.{gps_utc_ms},{gps_valid},{gps_lat_deg}{gps_lat_min}.{gps_lat_sec},{gps_lat_ns},{gps_lon_deg}{gps_lon_min}.{gps_lon_sec},{gps_lon_ew},{gps_speed},{bearing},{date},,,A"

                    # $RC3,[time],[count],[xacc],[yacc],[zacc],[gyrox],[gyroy],[gyroz],[rpm/d1],[d2],[a1],[a2],[a3],[a4],[a5],[a6],[a7],[a8],[a9],[a10],[a11],[a12],[a13],[a14],[a15]*[checksum]
                    RC3 = f"RC3,{gps_utc_hh}{gps_utc_mm}{gps_utc_ss}.{gps_utc_ms},{convert.count},,,,,,,{rpm},{tps},{vss1},{vss2},{tc_lean_angle},{tc_vss_fr_rate},{volt_batt},{t_eng},{t_air},{afr_wbo2_1},{afr_wbo2_2},{cyl1_eng_ap},{cyl1_eng_ap_decimal},{racelanuh_en}"

                    GNGGA = f"${GGA}*{checksum(GGA)}\n"
                    GNRMC = f"${RMC}*{checksum(RMC)}\n"
                    RC3out = f"${RC3}*{checksum(RC3)}\n"

                    result = GNGGA + GNRMC + RC3out
                    return result
    return ""


class BearingCalculator:
    def __init__(self):
        self.lat1 = "1"
        self.lon1 = "1"
        self.output = "0"

    def calculate_bearing(self, lat, lon):
        """
        計算從(self.lat1, self.lon1)點指向(lat2, lon2)點的航向角
        僅使用經緯度的小數部分

        參數:
        lat (str): 緯度的小數部分
        lon (str): 經度的小數部分

        返回:
        bearing (float): 航向角(0-360度)
        """
        # 轉為小數
        lat1_dec = "0." + str(self.lat1)
        lon1_dec = "0." + str(self.lon1)
        lat2_dec = "0." + str(lat)
        lon2_dec = "0." + str(lon)

        # 上一次的經緯度
        self.lat1 = lat
        self.lon1 = lon

        # 轉換為float
        lat1_min = float(lat1_dec)
        lon1_min = float(lon1_dec)
        lat2_min = float(lat2_dec)
        lon2_min = float(lon2_dec)

        # 計算差值
        dlat = lat2_min - lat1_min
        dlon = lon2_min - lon1_min

        # 計算方位角
        y = math.sin(dlon) * math.cos(lat2_min)
        x = math.cos(lat1_min) * math.sin(lat2_min) - math.sin(lat1_min) * math.cos(lat2_min) * math.cos(dlon)
        bearing = math.atan2(y, x)
        bearing_degrees = math.degrees(bearing)

        # 範圍0-360度
        bearing_degrees = (bearing_degrees + 360) % 360

        self.output = f"{bearing_degrees:.2f}"

        if bearing_degrees != 0:
            output = self.output
            return output
        else:
            return self.output


def checksum(cs):  # 計算NMEA0183校驗和
    checksum = 0
    for s in cs:
        checksum ^= ord(s)
    return '{:02X}'.format(checksum)


def get_variable_expr(func, var_name):
    """
    獲取函數中指定變量的賦值表達式

    Args:
        func (callable): 包含要獲取變量的函數
        var_name (str): 要獲取表達式的變量名

    Returns:
        str: 變量的賦值表達式字符串
    """
    # 獲取函數源代碼
    source = inspect.getsource(func)
    tree = ast.parse(source)

    # 遍歷抽象語法樹,找到指定變量的賦值語句
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            if isinstance(node.targets[0], ast.Name):
                name = node.targets[0].id
            elif isinstance(node.targets[0], ast.Attribute):
                # Handle attribute object
                name = node.targets[0].attr
            else:
                # Unsupported target type
                continue
            if name == var_name:
                # 獲取原始賦值表達式的字符串
                expr_str = source.split('\n')[node.value.lineno - 1].split('=', 1)[1].strip()
                return f"{name} = {expr_str}"

    raise ValueError(f"Variable '{var_name}' not found in function '{func.__name__}'")


if __name__ == '__main__':
    data = "f801c00e00000182000801043a2002581901d4f801c00e0000018200080202654e791802a6b7f801c00e00000182000803454100008000801ef801c00e0000018200080400800000002b00f8f801c00e00000182000805008000053a3a09a0f801c00e00000182000806fb6428000000001af801c00e000001820008070000001000000090f801c00e0000018200068800008500ff00009d"
    byte_data = bytes.fromhex(data)
    value = convert(byte_data)
    print(value)
    print(get_variable_expr(convert, 'RC3'))

    print(timeit.timeit('convert(byte_data)', globals=globals(), number=10000))
