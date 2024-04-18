#!/bin/bash

# 嘗試連接google.com確認是否有網路
check_network()
{
    # 使用curl命令連接google.com
    curl -sSf http://www.google.com > /dev/null 2>&1

    # 檢查curl命令的返回值
    if [ $? -eq 0 ]; then
        echo "connected"
        check_python
    else
        echo "disconnected"
    fi
}


# 检查系统是否安装了Python
check_python()
{
    if command -v python3 &> /dev/null; then
        echo "Python installed"
        # 输出 Python 的版本信息
        python3 --version
    else
        echo "Python not installed"
        pkg install python -y
    fi
    check_Twisted
}

# 检查 Twisted 是否安装
check_Twisted()
{
    if python -c "import twisted" &> /dev/null; then
        echo "Twisted installed"
        # 输出 Twisted 的版本信息
        python3 -c "import twisted; print('Twisted 版本：', twisted.__version__)"
    else
        echo "Twisted not installed"
        echo "正在使用 pip 安装 Twisted..."
        python3 -m pip install twisted

    fi
    check_Aracer_TCPdecode2Racechrono
}

# 確認是否已經下載了Aracer_TCPdecode2Racechrono
check_Aracer_TCPdecode2Racechrono()
{
    if [ -d "Aracer_TCPdecode2Racechrono" ]; then
        echo "Aracer_TCPdecode2Racechrono downloaded"
        cd Aracer_TCPdecode2Racechrono
        git pull origin main
    else
        echo "Aracer_TCPdecode2Racechrono not downloaded"
        echo "正在下载 Aracer_TCPdecode2Racechrono..."
        git clone https://github.com/timliucode/Aracer_TCPdecode2Racechrono.git
    fi
}


check_network