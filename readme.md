# 這是一個aracer x系列的wifi即時資訊轉racechhrono rc3的轉換程式

雖然有個用了一年多的舊版，能用

但實在太慘，有些小bug、還不夠clean code，趁這次重構弄得好點

## 適用平台
只要能跑python的平台都能用

僅在windows、android(termux)測試過

使用Twisted通訊，需安裝twisted套件

## 內容物
config.txt是讓你設定初始化ECU所需的IP、init、watchdog等數據

main.py是用來與ECU、Racechrono通訊實現用的

decode.py負責將ECU送來的資訊做轉換，轉換後的數據填入Racechrono所接受的RC3協議

TwistedProxyCalcTk.py是用來讓你測試ECU的數據對應的資訊為何
因為使用tk做GUI，可測試範圍只能給win、mac平台使用