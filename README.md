# kiosk-os-2026

A locked-down, browser-only kiosk system for repurposed 64-bit PCs, replacing Porteus Kiosk.
Debian 13 + the cage Wayland compositor + Chromium locked down with enterprise policies.

- Requirements: https://claude.ai/artifact/3DoRku9yRJcvZD23RqKZPw
- Technical plan: https://claude.ai/artifact/CQKnhR9dtQvy3yCcoBBp2o

**Never commit passwords or other sensitive data to this repository.** Wi-Fi passwords are entered at the kiosk.

## Layout

| Path | What it is |
| --- | --- |
| `docs/install.md` | Install a kiosk from the USB installer; admin console |
| `docs/phase0-hand-install.md` | Phase 0: set up a test kiosk by hand |
| `docs/escape-checklist.md` | Things to try that must all fail on a locked kiosk |
| `policies/kiosk.json` | Chromium managed policy (allow list, lockdown) |
| `scripts/setup.sh` | Setup script (run by the installer, or by hand as root) |
| `agent/` | Session manager (End session page, idle wipe, admin key) and `kiosk` admin command |
| `installer/` | Preseed and boot menus for the USB installer, and its build script |
| `system/` | systemd unit and system config files |
| `groups/` | Per-group config files (format draft; used from Phase 2) |

## Status

- Phase 0 (spike): done, see `docs/phase0-results.md`.
- Phase 1 (locked kiosk, USB installer, sessions): in testing.
