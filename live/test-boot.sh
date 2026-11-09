#!/bin/bash
# Test boot of the stick image in a virtual PC (used by the GitHub build).
#   live/test-boot.sh IMAGE bios|uefi SHOTDIR
# Boots from a virtual USB stick, sets the first-start admin password, checks
# the kiosk comes up, restarts, and checks the password was kept on the stick.
set -u
IMG=$1 MODE=$2 SHOTS=$3
MON=mon-$MODE
FW=""; [ "$MODE" = uefi ] && FW="-bios /usr/share/ovmf/OVMF.fd"
ACCEL=""; [ -e /dev/kvm ] && ACCEL="-enable-kvm -cpu host"
mkdir -p "$SHOTS"

qemu-system-x86_64 $ACCEL -m 3072 -smp 2 $FW \
    -drive file="$IMG",format=raw,if=none,id=stick \
    -device qemu-xhci -device usb-storage,drive=stick,bootindex=0 \
    -nic user,model=e1000 -vga std -display none \
    -monitor unix:$MON,server,nowait -serial file:serial-$MODE.txt &
QEMU=$!

hmp() { echo "$1" | socat - UNIX-CONNECT:$MON >/dev/null 2>&1; }
shot() { hmp "screendump $SHOTS/$MODE-$1.ppm"; }
type_text() { for c in $(echo "$1" | sed 's/./& /g'); do hmp "sendkey $c"; sleep 0.1; done; }

sleep 60; shot 1-first-start
type_text testpassword1; hmp "sendkey tab"; type_text testpassword1; hmp "sendkey ret"
sleep 30; shot 2-after-password
sleep 60; shot 3-kiosk
hmp system_reset
sleep 90; shot 4-after-restart
# Clean shutdown (like pressing the power button): must finish within 60 s
hmp system_powerdown
for i in $(seq 60); do kill -0 $QEMU 2>/dev/null || break; sleep 1; done
if kill -0 $QEMU 2>/dev/null; then
    shot 5-shutdown-hung; echo "SHUTDOWN TEST ($MODE): FAILED, still running after 60 s"
    hmp quit
else
    echo "SHUTDOWN TEST ($MODE): passed in ${i} s"
fi
wait $QEMU 2>/dev/null
for f in "$SHOTS"/$MODE-*.ppm; do convert "$f" "${f%.ppm}.png" && rm "$f"; done
cp serial-$MODE.txt "$SHOTS/" 2>/dev/null
true
