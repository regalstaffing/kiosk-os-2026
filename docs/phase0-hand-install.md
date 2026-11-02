# Phase 0: hand-install a test kiosk

Goal: on one or two retired 64-bit PCs, confirm that our real sites load, everything else is
blocked, and the screen shows nothing but the browser. This is a manual setup; Phase 1 automates it.

You need: a USB stick (1 GB+), the PC (wired network recommended), and about 30 minutes.

## 1. Install Debian 13

1. Download the Debian 13 "netinst" amd64 image from https://www.debian.org/distrib/netinst and write it to the USB stick (Rufus or balenaEtcher).
2. Boot the PC from the stick (boot menu key is usually F12, F9 or Esc) and choose **Install** or **Graphical install**.
3. Use the whole disk. This erases Windows.
4. Set a root password you keep somewhere safe. Create an admin user (e.g. `admin`).
5. At **Software selection**, untick everything except **standard system utilities**. No desktop.
6. Finish and reboot into the text login. Log in as `root`.

## 2. Install the kiosk pieces

Type each command below on its own line and press Enter after each one.
Wait for one to finish (the `root@...#` prompt comes back) before typing the next.

```sh
apt update
```

```sh
apt install -y git
```

```sh
git clone https://github.com/regalstaffing/kiosk-os-2026 /opt/kiosk-os
```

```sh
sh /opt/kiosk-os/scripts/setup-phase0.sh
```

The script installs the browser, creates the `kiosk` user, and copies in the lockdown
settings. It takes a few minutes and is safe to run again if anything goes wrong.
When it prints `Done.`, type:

```sh
reboot
```

The PC should boot straight into Chromium on the Regal portal and the two looping videos.

### If something goes wrong

- **Endless "Tried to start delayed item ... but failed" warnings:** press Ctrl+C, run
  `apt clean`, then `apt update`, then run the setup script again.
- **To update an already cloned copy:** `git -C /opt/kiosk-os pull`

## 3. Getting back in (admin)

Phase 0 has no admin screen yet. To get a shell: reboot, and in the GRUB menu press `e`,
add `systemd.unit=multi-user.target` to the end of the `linux` line, then Ctrl+X. Log in as root.
(This is possible because tamper protection, M9, is suspended during setup.)

## 4. Test

Work through `docs/escape-checklist.md` and note anything that gets through, plus any of your
real sites (Avionte, ADP, sign-in pages) that fail to load or break partway.

## Known limits of Phase 0

- No session wipe on idle yet: the profile only resets when the browser restarts or the PC reboots.
- No config download yet: the allow list is the copy in `policies/kiosk.json`.
- Wi-Fi is not set up by these steps; use wired network for testing.
