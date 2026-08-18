#!/bin/bash
set -e

sudo apt update
# ffmpeg - video va audio oqimlarini birlashtirish uchun.
# nodejs - YouTube pleyerining JS challenge'ini yechish uchun (usiz
# YouTube formatlari topilmaydi).
sudo apt install -y python3-venv python3-pip ffmpeg nodejs

mkdir -p ~/chaqqon-bot
cd ~/chaqqon-bot

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Endi .env faylini yarating: nano .env"
echo "Ichiga yozing: BOT_TOKEN=sizning_tokeningiz"
