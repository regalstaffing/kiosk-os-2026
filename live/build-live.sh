#!/bin/sh
# Build the run-from-stick image. Run as root on Debian/Ubuntu (GitHub Actions does this).
# Needs: mmdebstrap squashfs-tools dosfstools e2fsprogs grub-pc-bin grub2-common xz-utils fdisk
#   sh live/build-live.sh OUTDIR [KEYRING]
# Produces in OUTDIR:
#   kiosk-os-live.img.xz          write to a USB stick (balenaEtcher / Rufus)
#   vmlinuz initrd.img filesystem.squashfs version SHA256SUMS   update files for existing sticks
set -eux

REPO=$(cd "$(dirname "$0")/.." && pwd)
OUT=$(mkdir -p "$1" && cd "$1" && pwd)
KEYRING=${2:-}
WORK=$(mktemp -d)
ROOT=$WORK/rootfs
VERSION=$(date -u +%Y%m%d-%H%M)-$(git -C "$REPO" rev-parse --short HEAD)
# The release this stick updates itself from: live-latest, or live-test for a test build
CHANNEL=${KIOSK_CHANNEL:-live-latest}
case "$CHANNEL" in live-latest|live-test) ;; *) echo "KIOSK_CHANNEL must be live-latest or live-test" >&2; exit 1;; esac
IMG_MB=3600           # fits "4 GB" sticks; 8 GB or larger recommended

FIRMWARE=firmware-linux-free,firmware-misc-nonfree,firmware-iwlwifi,firmware-realtek,firmware-atheros,firmware-brcm80211,firmware-intel-graphics,firmware-amd-graphics,firmware-intel-sound
PKGS=linux-image-amd64,live-boot,systemd-sysv,dbus,ca-certificates,git,curl,grub-common,sudo,locales,console-setup,$FIRMWARE

case "$REPO$WORK" in *" "*) echo "paths must not contain spaces"; exit 1 ;; esac
mkdir -p "$WORK/debs"

# 1. Root file system with everything the hard-drive kiosk has (setup.sh in live mode)
mmdebstrap --mode=root --variant=important \
    --components="main contrib non-free-firmware" \
    ${KEYRING:+--keyring="$KEYRING"} \
    --include="$PKGS" \
    --customize-hook='mkdir -p "$1/opt/kiosk-os"' \
    --customize-hook="sync-in $REPO /opt/kiosk-os" \
    --customize-hook="chroot \"\$1\" env KIOSK_LIVE=1 DEBIAN_FRONTEND=noninteractive sh /opt/kiosk-os/scripts/setup.sh" \
    --customize-hook="echo '$VERSION' > \"\$1/etc/kiosk/version\"" \
    --customize-hook="echo '$CHANNEL' > \"\$1/etc/kiosk/channel\"" \
    --customize-hook='chroot "$1" sh -c "mkdir -p /root/debs && cd /root/debs && apt-get download shim-signed grub-efi-amd64-signed"' \
    --customize-hook="sync-out /root/debs $WORK/debs" \
    --customize-hook='rm -rf "$1/root/debs"; : > "$1/etc/machine-id"' \
    trixie "$ROOT" http://deb.debian.org/debian

# 2. Boot files and the compressed read-only system
SYS=$WORK/sys; mkdir -p "$SYS"
cp "$(ls "$ROOT"/boot/vmlinuz-* | sort -V | tail -1)" "$SYS/vmlinuz"
cp "$(ls "$ROOT"/boot/initrd.img-* | sort -V | tail -1)" "$SYS/initrd.img"
echo "$VERSION" > "$SYS/version"
mksquashfs "$ROOT" "$SYS/filesystem.squashfs" -comp xz -noappend -e boot
(cd "$SYS" && sha256sum version vmlinuz initrd.img filesystem.squashfs > SHA256SUMS)

# 3. Signed UEFI boot loader (works with Secure Boot)
for d in "$WORK"/debs/*.deb; do dpkg-deb -x "$d" "$WORK/efi-pkgs"; done
SHIM=$(find "$WORK/efi-pkgs" -name 'shimx64.efi.signed' | head -1)
GRUBEFI=$(find "$WORK/efi-pkgs" -name 'grubx64.efi.signed' | head -1)
MM=$(find "$WORK/efi-pkgs" -name 'mmx64.efi.signed' | head -1 || true)

# 4. Disk image: [1] KIOSKEFI (FAT, boot loaders + boot settings)  [2] KIOSKDATA (ext4, system slots + saved settings)
IMG=$WORK/kiosk-os-live.img
truncate -s ${IMG_MB}M "$IMG"
sfdisk "$IMG" <<EOT
label: dos
start=2048, size=512000, type=ef, bootable
start=514048, type=83
EOT
LOOP=$(losetup -fP --show "$IMG")
trap 'umount "$WORK/esp" "$WORK/data" 2>/dev/null; losetup -d "$LOOP" 2>/dev/null' EXIT
mkfs.vfat -F 32 -n KIOSKEFI "${LOOP}p1"
mkfs.ext4 -q -L KIOSKDATA -m 0 "${LOOP}p2"
mkdir -p "$WORK/esp" "$WORK/data"
mount "${LOOP}p1" "$WORK/esp"
mount "${LOOP}p2" "$WORK/data"

mkdir -p "$WORK/data/live/A" "$WORK/data/kiosk-data"
cp "$SYS"/* "$WORK/data/live/A/"

mkdir -p "$WORK/esp/EFI/BOOT" "$WORK/esp/EFI/debian" "$WORK/esp/boot/grub" "$WORK/esp/kiosk"
cp "$SHIM" "$WORK/esp/EFI/BOOT/BOOTX64.EFI"
cp "$GRUBEFI" "$WORK/esp/EFI/BOOT/grubx64.efi"
[ -n "$MM" ] && cp "$MM" "$WORK/esp/EFI/BOOT/mmx64.efi"
for d in EFI/BOOT EFI/debian boot/grub; do cp "$REPO/live/grub.cfg" "$WORK/esp/$d/grub.cfg"; done
grub-editenv "$WORK/esp/kiosk/grubenv" create
grub-editenv "$WORK/esp/kiosk/grubenv" set default_slot=A
# BIOS boot loader (older PCs)
grub-install --target=i386-pc --boot-directory="$WORK/esp/boot" --modules="part_msdos fat ext2 search loadenv" "$LOOP"

sync
umount "$WORK/esp" "$WORK/data"
losetup -d "$LOOP"
trap - EXIT

# 5. Outputs
xz -T0 -6 -c "$IMG" > "$OUT/kiosk-os-live.img.xz"
cp "$SYS"/* "$OUT/"
(cd "$OUT" && sha256sum kiosk-os-live.img.xz > kiosk-os-live.img.xz.sha256)
ls -la "$OUT"
