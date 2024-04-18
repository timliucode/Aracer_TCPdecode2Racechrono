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
        check_Twisted
    else
        echo "Python not installed"
        pkg install python -y
    fi
}

# 检查 Twisted 是否安装
check_Twisted()
{
    if python -c "import twisted" &> /dev/null; then
        echo "Twisted installed"
        # 输出 Twisted 的版本信息
        python -c "import twisted; print('Twisted 版本：', twisted.__version__)"
    else
        echo "Twisted not installed"

    fi
}

check_network