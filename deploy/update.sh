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
git pull

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
