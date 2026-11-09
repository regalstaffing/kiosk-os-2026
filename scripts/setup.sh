#!/bin/sh
# Kiosk setup. Run as root from the cloned repository:
#   sh /opt/kiosk-os/scripts/setup.sh
# Also run by the USB installer at the end of installation.
# Safe to run more than once.
set -e

REPO=$(cd "$(dirname "$0")/.." && pwd)
# KIOSK_LIVE=1: building the run-from-stick image (live/build-live.sh), in a chroot.
LIVE=${KIOSK_LIVE:-0}

echo "==> Installing packages"
apt-get update
# fonts-noto-core is small; the full fonts-noto set pulls in ~1 GB of CJK fonts
# --install-recommends: the run-from-stick build turns recommended packages off
# by default, but Wi-Fi needs them (wpasupplicant, wireless-regdb)
apt-get install -y --install-recommends cage chromium fonts-noto-core fontconfig python3 kbd git \
    python3-gi gir1.2-gtk-3.0 network-manager wpasupplicant plymouth plymouth-themes unattended-upgrades
if [ "$LIVE" = 1 ]; then apt-get install -y live-boot curl grub-common; fi

echo "==> Handing networking to NetworkManager"
# NetworkManager connects any wired port automatically and lets the admin
# screen join Wi-Fi. It ignores interfaces listed in /etc/network/interfaces,
# so reduce that file to loopback only (original kept as .before-kiosk).
[ -e /etc/network/interfaces.before-kiosk ] || cp /etc/network/interfaces /etc/network/interfaces.before-kiosk
printf 'source /etc/network/interfaces.d/*\n\nauto lo\niface lo inet loopback\n' > /etc/network/interfaces
rm -f /etc/network/interfaces.d/kiosk-wired
systemctl enable NetworkManager.service

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
if [ "$LIVE" = 1 ]; then
    # The system itself runs from a USB stick: other sticks are blocked by
    # kiosk-live instead of switching off USB storage altogether.
    rm -f /etc/modprobe.d/kiosk.conf
else
    install -D -m 644 "$REPO/system/modprobe-kiosk.conf" /etc/modprobe.d/kiosk.conf
fi
install -D -m 644 "$REPO/system/kiosk.service"         /etc/systemd/system/kiosk.service
[ "$LIVE" = 1 ] || install -D -m 644 "$REPO/system/grub-kiosk.cfg" /etc/default/grub.d/kiosk.cfg
install -D -m 644 "$REPO/system/kiosk-sessiond.service" /etc/systemd/system/kiosk-sessiond.service
install -D -m 755 "$REPO/agent/kiosk-sessiond"         /usr/local/sbin/kiosk-sessiond
install -D -m 755 "$REPO/agent/kiosk"                  /usr/local/sbin/kiosk
install -D -m 755 "$REPO/agent/kiosk-admin-ui"         /usr/local/sbin/kiosk-admin-ui
install -D -m 755 "$REPO/agent/kiosk-config"          /usr/local/sbin/kiosk-config
install -D -m 644 "$REPO/system/kiosk-config.service"  /etc/systemd/system/kiosk-config.service
install -D -m 644 "$REPO/system/kiosk-config.timer"    /etc/systemd/system/kiosk-config.timer
install -D -m 755 "$REPO/agent/kiosk-autoupdate"       /usr/local/sbin/kiosk-autoupdate
install -D -m 644 "$REPO/system/kiosk-update.service"  /etc/systemd/system/kiosk-update.service
install -D -m 755 "$REPO/agent/kiosk-browser"          /usr/local/bin/kiosk-browser
install -D -m 755 "$REPO/agent/kiosk-splash"           /usr/local/bin/kiosk-splash
install -D -m 644 "$REPO/system/kiosk-admin.service"   /etc/systemd/system/kiosk-admin.service
install -D -m 644 "$REPO/system/profile-timeout.sh"    /etc/profile.d/kiosk-timeout.sh
install -D -m 644 "$REPO/system/motd"                  /etc/motd
install -D -m 644 "$REPO/system/apt-auto-upgrades"     /etc/apt/apt.conf.d/20auto-upgrades
install -D -m 644 "$REPO/system/hwdb-kiosk.hwdb"       /etc/udev/hwdb.d/90-kiosk.hwdb
systemd-hwdb update
# Keep logs across reboots for troubleshooting
mkdir -p /var/log/journal
udevadm trigger --subsystem-match=input --action=change 2>/dev/null || true
# Keep local settings once created, so admins can edit them
mkdir -p /etc/kiosk
echo "$REPO" > /etc/kiosk/repo
[ -e /etc/kiosk/settings ] || install -D -m 644 "$REPO/system/settings" /etc/kiosk/settings
# Which group settings file (groups/<GROUP>.toml) and branch this kiosk follows.
# Kept once created; change it with "kiosk group".
[ -e /etc/kiosk/group ] || printf 'GROUP=default\nBRANCH=main\n' > /etc/kiosk/group

echo "==> Applying group settings"
/usr/local/sbin/kiosk-config apply || echo "Group settings not applied; using the built-in defaults"

echo "==> Installing branding and boot splash"
THEME=/usr/share/plymouth/themes/kiosk
if [ -f "$REPO/branding/logo.png" ]; then
    install -D -m 644 "$REPO/branding/logo.png" /usr/share/kiosk/logo.png
    rm -rf "$THEME"
    cp -r /usr/share/plymouth/themes/spinner "$THEME"
    mv "$THEME/spinner.plymouth" "$THEME/kiosk.plymouth"
    sed -i -e 's/^Name=.*/Name=Kiosk/' \
        -e 's/^BackgroundStartColor=.*/BackgroundStartColor=0xf4f5f7/' \
        -e 's/^BackgroundEndColor=.*/BackgroundEndColor=0xf4f5f7/' \
        -e 's|/spinner$|/kiosk|' "$THEME/kiosk.plymouth"
    cp "$REPO/branding/logo.png" "$THEME/watermark.png"
    plymouth-set-default-theme kiosk
else
    rm -f /usr/share/kiosk/logo.png
    plymouth-set-default-theme spinner
fi

if [ "$LIVE" = 1 ]; then
    echo "==> Run-from-stick services"
    install -D -m 755 "$REPO/agent/kiosk-live"                   /usr/local/sbin/kiosk-live
    install -D -m 644 "$REPO/system/live/kiosk-live-boot.service" /etc/systemd/system/kiosk-live-boot.service
    install -D -m 644 "$REPO/system/live/kiosk-setpw.service"     /etc/systemd/system/kiosk-setpw.service
    install -D -m 644 "$REPO/system/live/kiosk-live-update.service" /etc/systemd/system/kiosk-live-update.service
    install -D -m 644 "$REPO/system/live/kiosk-live-update.timer" /etc/systemd/system/kiosk-live-update.timer
    install -D -m 644 "$REPO/system/live/kiosk-debug-serial.service" /etc/systemd/system/kiosk-debug-serial.service
    install -D -m 644 "$REPO/system/live/90-kiosk-usb-guard.rules" /etc/udev/rules.d/90-kiosk-usb-guard.rules
    echo kiosk > /etc/hostname
    # Logs stay in memory only (nothing written to the stick or the PC)
    rm -rf /var/log/journal
    mkdir -p /etc/systemd/journald.conf.d
    printf '[Journal]\nStorage=volatile\nRuntimeMaxUse=50M\n' > /etc/systemd/journald.conf.d/kiosk-live.conf
    : > /etc/fstab
    # The repository copy is checked by git as root
    chown -R root:root "$REPO"
    # Never hang long when restarting or shutting down
    mkdir -p /etc/systemd/system.conf.d
    printf '[Manager]\nDefaultTimeoutStopSec=10s\n' > /etc/systemd/system.conf.d/kiosk-live.conf
    # Updates come as whole new system images, not package upgrades
    systemctl mask apt-daily.timer apt-daily-upgrade.timer
    echo "==> Building the boot files"
    update-initramfs -u -k all
    systemctl set-default graphical.target
    systemctl enable kiosk.service kiosk-sessiond.service kiosk-config.timer \
        kiosk-live-boot.service kiosk-setpw.service kiosk-live-update.timer kiosk-debug-serial.service
    echo "Done (run-from-stick image)."
    exit 0
fi

echo "==> Applying USB storage block and splash to the boot files"
update-initramfs -u
update-grub

systemctl daemon-reload
systemctl set-default graphical.target
systemctl enable kiosk.service kiosk-sessiond.service kiosk-update.service kiosk-config.timer

echo
echo "Done. Type 'reboot' and press Enter to start the kiosk."
