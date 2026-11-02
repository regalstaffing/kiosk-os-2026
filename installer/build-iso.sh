#!/bin/sh
# Build the kiosk USB installer: the official Debian 13 netinst image with our
# preseed and boot menus added. Needs: curl, xorriso, sha256sum.
#   sh installer/build-iso.sh [output.iso]
set -e

HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${1:-kiosk-os-installer.iso}
BASE=https://cdimage.debian.org/debian-cd/current/amd64/iso-cd
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

curl -fsSL "$BASE/SHA256SUMS" -o "$WORK/SHA256SUMS"
ISO=$(grep -o 'debian-[0-9.]*-amd64-netinst\.iso' "$WORK/SHA256SUMS" | head -n 1)
[ -n "$ISO" ] || { echo "Could not find the netinst image name" >&2; exit 1; }

echo "==> Downloading $ISO"
curl -fL "$BASE/$ISO" -o "$WORK/$ISO"
(cd "$WORK" && grep " $ISO\$" SHA256SUMS | sha256sum -c -)

echo "==> Building $OUT"
rm -f "$OUT"
xorriso -indev "$WORK/$ISO" -outdev "$OUT" \
    -map "$HERE/preseed.cfg"   /preseed.cfg \
    -map "$HERE/isolinux.cfg"  /isolinux/isolinux.cfg \
    -map "$HERE/kiosk.msg"     /isolinux/kiosk.msg \
    -map "$HERE/grub.cfg"      /boot/grub/grub.cfg \
    -boot_image any replay

echo "==> Done: $OUT (based on $ISO)"
