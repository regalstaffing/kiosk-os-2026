# Notes for AI agents and new maintainers

Read `README.md` first: it explains the two editions (`usb-live` = run-from-stick, `main` = hard drive), how a kiosk starts, releases and test builds, and where everything is.

Ground rules from the owner (Aria, Regal Staffing):

- **This repository is public. Never commit passwords, tokens, Wi-Fi passwords or other sensitive data**, including in `groups/*.toml` and commit messages.
- **Don't lose the working version.** Never rewrite history on `main` or `usb-live`, and don't push untested work to `usb-live`: every office stick installs it automatically.
- **Test first:** build a test image from your branch (`gh workflow run build-live.yml --ref <branch>`, published as `live-test`), have it tried on a real PC, and merge into `usb-live` only after the owner's OK.
- **Kiosk safety:** settings that come from the stick or the manager are data, never config files or scripts. Check every value before use; when in doubt, fail closed (for example, camera off).
- **Explain big design changes before making them.**
- Notes for the project use the form `<description> YYYY_MM_DD -Aria (Via Claude)`.

Related repository: [kiosk-manager-repo-2026Aria](https://github.com/regalstaffing/kiosk-manager-repo-2026Aria), the Kiosk Manager website that stick kiosks check in with. If you change what a kiosk sends or accepts (`agent/kiosk-checkin`), or the `127.0.0.1:8099` pages, check that repo too.
