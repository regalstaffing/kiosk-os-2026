# kiosk-os-2026

A locked-down, browser-only kiosk system for Regal Staffing's applicant lobby PCs, replacing Porteus Kiosk.
Debian 13 + the cage Wayland compositor + Chromium locked down with enterprise policies.

**Never commit passwords or other sensitive data to this repository: it is public.** Wi-Fi passwords are typed in at the kiosk.

New here (person or AI agent)? Read [Start here](#start-here), then `AGENTS.md`.

## Start here

There are two editions, on two branches:

| | **Run-from-stick** (the edition going forward) | **Hard drive** (the earlier edition) |
| --- | --- | --- |
| Branch | `usb-live` | `main` (GitHub's default branch) |
| How a PC gets it | Boot from a USB stick; the PC's own drive is never touched | USB installer that **erases** the PC's drive |
| Download | `kiosk-os-live.img.xz` from release [live-latest](https://github.com/regalstaffing/kiosk-os-2026/releases/tag/live-latest) | `kiosk-os-installer.iso` from release [installer-latest](https://github.com/regalstaffing/kiosk-os-2026/releases/tag/installer-latest) |
| Settings come from | The [Kiosk Manager](https://kiosks.regalstaffing.com) (repo [kiosk-manager-repo-2026Aria](https://github.com/regalstaffing/kiosk-manager-repo-2026Aria)); falls back to `groups/*.toml` | `groups/*.toml` in this repo |
| Updates | Daily check; new system image to a spare slot on the stick, used at next restart, automatic roll-back | `git pull` + `scripts/setup.sh` at start-up |
| Device settings (sound, mic, camera, brightness) | Yes, kept on the stick | Not yet ([PR #1](https://github.com/regalstaffing/kiosk-os-2026/pull/1)) |
| Guide | [docs/run-from-stick.md](https://github.com/regalstaffing/kiosk-os-2026/blob/usb-live/docs/run-from-stick.md) (on `usb-live`) | [docs/install.md](docs/install.md) |

The owner's rule from the start: **don't lose the current working version when moving to a new one.** That is why `main` is kept as it is, the stick keeps the previous version in a second slot, and test builds never reach office kiosks.

## How a stick kiosk works

1. The PC boots the stick: a read-only system image, with all changes kept in memory. A small data area on the stick holds what must survive a restart (see `SAVED` in `agent/kiosk-live`).
2. `kiosk-live boot` loads the saved settings and blocks every other USB stick.
3. `kiosk-checkin` checks in with the Kiosk Manager once per start-up, gets the group's settings and the admin password hash, and `kiosk-config` turns them into Chromium's policy (`/etc/chromium/policies/managed/kiosk.json`). If the manager can't be reached it keeps the last settings and retries every 5 minutes.
4. `kiosk.service` runs cage + Chromium (`agent/kiosk-browser`) as the `kiosk` user, with a fresh in-memory profile every session.
5. `kiosk-sessiond` serves the End session page and the looping video player on `http://127.0.0.1:8099`, wipes idle sessions, and opens the admin menu on **Ctrl+Alt+Shift+A** (`agent/kiosk-admin-ui`).
6. `kiosk-live update` (timer: 10 minutes after boot, then daily) downloads a newer image from the release.

## Releases and test builds

Built by `.github/workflows/build-live.yml`:

| Built from | Release tag | File name for sticks | Who gets it |
| --- | --- | --- | --- |
| `usb-live` (on every push that touches the system) | `live-latest` | `kiosk-os-live.img.xz` | Every normal stick, automatically |
| Any other branch (run the workflow by hand) | `live-test` | `kiosk-os-TEST-<branch>-<version>.img.xz` | Only sticks made from a test build |

A test image has `/etc/kiosk/channel` set to `live-test`, so a test stick updates only from test builds and never jumps to the normal version. When testing is over, re-make the test stick from `live-latest`.

`build-installer.yml` builds the hard-drive installer from `main`. `check-groups.yml` checks every `groups/*.toml` for mistakes.

## Making changes

1. Branch off `usb-live` (stick) or `main` (hard drive). Never push untested work to `usb-live`: it goes to every office kiosk.
2. Build a test image: `gh workflow run build-live.yml --ref <branch>`. It's published as `live-test`.
3. Test on a real PC with a test stick. On a stick that already runs a test build, `kiosk update` in the Text console fetches the newest test build and restarts.
4. With the owner's OK, merge into `usb-live`. Office sticks pick it up within a day and switch at their next restart.
5. If the change matters to the hard-drive edition too (for example anything in `agent/kiosk-sessiond`), bring it to `main` as well.

Tests: `python3 tests/kiosk_devices_restore_test.py` (device settings restore) and `live/test-boot.sh` (boots the image in QEMU; the workflow runs it and saves screenshots).

## Layout

This branch is `main` (hard drive). Some paths below exist only on `usb-live`: `live/`, `tests/`, `system/live/`, and in `agent/` the files `kiosk-live`, `kiosk-checkin`, `kiosk-hwid` and `kiosk_devices.py`.

| Path | What it is |
| --- | --- |
| `agent/` | Programs that run on the kiosk (see below) |
| `system/` | systemd units and system config; `system/live/` only on stick kiosks |
| `policies/kiosk.json` | Base Chromium policy (the lockdown). Sites and home pages are added from the group's settings. |
| `groups/` | One settings file per group. Fallback for stick kiosks, the source of truth for hard-drive kiosks. |
| `scripts/setup.sh` | Installs everything above; used by the image build and the hard-drive installer |
| `live/` | Builds the stick image (`build-live.sh`), its boot menu, and the QEMU boot test |
| `installer/` | Preseed and boot menus for the hard-drive USB installer |
| `tests/` | Automated tests |
| `branding/` | Logo for the boot splash and background |
| `docs/` | Guides (below) |
| `manager/prototype/` | The first clickable mock-up of the manager (`main` only). Superseded by [kiosk-manager-repo-2026Aria](https://github.com/regalstaffing/kiosk-manager-repo-2026Aria). |

### Programs in `agent/`

| File | What it does |
| --- | --- |
| `kiosk` | The admin command in the Text console: `kiosk check`, `kiosk update`, `kiosk group`, `kiosk back`… |
| `kiosk-browser` | Starts Chromium inside cage, again after every session |
| `kiosk-sessiond` | End session page, looping video page (`/loop?v=VIDEO&start=S&end=E`), idle wipe, admin key combination |
| `kiosk-admin-ui` | The admin menu (Wi-Fi, Device settings, Check for settings now, Text console, password, restart) |
| `kiosk_devices.py` | Device settings screen, and `restore` at boot (run by `kiosk-devices.service`) |
| `kiosk-checkin` | Checks in with the Kiosk Manager and saves what it sends |
| `kiosk-config` | Turns group settings into Chromium's policy; also checks group files |
| `kiosk-hwid` | Works out the PC's ID (serial, board, UUID…) for the manager |
| `kiosk-live` | Stick only: saving settings to the stick, USB guard, updates and roll-back |
| `kiosk-autoupdate` | Hard drive only: pulls updates from the branch at start-up |
| `kiosk-splash` | The branded screen shown behind the browser while it starts |

## Docs

| File | What it covers |
| --- | --- |
| `docs/run-from-stick.md` | Making a stick, what's saved on it, updates, device settings, the Kiosk Manager (on `usb-live`) |
| `docs/install.md` | Hard-drive install and the admin console |
| `docs/managing-groups.md` | Group files in `groups/` |
| `docs/escape-checklist.md` | Things to try that must all fail on a locked kiosk |
| `docs/phase0-*.md` | History: the first hand-built test kiosk |

Project background: [requirements](https://claude.ai/artifact/3DoRku9yRJcvZD23RqKZPw) and [technical plan](https://claude.ai/artifact/CQKnhR9dtQvy3yCcoBBp2o).

## Status

- Phases 0 and 1 (spike, locked kiosk, installer, sessions): done.
- Phase 2 (online management): done. The Kiosk Manager is live and stick kiosks use it.
- Run-from-stick edition: released (`live-latest`), with device settings and the looping video player.
