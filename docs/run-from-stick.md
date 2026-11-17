# Run-from-stick kiosk

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
working settings, the kiosk manager key and the settings it last sent, and the
device settings (sound, microphone, camera, brightness) as plain values. The full
list is `SAVED` in `agent/kiosk-live`. Browser data, logs and Wi-Fi passwords live
in memory and are gone after a restart.

Device settings are saved as checked values in `devices.json`, never as config
files (config files can run programs). At start-up `kiosk-devices.service` checks
them and writes the sound and camera config itself; a value that doesn't check out
is ignored, and an unreadable camera choice turns the camera off.

## Device settings

Admin menu (Ctrl+Alt+Shift+A) > **Device settings**: pick the speakers and the
microphone, set the volume, turn the camera on or off, and set the screen
brightness. Changes are used right away and kept after a restart.

## Looping videos

`http://127.0.0.1:8099/loop?v=VIDEO&start=S&end=E` is the kiosk's own looping
video page (served by `kiosk-sessiond`): YouTube's player with full screen allowed,
looping from S to E seconds inside one play, so an ad plays at most once. VIDEO is
the 11 characters after `v=` in a YouTube link. Set it as a home page in the Kiosk
Manager with *Add looping video*. Looper websites can't go full screen on the kiosk.

## Updates

GitHub builds a new image when the software changes. Each kiosk checks daily,
downloads the new version to a spare slot on the stick, and starts it at the next
restart. If the new version fails to start, the next restart brings back the
previous one. The boot menu also has "Kiosk (previous version)".
On the admin console, `kiosk update` fetches the newest version and restarts now;
`kiosk check` shows the versions on the stick.

**Test builds.** A build from any branch other than `usb-live` is published as the
`live-test` release, with an image named `kiosk-os-TEST-<branch>-<version>.img.xz`.
A stick made from it updates only from `live-test`, never from `live-latest`.
Re-make it from `kiosk-os-live.img.xz` when testing is over.

## USB sticks

Only the stick the kiosk started from is allowed. Any other USB stick is blocked.

## Kiosk manager

Once each time it starts up, the kiosk checks in with the kiosk manager at kiosks.regalstaffing.com. (If the network isn't up yet, for example because the Wi-Fi password still has to be typed in, it tries again every 5 minutes until the manager answers.) It sends who it is: its PC ID, model, software and browser versions, and stick ID. In return it gets its group's settings.

- **A new kiosk** shows up in the manager as *New* and keeps the default settings. A manager approves it by saving it on its page or by moving it into a group. Only approved kiosks receive the admin password, and they get it only in its scrambled form.
- **Its key.** The first time a kiosk checks in, it makes its own random key (`/etc/kiosk/manager.key`). The key is kept on the stick, and the manager won't accept that PC with any other key. If a stick is replaced or re-made, use *Forget device* in the manager so the PC can register again.
- **When the manager can't be reached.** A kiosk that has had settings from the manager keeps using the last ones it received. A kiosk that has never reached the manager follows its group file on GitHub, as before.
- **Getting changes.** Changes made in the manager reach a kiosk the next time it starts up. To get them right away, open the admin menu (Ctrl+Alt+Shift+A) and press *Check for settings now*. Kiosks check in only at start-up to keep the manager's database use low.
- **Troubleshooting.** `kiosk check` shows the last check-in. `sudo kiosk-checkin` checks in right away.
