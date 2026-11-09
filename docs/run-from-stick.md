# Run-from-stick kiosk (testing)

The whole kiosk runs from a USB stick. The PC's own drive is never used: its
drivers are not even loaded, so Windows (or the hard-drive kiosk) stays exactly
as it was. Every restart starts a fresh, clean system.

## Make a stick

1. Download `kiosk-os-live.img.xz` from the
   [live-latest release](https://github.com/regalstaffing/kiosk-os-2026/releases/tag/live-latest).
2. Write it to a USB stick (8 GB or larger; everything on the stick is erased)
   with [balenaEtcher](https://etcher.balena.io/) (it reads the .xz file directly) or Rufus.

## Start a PC from the stick

1. Plug the stick into a back port and turn the PC on.
2. Open the one-time boot menu (Dell: F12, HP: F9, Lenovo: F12) and pick the USB stick.
   To make it permanent, put USB first in the boot order in the BIOS settings.
3. **First start only:** set the admin password. It is saved on the stick (scrambled).
4. The kiosk starts. Wi-Fi: Ctrl+Alt+Shift+A > Wi-Fi (typed again after each restart).

Remove the stick and restart to get the PC's normal system back.

## What is saved on the stick

Only: the admin password (scrambled), the device ID, the group and its last
working settings. Browser data, logs and Wi-Fi passwords live in memory and are
gone after a restart.

## Updates

GitHub builds a new image when the software changes. Each kiosk checks daily,
downloads the new version to a spare slot on the stick, and starts it at the next
restart. If the new version fails to start, the next restart brings back the
previous one. The boot menu also has "Kiosk (previous version)".
On the admin console, `kiosk update` fetches the newest version and restarts now;
`kiosk check` shows the versions on the stick.

## USB sticks

Only the stick the kiosk started from is allowed. Any other USB stick is blocked.
