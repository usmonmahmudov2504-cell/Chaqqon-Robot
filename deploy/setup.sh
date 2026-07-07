#!/bin/bash
set -e

sudo apt update
sudo apt install -y python3-venv python3-pip ffmpeg

mkdir -p ~/chaqqon-bot
cd ~/chaqqon-bot

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Endi .env faylini yarating: nano .env"
echo "Ichiga yozing: BOT_TOKEN=sizning_tokeningiz"
