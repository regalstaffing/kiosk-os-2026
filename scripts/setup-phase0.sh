#!/bin/sh
# Phase 0 kiosk setup. Run as root from the cloned repository:
#   sh /opt/kiosk-os/scripts/setup-phase0.sh
# Safe to run more than once.
set -e

REPO=$(cd "$(dirname "$0")/.." && pwd)

echo "==> Installing packages"
apt-get update
# fonts-noto-core is small; the full fonts-noto set pulls in ~1 GB of CJK fonts
apt-get install -y cage chromium fonts-noto-core

echo "==> Enabling wired network on every Ethernet port"
# The Debian installer configures only the interface used during install
# (sometimes Wi-Fi), leaving Ethernet unmanaged.
WIRED=/etc/network/interfaces.d/kiosk-wired
: > "$WIRED"
for dev in /sys/class/net/*; do
    name=$(basename "$dev")
    [ "$name" = lo ] && continue
    [ -e "$dev/device" ] || continue      # skip virtual interfaces
    [ -e "$dev/wireless" ] && continue    # skip Wi-Fi
    grep -qs "iface $name " /etc/network/interfaces && continue
    printf 'allow-hotplug %s\niface %s inet dhcp\n\n' "$name" "$name" >> "$WIRED"
    echo "    $name"
done

echo "==> Creating the kiosk user"
if id kiosk >/dev/null 2>&1; then
    usermod --shell /usr/sbin/nologin kiosk
else
    useradd --create-home --shell /usr/sbin/nologin kiosk
fi

echo "==> Installing browser policy and system config"
install -D -m 644 "$REPO/policies/kiosk.json"          /etc/chromium/policies/managed/kiosk.json
install -D -m 644 "$REPO/system/logind-kiosk.conf"     /etc/systemd/logind.conf.d/kiosk.conf
install -D -m 644 "$REPO/system/sysctl-kiosk.conf"     /etc/sysctl.d/90-kiosk.conf
install -D -m 644 "$REPO/system/modprobe-kiosk.conf"   /etc/modprobe.d/kiosk.conf
install -D -m 644 "$REPO/system/kiosk.service"         /etc/systemd/system/kiosk.service

systemctl daemon-reload
systemctl set-default graphical.target
systemctl enable kiosk.service

echo
echo "Done. Type 'reboot' and press Enter to start the kiosk."
