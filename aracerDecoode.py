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


def convert(data):
    buffer = b""  # 用於存放不完整的數據
    buffer += data  # 將收到的數據添加到 buffer 中
    while len(buffer) >= length:  # 如果 buffer 中的數據大於等於一條數據的長度
        message = buffer[:length]  # 獲取一條數據
        buffer = buffer[length:]  # 從 buffer 中刪除這條數據
        if message[6:8] == bytes.fromhex(ID):  # 如果這條數據的ID是我們需要的
            mv = memoryview(message)

