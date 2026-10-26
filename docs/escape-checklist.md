# Escape checklist

On a locked kiosk every item must FAIL (do nothing, or show a blocked page). Run on every release.

## Keyboard
- [ ] Ctrl+Alt+F1 … F12 (switch to text console)
- [ ] Ctrl+Alt+Backspace, Ctrl+Alt+Del
- [ ] Alt+Tab, Alt+F4, Super/Windows key
- [ ] Alt+SysRq combinations
- [ ] F11 / Esc to leave full screen

## Browser
- [ ] Ctrl+Shift+I, F12, Ctrl+Shift+J, Ctrl+U (developer tools / view source)
- [ ] Ctrl+N, Ctrl+Shift+N (new window, incognito)
- [ ] Ctrl+O, Ctrl+S, Ctrl+P (open, save, print)
- [ ] Ctrl+J, Ctrl+H (downloads, history)
- [ ] Right-click menu: "Inspect", "Save as", "Open link in new window"
- [ ] Typing chrome://settings, chrome://flags, file:///, about:blank, view-source:… (if an address bar is reachable)
- [ ] A link or redirect from an allowed site to a site not on the list
- [ ] A pop-up to a site not on the list
- [ ] Downloading a file from an allowed site

## Device
- [ ] Plug in a USB stick: nothing mounts, nothing offered for upload
- [ ] Kill/crash the browser (e.g. Ctrl+Shift+Q / Ctrl+W on last tab): it comes back within seconds
- [ ] Reboot: previous user's logins and history are gone
