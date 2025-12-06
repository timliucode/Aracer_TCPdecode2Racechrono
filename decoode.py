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

"""
to do:
vss、afr修正
減少無謂的格式轉換
"""
import time
import timeit
import ast
import datetime
import inspect
import math

ID = '0182'  # CAN ID (這是monitor的ID)
length = 19  # 1個CAN包加上前綴及checksum的長度

# 暫時性的，趕著比賽可用
# rear Tire setting
width = 120      # 輪胎寬度(mm)
aspect_ratio = 80  # 輪胎側比(%)
rim_diameter = 12  # 輪圈直徑(inch)
# 計算輪胎圓周長(cm)
tire_circumference = ((width * aspect_ratio * 2 / 1000) + (rim_diameter * 2.54)) * math.pi / 100
# 齒比
font_gear_in = 12
font_gear_out = 39
rear_gear_in = 13
rear_gear_out = 40
gear_ratio = (font_gear_out / font_gear_in) * (rear_gear_out / rear_gear_in)


# ===== 工具函式 =====
def nmea_to_decimal(nmea_str: str, is_lat: bool) -> float:
    """
    將 NMEA 格式的 DDMM.mmmm / DDDMM.mmmm 轉為十進位度數
    is_lat=True 表示緯度(通常 2 位數度)，False 表示經度(3 位數度)
    """
    if not nmea_str:
        return 0.0

    val = float(nmea_str)
    # 緯度/經度都可以用 //100 切出度數部分
    deg = int(val // 100)
    minutes = val - deg * 100
    return deg + minutes / 60.0


def checksum(cs):  # 計算NMEA0183校驗和
    checksum_val = 0
    for s in cs:
        checksum_val ^= ord(s)
    return '{:02X}'.format(checksum_val)


# ===== 航向計算 + EMA =====
class BearingCalculator:
    def __init__(self, speed_threshold_knots: float = 1.0, ema_alpha: float = 0.3):
        # 前一筆位置 (decimal degrees)
        self.prev_lat = None
        self.prev_lon = None

        # 上一次輸出的(平滑後)航向字串
        self.last_output = "0.00"

        # EMA 相關
        self.speed_threshold_knots = speed_threshold_knots
        self.ema_alpha = ema_alpha
        self.ema_value = None  # float, degrees

    def update(self, nmea_lat: str, lat_ns: str,
               nmea_lon: str, lon_ew: str,
               speed_knots: float | None) -> str:
        """
        使用上一點與這一點的位置計算 COG，並做 EMA 平滑
        nmea_lat, nmea_lon: NMEA 'DDMM.mmmm' / 'DDDMM.mmmm'
        lat_ns: 'N' 或 'S'
        lon_ew: 'E' 或 'W'
        speed_knots: 當下速度(節)，低於門檻不更新航向
        """
        # 速度太低時不更新航向，避免靜止時 GPS 抖動亂跳
        if speed_knots is not None and speed_knots < self.speed_threshold_knots:
            return self.last_output

        if not nmea_lat or not nmea_lon:
            return self.last_output

        # NMEA -> decimal degrees
        lat_deg = nmea_to_decimal(nmea_lat, is_lat=True)
        lon_deg = nmea_to_decimal(nmea_lon, is_lat=False)

        # 南半球 / 西經轉成負值
        if lat_ns == 'S':
            lat_deg = -lat_deg
        if lon_ew == 'W':
            lon_deg = -lon_deg

        # 第一次沒有前一筆資料：只記錄，不更新方向
        if self.prev_lat is None or self.prev_lon is None:
            self.prev_lat = lat_deg
            self.prev_lon = lon_deg
            return self.last_output

        # 換成弧度
        lat1 = math.radians(self.prev_lat)
        lon1 = math.radians(self.prev_lon)
        lat2 = math.radians(lat_deg)
        lon2 = math.radians(lon_deg)

        dlon = lon2 - lon1

        # 方位角公式
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        bearing = math.atan2(y, x)
        bearing_deg = (math.degrees(bearing) + 360.0) % 360.0

        # 記下這次位置，給下一筆用
        self.prev_lat = lat_deg
        self.prev_lon = lon_deg

        # EMA 平滑
        if self.ema_value is None:
            self.ema_value = bearing_deg
        else:
            alpha = self.ema_alpha
            self.ema_value = alpha * bearing_deg + (1.0 - alpha) * self.ema_value

        self.last_output = f"{self.ema_value:.2f}"
        return self.last_output


# ===== 加速度計算 =====
class acceleration:
    def __init__(self):
        self.time = time.time()
        self.speed = 0.0

    def calculate(self, speed: float) -> str:
        current_time = time.time()
        dt = current_time - self.time
        speed_diff = speed - self.speed
        self.speed = speed
        self.time = current_time

        if dt == 0:
            return "0.000"
        acceleration_val = speed_diff / dt
        return f"{acceleration_val:.3f}"


def get_variable_expr(func, var_name):
    """
    獲取函數中指定變量的賦值表達式
    """
    source = inspect.getsource(func)
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]

            if isinstance(target, ast.Name):
                name = target.id
            elif isinstance(target, ast.Attribute):
                name = target.attr
            else:
                continue

            if name == var_name:
                # 這裡用 ast.unparse 把右邊的表達式還原成程式碼字串
                try:
                    expr_code = ast.unparse(node.value)
                except AttributeError:
                    # 舊版 Python 沒有 ast.unparse，就退而求其次簡單抓一行
                    import textwrap
                    lines = textwrap.dedent(source).splitlines()
                    line = node.value.lineno - 1
                    expr_code = lines[line].split('=', 1)[-1].strip()

                return f"{name} = {expr_code}"

    raise ValueError(f"Variable '{var_name}' not found in function '{func.__name__}'")


def convert(data: bytes) -> str:
    # 計數
    if not hasattr(convert, 'count'):
        convert.count = 0
    convert.count += 1
    if convert.count > 65535:
        convert.count = 0

    # 初始化持久物件（只會第一次設定）
    if not hasattr(convert, 'bearing_calc'):
        convert.bearing_calc = BearingCalculator(speed_threshold_knots=1.0, ema_alpha=0.3)
    if not hasattr(convert, 'speed_acc'):
        convert.speed_acc = acceleration()
    if not hasattr(convert, 'rpm_acc'):
        convert.rpm_acc = acceleration()
    if not hasattr(convert, 'rr_acc'):
        convert.rr_acc = acceleration()

    # ---------- 預設值，避免未定義變數，也方便判斷是否有 GPS ----------
    gps_utc_hh = ""
    gps_utc_mm = ""
    gps_utc_ss = ""
    gps_utc_ms = ""

    gps_lat_deg = ""
    gps_lat_min = ""
    gps_lat_sec = ""
    gps_lat_ns = "N"

    gps_lon_deg = ""
    gps_lon_min = ""
    gps_lon_sec = ""
    gps_lon_ew = "E"

    gps_valid = "V"
    gps_speed = "0"

    rpm = 0
    tps = 0
    vss1 = 0
    vss2 = 0
    tc_lean_angle = 0
    tc_vss_fr_rate = 0
    volt_batt = 0
    t_eng = 0
    t_air = 0
    afr_wbo2_1 = 0
    afr_wbo2_2 = 0
    cyl1_eng_ap = 0
    cyl1_eng_ap_decimal = 0
    racelanuh_en = 0

    # 這一輪有沒有收齊 GPS 三段資料（index 1/2/3）
    gps_got_data = False

    buffer = b""
    buffer += data
    results = []  # 累積所有輸出，避免提前 return 導致後續 case 不執行

    while len(buffer) >= length:
        message = buffer[:length]
        buffer = buffer[length:]

        if message[6:8] == bytes.fromhex(ID):
            idx = message[10]

            match idx:
                case 1:  # GPS 時間 + 緯度前半
                    gps_utc_hh = f"{message[11]:02d}"
                    gps_utc_mm = f"{message[12]:02d}"
                    gps_utc_ss = f"{message[13]:02d}"
                    gps_utc_ms = f"{int.from_bytes(message[14:16], byteorder='big'):03d}"
                    gps_lat_deg = f"{message[16]:02d}"
                    gps_lat_min = f"{message[17]:02d}"

                case 2:  # 緯度後半 + 經度前半
                    gps_lat_sec = f"{int.from_bytes(message[11:13], byteorder='big'):04d}"
                    gps_lat_ns = chr(message[13])
                    gps_lon_deg = f"{message[14]:02d}"
                    gps_lon_min = f"{message[15]:02d}"
                    gps_lon_sec = f"{int.from_bytes(message[16:18], byteorder='big'):04d}"

                case 3:  # 經度後半 + valid + 速度
                    gps_lon_ew = chr(message[11])
                    gps_valid = chr(message[12])
                    gps_speed = f"{int.from_bytes(message[13:15], byteorder='big') * 0.539956803:.3f}"
                    gps_got_data = True

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
                    tc_status = message[15]  # 目前沒用到

                case _:
                    # 其它 index（例如 7）結束一組數據
                    pass

            # ★ 在非 1/2/3 的 index（例如 4/5/6/7…）時組輸出
            if idx not in (1, 2, 3):
                has_gps = (
                    gps_got_data and
                    gps_utc_hh != "" and
                    gps_lat_deg != "" and
                    gps_lon_deg != "" and
                    gps_valid == "A"
                )

                if has_gps:
                    quality = 1
                    nmea_time = f"{gps_utc_hh}{gps_utc_mm}{gps_utc_ss}.{gps_utc_ms}"
                    date = datetime.datetime.now(datetime.UTC).strftime('%d%m%y')

                    gps_lat = f"{gps_lat_deg}{gps_lat_min}.{gps_lat_sec}"
                    gps_lon = f"{gps_lon_deg}{gps_lon_min}.{gps_lon_sec}"

                    try:
                        gps_speed_f = float(gps_speed)
                    except Exception:
                        gps_speed_f = 0.0

                    # 使用持久化的 BearingCalculator + EMA
                    bearing = convert.bearing_calc.update(
                        gps_lat, gps_lat_ns,
                        gps_lon, gps_lon_ew,
                        gps_speed_f
                    )
                else:
                    quality = 0
                    nmea_time = ""
                    date = ""
                    gps_lat = ""
                    gps_lon = ""
                    gps_speed_f = 0.0
                    bearing = "0.00"

                # ---- 速度、轉速相關計算 ----
                # speed_acc：knot -> m/s 再算加速度
                ms2 = convert.speed_acc.calculate(gps_speed_f * 0.514444444)

                try:
                    rpm_i = int(rpm)
                except Exception:
                    rpm_i = 0

                # RPM -> rps 再算加速度
                rps2 = convert.rpm_acc.calculate(rpm_i / 60 if rpm_i else 0.0)

                # 齒比 / 減速比
                try:
                    denom = (gps_speed_f * 30.8666667) / tire_circumference
                    if denom == 0:
                        Reduction_Ratio = "0.000"
                    else:
                        Reduction_Ratio = f"{rpm_i / denom:.3f}"
                except Exception:
                    Reduction_Ratio = "0.000"

                try:
                    irrs2 = convert.rr_acc.calculate(float(Reduction_Ratio))
                except Exception:
                    irrs2 = "0.000"

                try:
                    alpha_ratio = f"{float(Reduction_Ratio) / gear_ratio:.3f}"
                except Exception:
                    alpha_ratio = "0.000"

                result = ""

                if has_gps:
                    # $GNGGA
                    GGA = (
                        f"GNGGA,{nmea_time},{gps_lat},{gps_lat_ns},"
                        f"{gps_lon},{gps_lon_ew},{quality},,,,M,,M,,"
                    )
                    # $GNRMC
                    RMC = (
                        f"GNRMC,{nmea_time},{gps_valid},"
                        f"{gps_lat_deg}{gps_lat_min}.{gps_lat_sec},{gps_lat_ns},"
                        f"{gps_lon_deg}{gps_lon_min}.{gps_lon_sec},{gps_lon_ew},"
                        f"{gps_speed},{bearing},{date},,,A"
                    )
                    result += f"${GGA}*{checksum(GGA)}\n"
                    result += f"${RMC}*{checksum(RMC)}\n"

                # ---- 組 RC3 sentence ----
                RC3 = (
                    f"RC3,{nmea_time},{convert.count},,,,,,,"
                    f"{rpm},{tps},{vss1},{vss2},{tc_lean_angle},{tc_vss_fr_rate},"
                    f"{volt_batt},{t_eng},{t_air},{afr_wbo2_1},{afr_wbo2_2},"
                    f"{cyl1_eng_ap},{cyl1_eng_ap_decimal},{racelanuh_en},"
                    f"{Reduction_Ratio},{alpha_ratio},{irrs2},{ms2},{rps2}"
                )
                result += f"${RC3}*{checksum(RC3)}\n"

                # 不要提前回傳，累積後續訊息
                results.append(result)

    # 只回傳最後一筆結果；若沒有則回傳空字串
    return results[-1] if results else ""


if __name__ == '__main__':
    data = "f801c00e0000018200080103252402581706e3f801c00e0000018200080209854e780d0e1026f801c00e0000018200080345410020753371e5f801c00e00000182000804fa6d7f2bbaff27b2f801c00e00000182000805ff64008d704309f6f801c00e00000182000806fb5b2c09290b1cc6f801c00e00000182000807000000100000038df801c00e000001820006887e538300ff0000ce"
    byte_data = bytes.fromhex(data)
    value = convert(byte_data)
    print(value)
    print(get_variable_expr(convert, 'RC3'))

    print(timeit.timeit('convert(byte_data)', globals=globals(), number=10000))
