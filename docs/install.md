# Installing a kiosk from USB

Turns a PC into a kiosk with almost no typing. **This erases everything on the PC's disk.**

You need: a USB stick (1 GB+, it will be erased), a wired network connection, and the PC's admin (root) password you want to use.

## 1. Make the USB stick (once)

1. Download `kiosk-os-installer.iso` from the
   [installer-latest release](https://github.com/regalstaffing/kiosk-os-2026/releases/tag/installer-latest).
2. Write it to the stick with [Rufus](https://rufus.ie) (choose "DD image" if asked) or [balenaEtcher](https://etcher.balena.io).

## 2. Install

1. Plug in the network cable and the USB stick, and boot from the stick (boot menu key is usually F12 on Dell, F9 on HP, Esc or F10 on others).
2. Press **Enter** at the "Kiosk OS installer" screen.
3. Type the **root password** twice when asked. This is the admin password for the kiosk; keep it safe.
4. If the PC has more than one disk, pick the internal one (not the USB stick).
5. Wait about 10 to 20 minutes. Remove the USB stick when the PC restarts.

On first start the PC finishes the kiosk setup (a few minutes of text on screen), restarts once more, and then boots straight into the kiosk.

## 3. Admin screen

Press **Ctrl+Alt+Shift+A** on the kiosk and enter the root password from step 2.
(This ends the current browser session.)

| Button | What it does |
| --- | --- |
| Wi-Fi | List nearby networks and connect; the password is saved on this device only |
| Text console | Open the command line (see below) |
| Restart / Shut down | Restart or power off, after a confirmation |
| Back to kiosk | Return to the browser |

After 5 wrong passwords the screen locks for a minute. It closes by itself after 3 idle minutes.

### Text console commands

| Command | What it does |
| --- | --- |
| `kiosk back` | Return to the kiosk screen |
| `kiosk end-session` | Wipe the current session and return |
| `kiosk update` | Pull the latest kiosk files and apply them (then `reboot`) |
| `kiosk status` | Show whether the kiosk services are running |
| `kiosk check` | Show versions and settings for troubleshooting |
| `nmtui` | Network and Wi-Fi settings in text menus |

The console logs out after 10 idle minutes, and the kiosk comes back by itself.

Settings that live on the device are in `/etc/kiosk/settings` (for example `IDLE_MINUTES=6`).
Edit with `nano /etc/kiosk/settings`, then `systemctl restart kiosk-sessiond`.

## Sessions

- The browser's **Home** button opens the "End your session?" page. Ending a session closes every page and signs out of all sites.
- After `IDLE_MINUTES` with no keyboard, mouse or touch input, the session is wiped automatically.
- A reboot always starts clean.
