# Aracer x系列的wifi即時資訊轉racechhrono rc3的轉換程式
這是一個用於將aracer x系列的wifi即時資訊轉換為racechhrono rc3格式的程式。

## 文件結構
config.txt: 用於設定初始化ECU所需的IP、init、watchdog等數據。
main.py: 負責與ECU和Racechrono進行通訊。
decode.py: 負責將ECU送來的資訊做轉換，轉換後的數據填入Racechrono所接受的RC3協議。
TwistedProxyCalcTk.py: 提供一個GUI界面，用於測試ECU的數據對應的資訊。由於使用了tk做GUI，因此只能在win、mac平台上使用。
## 使用方式
編輯 config.txt 文件，設定初始化ECU所需的IP、init、watchdog等數據。
執行 main.py 以開始與ECU和Racechrono的通訊。
如果需要測試ECU的數據對應的資訊，可以執行 TwistedProxyCalcTk.py。
## 需求
Python
Twisted 套件
# 測試平台
這個程式已在Windows和Android (termux)上進行過測試。