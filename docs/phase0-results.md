# Phase 0 test results

Dell laptop (Intel e1000e Ethernet), Debian 13, Chromium 156, tested 2026-11-02.

| Check | Result | Follow-up |
| --- | --- | --- |
| Ctrl+Alt+F1…F12 console switch | Blocked | |
| Ctrl+Alt+Backspace / Del | Blocked | |
| Alt+Tab, Super key | Blocked | |
| Alt+F4 | Closes browser, restarts in seconds | Acceptable for now; revisit |
| Alt+SysRq (Alt+PrtSc + r/e/i/b) | No effect | |
| F11 / Esc leave full screen | Blocked | |
| Developer tools / view source | Blocked ("not allowed" message) | |
| Ctrl+N new window | Opens (still whitelisted) | Low priority |
| Incognito | Blocked | |
| Ctrl+O / S / P | Blocked | |
| F1 help key | Opened Chrome help (google.com is allowed) | Fixed: F1 disabled, Chrome help pages blocked |
| Ctrl+H / Ctrl+J history, downloads | Opened in first run | Fixed: chrome:// pages blocked |
| Right-click Inspect / Save as | Blocked / greyed out | |
| Right-click Open link in new window | Opens (still whitelisted) | Low priority |
| Typing chrome://, file://, view-source: | Blocked | |
| Link/redirect to non-listed site | Blocked | |
| Pop-up to non-listed site | Not tested yet | |
| Download from allowed site | Not tested yet | |
| USB stick | Blocked (after fix: drivers blocked at boot); first run detected it as sdb | |
| Ctrl+W on last tab | Browser restarts in seconds | |
| Reboot clears logins | Gmail signed out after reboot | |
| Network | Ethernet was not configured by installer | Fixed: setup script enables all Ethernet ports |
