# kiosk-os-2026

A locked-down, browser-only kiosk system for repurposed 64-bit PCs, replacing Porteus Kiosk.
Debian 13 + the cage Wayland compositor + Chromium locked down with enterprise policies.

- Requirements: https://claude.ai/artifact/3DoRku9yRJcvZD23RqKZPw
- Technical plan: https://claude.ai/artifact/CQKnhR9dtQvy3yCcoBBp2o

**Never commit passwords or other sensitive data to this repository.** Wi-Fi passwords are entered at the kiosk.

## Layout

| Path | What it is |
| --- | --- |
| `docs/phase0-hand-install.md` | Phase 0: set up a test kiosk by hand |
| `docs/escape-checklist.md` | Things to try that must all fail on a locked kiosk |
| `policies/kiosk.json` | Chromium managed policy (allow list, lockdown) |
| `system/` | systemd unit and system config files |
| `groups/` | Per-group config files (format draft; used from Phase 2) |

## Status

Phase 0 (spike): prove that the current whitelist works as Chromium policy on real hardware.
