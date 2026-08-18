#!/bin/bash
# Serverda yangilanishni bir buyruq bilan bajaradi:
#   cd ~/chaqqon-bot && bash deploy/update.sh
set -e

cd "$(dirname "$0")/.."
echo "== Papka: $(pwd)"

echo "== Tizim paketlari (ffmpeg + nodejs)"
sudo apt update -qq
# ffmpeg - video va audio oqimlarini birlashtirish uchun.
# nodejs - YouTube pleyerining JS challenge'ini yechish uchun.
sudo apt install -y ffmpeg nodejs

echo "== Yangi kod"
if [ -d .git ]; then
    git pull
else
    echo "  XATO: bu papka git repozitoriysi emas."
    echo "  Quyidagini bajaring:"
    echo "    cd ~ && mv chaqqon-bot chaqqon-bot-eski"
    echo "    git clone https://github.com/usmonmahmudov2504-cell/Chaqqon-Robot.git chaqqon-bot"
    echo "    cp chaqqon-bot-eski/.env chaqqon-bot/"
    echo "    cp chaqqon-bot-eski/cookies.txt chaqqon-bot/ 2>/dev/null"
    echo "    cd chaqqon-bot && python3 -m venv venv"
    echo "    source venv/bin/activate && pip install -r requirements.txt"
    echo "    bash deploy/update.sh"
    exit 1
fi

echo "== yt-dlp yangilanishi"
source venv/bin/activate
pip install -q --upgrade yt-dlp

echo "== Tekshiruv"
command -v ffmpeg >/dev/null && echo "  ffmpeg: OK" || echo "  ffmpeg: TOPILMADI"
command -v node   >/dev/null && echo "  node:   OK" || echo "  node:   TOPILMADI"
[ -f cookies.txt ] && echo "  cookies.txt: OK" || echo "  cookies.txt: TOPILMADI - kompyuteringizdan scp bilan yuboring"

echo "== Botni qayta ishga tushirish"
sudo systemctl restart chaqqon-bot
sleep 2
sudo systemctl status chaqqon-bot --no-pager -n 10

echo
echo "Tayyor. Telegram'da botga /diag yuboring."
