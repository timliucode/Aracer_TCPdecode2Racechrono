#!/bin/bash
pkg install git -y
pkg install python -y
python3 -m pip install twisted
git clone https://github.com/timliucode/Aracer_TCPdecode2Racechrono.git
cd Aracer_TCPdecode2Racechrono
python3 main.py
