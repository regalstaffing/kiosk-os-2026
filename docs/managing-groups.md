# Managing kiosks online

Each kiosk belongs to a **group** (for example a location or a function). A group's
settings live in one file in this repository: `groups/<name>.toml`. Edit that file
on GitHub and every kiosk in the group picks up the change by itself.

**Never put passwords or other sensitive information in these files. The repository is public.**

## What a group file controls

| Setting | What it does |
|---|---|
| `home_pages` | Pages opened at the start of every session, one tab each |
| `new_tab_page` | Page opened by the new-tab button (optional; defaults to the first home page) |
| `[session] idle_minutes` | Wipe the session after this many idle minutes (0 = never) |
| `[browser] printing` | `true` or `false` |
| `[allow] sites` | Sites applicants may open. Everything else is blocked |

Site examples: `"example.com"` allows the whole site and its subdomains.
`"example.com/jobs"` allows only that page and the pages under it.

## Changing a group's settings

1. Open the file on GitHub, for example `groups/default.toml`, and click the pencil icon.
2. Make the change. Keep the `"double quotes"` and the comma after each site.
3. Click **Commit changes**.
4. A check runs on GitHub within a minute. A green tick means the file is fine.
   A red X means it has a mistake; open the check to see which line.
   Kiosks ignore a file with mistakes and keep their last working settings.

Kiosks check for changes once at every start-up. To get a change on a kiosk right
away, press *Check for settings now* in its admin menu (Ctrl+Alt+Shift+A); the new
settings are used when the kiosk session starts again.

## Adding a group

Copy `groups/default.toml` to a new name such as `groups/front-desk.toml`, edit it,
and commit. Then put a kiosk in that group (below).

## Putting a kiosk in a group

On the kiosk, open the admin menu (Ctrl+Alt+Shift+A), choose **Text console** and run:

    kiosk group                          # show the current group and the ones available
    kiosk group front-desk               # move this kiosk to the front-desk group

## Trying changes on test kiosks first

The `patch-experimental` branch is for testing. Kiosks set to follow it get both
settings and software changes from that branch instead of `main`:

    kiosk group default patch-experimental

Make changes on `patch-experimental` first, check them on a test kiosk, then merge
them into `main` for every kiosk. To put a test kiosk back: `kiosk group default main`.

## If something goes wrong

`kiosk check` on the kiosk shows its group, branch and the result of the last settings check.
