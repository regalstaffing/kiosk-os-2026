"""Device settings pages of the kiosk admin screen: sound, microphone,
camera and screen brightness.

Kiosks may have no buttons on the unit and keyboards without media keys, so
these settings are made here. They apply to the whole system and last across
restarts:

- Sound and microphone: /etc/asound.conf (written here) picks the ALSA
  devices Chromium uses. Volume and mute are ALSA controls, saved with
  "alsactl store" and restored at start-up by alsa-utils.
- Camera: a udev rule lets the kiosk user open only the chosen camera, or none.
- Brightness: /sys/class/backlight, saved and restored by systemd-backlight.

Installed as /usr/local/lib/kiosk/kiosk_devices.py and used by kiosk-admin-ui
(which runs as root).
"""
import array
import glob
import os
import re
import subprocess
import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

try:
    gi.require_version("Gst", "1.0")
    from gi.repository import Gst  # noqa: E402
    Gst.init(None)
    HAVE_GST = Gst.ElementFactory.find("gtksink") is not None
except (ImportError, ValueError):
    HAVE_GST = False

# Paths (tests point these somewhere else)
PROC_ASOUND = "/proc/asound"
ASOUND_CONF = "/etc/asound.conf"
CAMERA_RULES = "/etc/udev/rules.d/71-kiosk-camera.rules"
SYS_V4L = "/sys/class/video4linux"
SYS_BACKLIGHT = "/sys/class/backlight"
TEST_SOUND = "/usr/share/sounds/alsa/Front_Center.wav"

# Our software volume and mute, created on the output card by asound.conf
VOLUME_CONTROL = "Kiosk"
NEW_VOLUME = 70           # % for a newly picked output
MIN_BRIGHTNESS = 5        # % so the screen never goes fully dark
HEADER = "# Written by the kiosk admin screen (Device settings). Changes here are overwritten.\n"

CSS = b"""
scale trough { min-height: 10px; }
scale slider { min-width: 34px; min-height: 34px; }
.section { font-weight: bold; margin-top: 8px; }
button.small { min-height: 64px; min-width: 150px; }
levelbar block { min-height: 18px; }
"""


def run(*cmd, data=None):
    try:
        p = subprocess.run(cmd, capture_output=True, input=data,
                           text=data is None, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)
    out = p.stdout + p.stderr
    if isinstance(out, bytes):
        out = out.decode(errors="replace")
    return p.returncode, out.strip()


def read(path, default=""):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return default


def save_mixer():
    """Keep volume, mute and mic level for the next start-up."""
    run("alsactl", "store")


# --- ALSA devices ---

def alsa_cards():
    """{card number: (id, name)} from /proc/asound."""
    cards = {}
    for line in read(os.path.join(PROC_ASOUND, "cards")).splitlines():
        m = re.match(r"\s*(\d+)\s+\[(\S+)\s*\]:\s*(.*?)\s+-\s+(.*)", line)
        if m:
            cards[int(m.group(1))] = (m.group(2), m.group(4).strip())
    return cards


def alsa_devices():
    """Sound devices: dicts with key ("CARDID,DEV"), card, label, playback, capture."""
    cards = alsa_cards()
    devices = []
    for line in read(os.path.join(PROC_ASOUND, "pcm")).splitlines():
        parts = [p.strip() for p in line.split(":")]
        m = re.match(r"(\d+)-(\d+)$", parts[0]) if parts else None
        if not m or int(m.group(1)) not in cards:
            continue
        card, dev = int(m.group(1)), int(m.group(2))
        card_id, card_name = cards[card]
        name = parts[2] if len(parts) > 2 and parts[2] else parts[1]
        devices.append({
            "key": "%s,%d" % (card_id, dev),
            "card": card_id,
            "label": "%s — %s" % (card_name, name),
            "screen": bool(re.search(r"HDMI|DisplayPort|\bDP\b", name, re.I)),
            "playback": any(p.startswith("playback") for p in parts[3:]),
            "capture": any(p.startswith("capture") for p in parts[3:]),
        })
    return devices


def current_sound_choice():
    """(output key, input key) saved in asound.conf, or (None, None)."""
    text = read(ASOUND_CONF)
    out = re.search(r"^# kiosk-output=(\S+)", text, re.M)
    inp = re.search(r"^# kiosk-input=(\S+)", text, re.M)
    return (out.group(1) if out else None), (inp.group(1) if inp else None)


def asound_conf(output, inp):
    """asound.conf text: the kiosk's default output (with our volume and mute) and input."""
    card, dev = output.split(",")
    text = HEADER + "# kiosk-output=%s\n" % output
    if inp:
        text += "# kiosk-input=%s\n" % inp
        in_card, in_dev = inp.split(",")
        capture = '"hw:CARD=%s,DEV=%s"' % (in_card, in_dev)
    else:
        capture = '"sysdefault"'
    text += """
pcm.!default {
    type asym
    playback.pcm "kiosk_out"
    capture.pcm "kiosk_in"
}

# Output: volume, then mute, then dmix so several sounds can play at once
pcm.kiosk_out {
    type plug
    slave.pcm {
        type softvol
        control { name "%(ctl)s Playback Volume" card %(card)s }
        slave.pcm {
            type softvol
            control { name "%(ctl)s Playback Switch" card %(card)s }
            resolution 2
            slave.pcm "dmix:CARD=%(card)s,DEV=%(dev)s"
        }
    }
}

pcm.kiosk_in {
    type plug
    slave.pcm %(capture)s
}

ctl.!default {
    type hw
    card %(card)s
}
""" % {"ctl": VOLUME_CONTROL, "card": card, "dev": dev, "capture": capture}
    return text


def mixer_controls(card):
    """Simple mixer controls of a card: list of (name, index, capabilities)."""
    code, out = run("amixer", "-c", card, "scontents")
    if code != 0:
        return []
    controls = []
    for block in re.split(r"^Simple mixer control ", out, flags=re.M):
        m = re.match(r"'(.*)',(\d+)", block)
        if not m:
            continue
        caps = re.search(r"^\s*Capabilities:(.*)$", block, re.M)
        controls.append((m.group(1), int(m.group(2)), set(caps.group(1).split()) if caps else set()))
    return controls


def mixer_get(card, control):
    """(volume %, switched on) of a simple control, or (None, None)."""
    code, out = run("amixer", "-c", card, "sget", control)
    if code != 0:
        return None, None
    pct = re.search(r"\[(\d+)%\]", out)
    sw = re.search(r"\[(on|off)\]", out)
    return (int(pct.group(1)) if pct else None), (sw.group(1) == "on" if sw else None)


def mixer_set(card, control, *values):
    return run("amixer", "-q", "-c", card, "sset", control, *values)


def open_output():
    """Open the default output for a moment, so the volume controls exist."""
    run("aplay", "-q", "-D", "default", "-t", "raw", "-f", "S16_LE", "-r", "48000", "-c", "2",
        data=bytes(48000 * 2 * 2 // 10))


def use_output(device, inp):
    """Make device the kiosk's sound output. Returns an error message or None."""
    card = device["card"]
    had_volume = mixer_get(card, VOLUME_CONTROL)[0] is not None
    with open(ASOUND_CONF, "w") as f:
        f.write(asound_conf(device["key"], inp))
    open_output()
    if mixer_get(card, VOLUME_CONTROL)[0] is None:
        return "The volume control could not be set up on this device."
    if not had_volume:
        mixer_set(card, VOLUME_CONTROL, "%d%%" % NEW_VOLUME, "unmute")
    # Hardware volume all the way up and on: the kiosk volume above controls the level
    for name, index, caps in mixer_controls(card):
        ctl = "%s,%d" % (name, index)
        if name in ("Master", "Speaker", "Headphone", "PCM", "Front") and "pvolume" in caps:
            mixer_set(card, ctl, "100%", "unmute")
        elif name.startswith("IEC958") and "pswitch" in caps:
            mixer_set(card, ctl, "unmute")
    save_mixer()
    return None


def use_input(device, output):
    with open(ASOUND_CONF, "w") as f:
        f.write(asound_conf(output, device["key"]))
    save_mixer()


def mic_control(card):
    """The capture level control of a card, e.g. "Capture,0" or "Mic,0", or None."""
    controls = [(n, i) for n, i, caps in mixer_controls(card) if "cvolume" in caps]
    for preferred in ("Capture", "Mic", "Internal Mic", "Digital"):
        for name, index in controls:
            if name == preferred:
                return "%s,%d" % (name, index)
    return "%s,%d" % controls[0] if controls else None


def pick_default_sound(devices):
    """First output that is not a screen (HDMI/DP), and the first microphone."""
    outs = [d for d in devices if d["playback"]]
    ins = [d for d in devices if d["capture"]]
    out = next((d for d in outs if not d["screen"]), outs[0] if outs else None)
    return out, (ins[0] if ins else None)


# --- cameras ---

def udev_props(devnode):
    code, out = run("udevadm", "info", "-q", "property", "-n", devnode)
    props = {}
    for line in out.splitlines() if code == 0 else []:
        k, _, v = line.partition("=")
        props[k] = v
    return props


def cameras():
    """Cameras that can take pictures: dicts with key, label, dev, match (udev rule match)."""
    found = []
    nodes = sorted(glob.glob(os.path.join(SYS_V4L, "video*")),
                   key=lambda p: int(re.sub(r"\D", "", os.path.basename(p)) or 0))
    for node in nodes:
        dev = "/dev/" + os.path.basename(node)
        props = udev_props(dev)
        if ":capture:" not in props.get("ID_V4L_CAPABILITIES", ""):
            continue  # e.g. the metadata node every USB camera also has
        serial, iface = props.get("ID_SERIAL"), props.get("ID_USB_INTERFACE_NUM")
        if serial and iface:
            # Same camera even in another USB port
            key = "usb:%s:%s" % (serial, iface)
            match = [("ID_SERIAL", serial), ("ID_USB_INTERFACE_NUM", iface)]
        else:
            key = "path:" + props.get("ID_PATH", dev)
            match = [("ID_PATH", props.get("ID_PATH", ""))]
        name = props.get("ID_V4L_PRODUCT") or read(os.path.join(node, "name")) or dev
        name = name.split(":")[0].strip() or name  # "Integrated Camera: Integrated C"
        found.append({"key": key, "label": name, "dev": dev, "match": match})
    return found


def current_camera():
    """Saved camera key, "off", or None (all cameras allowed)."""
    m = re.search(r"^# kiosk-camera=(\S+)", read(CAMERA_RULES), re.M)
    return m.group(1) if m else None


def camera_rules(camera):
    """udev rules that take away the kiosk's access to all cameras except camera (None: all)."""
    if camera is None:
        return HEADER + "# kiosk-camera=off\nSUBSYSTEM==\"video4linux\", TAG-=\"uaccess\"\n"
    text = HEADER + "# kiosk-camera=%s\n" % camera["key"]
    for prop, value in camera["match"]:
        value = re.sub(r'["\\]', "", value)
        text += 'SUBSYSTEM=="video4linux", ENV{%s}!="%s", TAG-="uaccess"\n' % (prop, value)
    return text


def use_camera(camera, all_cameras=False):
    """camera: dict, None for no camera; all_cameras=True removes the limit."""
    if all_cameras:
        try:
            os.remove(CAMERA_RULES)
        except FileNotFoundError:
            pass
    else:
        os.makedirs(os.path.dirname(CAMERA_RULES), exist_ok=True)
        with open(CAMERA_RULES, "w") as f:
            f.write(camera_rules(camera))
    run("udevadm", "control", "--reload")
    run("udevadm", "trigger", "--subsystem-match=video4linux", "--action=change")
    run("udevadm", "settle", "--timeout=5")
    # Clear access the kiosk user was given earlier; it gets access to the
    # allowed camera again when the kiosk starts
    for dev in glob.glob("/dev/video*"):
        try:
            os.removexattr(dev, "system.posix_acl_access")
        except OSError:
            pass


# --- screen brightness ---

def backlight():
    """The screen's backlight folder, or None. Kernel advice: firmware, then platform, then raw."""
    devs = glob.glob(os.path.join(SYS_BACKLIGHT, "*"))
    order = {"firmware": 0, "platform": 1, "raw": 2}
    devs.sort(key=lambda d: (order.get(read(os.path.join(d, "type")), 3), d))
    return devs[0] if devs else None


def get_brightness(dev):
    top = int(read(os.path.join(dev, "max_brightness"), "0") or 0)
    now = int(read(os.path.join(dev, "brightness"), "0") or 0)
    return round(100 * now / top) if top else None


def set_brightness(dev, pct):
    top = int(read(os.path.join(dev, "max_brightness"), "0") or 0)
    pct = max(MIN_BRIGHTNESS, min(100, pct))
    with open(os.path.join(dev, "brightness"), "w") as f:
        f.write(str(max(1, round(top * pct / 100))))


# --- pages ---

class DeviceSettings:
    """Adds the Device settings pages to the admin window's stack.

    win must provide stack, page(), label(text, css) and button(text, handler, css).
    """

    def __init__(self, win, back_to="menu"):
        self.win = win
        self.back_to = back_to
        self.devices = []
        self.cameras = []
        self.out_key = self.in_key = None
        self.mic_ctl = None
        self.meter = None
        self.pipeline = None
        self.pending = {}
        self.filling = False
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(win.get_screen(), provider,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1)
        win.stack.add_named(self.build_menu(), "devices")
        win.stack.add_named(self.build_sound(), "sound")
        win.stack.add_named(self.build_mic(), "mic")
        win.stack.add_named(self.build_camera(), "camera")
        win.stack.add_named(self.build_brightness(), "brightness")

    # helpers

    def page(self, title):
        box = self.win.page()
        box.set_size_request(640, -1)
        box.pack_start(self.win.label(title, "title"), False, False, 0)
        msg = self.win.label("", "status")
        msg.set_max_width_chars(60)
        box.pack_start(msg, False, False, 0)
        return box, msg

    def chooser(self, box, handler, height=150):
        scroller = Gtk.ScrolledWindow()
        scroller.set_min_content_height(height)
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        listbox = Gtk.ListBox()
        listbox.connect("row-selected", handler)
        scroller.add(listbox)
        box.pack_start(scroller, False, False, 0)
        return listbox

    def fill(self, listbox, items, selected_key):
        """items: (key, text) pairs. Selects the row with selected_key without applying it."""
        self.filling = True
        for row in listbox.get_children():
            listbox.remove(row)
        for key, text in items:
            row = Gtk.ListBoxRow()
            row.key = key
            row.add(Gtk.Label(label=text, xalign=0, margin=8))
            listbox.add(row)
            if key == selected_key:
                listbox.select_row(row)
        listbox.show_all()
        self.filling = False

    def slider(self, box, label, handler, lowest=0):
        row = Gtk.Box(spacing=16)
        row.pack_start(self.win.label(label), False, False, 0)
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, lowest, 100, 1)
        scale.set_digits(0)
        scale.set_value_pos(Gtk.PositionType.RIGHT)
        scale.connect("value-changed", handler)
        row.pack_start(scale, True, True, 0)
        box.pack_start(row, False, False, 0)
        return row, scale

    def later(self, name, func):
        """Run func shortly, once, while a slider is being dragged."""
        if name in self.pending:
            GLib.source_remove(self.pending[name])

        def go():
            del self.pending[name]
            func()
            return False
        self.pending[name] = GLib.timeout_add(150, go)

    def show(self, name):
        self.win.stack.set_visible_child_name(name)

    def on_back(self, _widget):
        self.stop_meter()
        self.stop_preview()
        self.menu_msg.set_text(self.summary())
        self.show("devices")

    # menu

    def build_menu(self):
        box, self.menu_msg = self.page("Device settings")
        for text, handler in (("Sound", self.on_sound), ("Microphone", self.on_mic),
                              ("Camera", self.on_camera), ("Screen brightness", self.on_brightness)):
            box.pack_start(self.win.button(text, handler), False, False, 0)
        box.pack_start(self.win.button("Back", lambda _w: self.win.stack.set_visible_child_name(self.back_to)),
                       False, False, 0)
        return box

    def open(self, _widget=None):
        self.menu_msg.set_text(self.summary())
        self.show("devices")

    def summary(self):
        parts = []
        out = self.find(self.out_key or current_sound_choice()[0])
        if out:
            vol, on = mixer_get(out["card"], VOLUME_CONTROL)
            if vol is not None:
                parts.append("Volume %d%%%s" % (vol, "" if on else " (muted)"))
        cam = current_camera()
        parts.append("Camera off" if cam == "off" else "Camera on")
        bl = backlight()
        if bl and get_brightness(bl) is not None:
            parts.append("Brightness %d%%" % get_brightness(bl))
        return "   ·   ".join(parts)

    def find(self, key):
        if not self.devices:
            self.devices = alsa_devices()
        return next((d for d in self.devices if d["key"] == key), None)

    def ensure_sound(self):
        """Read the sound devices; on first use, pick an output and a microphone."""
        self.devices = alsa_devices()
        self.out_key, self.in_key = current_sound_choice()
        if self.out_key is None:
            out, inp = pick_default_sound(self.devices)
            if out:
                use_output(out, inp["key"] if inp else None)
                self.out_key, self.in_key = out["key"], (inp["key"] if inp else None)

    # sound

    def build_sound(self):
        box, self.sound_msg = self.page("Sound")
        box.pack_start(self.win.label("Play sound through", "section"), False, False, 0)
        self.out_list = self.chooser(box, self.on_output_selected)
        self.vol_row, self.volume = self.slider(box, "Volume", self.on_volume)
        self.mute = Gtk.ToggleButton(label="Mute")
        self.mute.get_style_context().add_class("small")
        self.mute.connect("toggled", self.on_mute)
        self.vol_row.pack_start(self.mute, False, False, 0)
        box.pack_start(self.win.button("Play test sound", self.on_test_sound), False, False, 0)
        box.pack_start(self.win.button("Back", self.on_back), False, False, 0)
        return box

    def on_sound(self, _widget):
        self.show("sound")
        self.ensure_sound()
        outs = [d for d in self.devices if d["playback"]]
        if not outs:
            self.sound_msg.set_text("No sound device found.")
        elif not self.find(self.out_key):
            self.sound_msg.set_text("The chosen sound device is not connected. Pick another one.")
        else:
            self.sound_msg.set_text("Changes are used right away and kept after a restart.")
        items = [(d["key"], d["label"] + ("   (screen)" if d["screen"] else "")) for d in outs]
        self.fill(self.out_list, items, self.out_key)
        self.load_volume()

    def load_volume(self):
        dev = self.find(self.out_key)
        vol, on = mixer_get(dev["card"], VOLUME_CONTROL) if dev else (None, None)
        self.vol_row.set_sensitive(vol is not None)
        self.filling = True
        self.volume.set_value(vol or 0)
        self.mute.set_active(on is False)
        self.filling = False

    def on_output_selected(self, _listbox, row):
        if row is None or self.filling or row.key == self.out_key:
            return
        dev = self.find(row.key)
        self.sound_msg.set_text("Switching…")
        err = use_output(dev, self.in_key)
        self.out_key = row.key
        self.sound_msg.set_text(err or "Sound now plays through %s." % dev["label"])
        self.load_volume()

    def on_volume(self, scale):
        if self.filling:
            return
        dev = self.find(self.out_key)
        if dev:
            self.later("volume", lambda: (mixer_set(dev["card"], VOLUME_CONTROL, "%d%%" % scale.get_value()),
                                          save_mixer()))

    def on_mute(self, button):
        if self.filling:
            return
        dev = self.find(self.out_key)
        if dev:
            mixer_set(dev["card"], VOLUME_CONTROL, "mute" if button.get_active() else "unmute")
            save_mixer()

    def on_test_sound(self, _widget):
        if os.path.exists(TEST_SOUND):
            cmd = ["aplay", "-q", "-D", "default", TEST_SOUND]
        else:
            cmd = ["speaker-test", "-D", "default", "-t", "sine", "-f", "440", "-c", "2", "-l", "1"]
        self.sound_msg.set_text("Playing a test sound…")

        def work():
            code, out = run(*cmd)
            GLib.idle_add(self.sound_msg.set_text, "Did you hear it? If not, check the volume and mute, "
                          "or pick another device." if code == 0 else "Could not play: " + out[-200:])
        threading.Thread(target=work, daemon=True).start()

    # microphone

    def build_mic(self):
        box, self.mic_msg = self.page("Microphone")
        box.pack_start(self.win.label("Use the microphone of", "section"), False, False, 0)
        self.in_list = self.chooser(box, self.on_input_selected)
        self.level_row, self.level = self.slider(box, "Level", self.on_level)
        self.mic_mute = Gtk.ToggleButton(label="Mute")
        self.mic_mute.get_style_context().add_class("small")
        self.mic_mute.connect("toggled", self.on_mic_mute)
        self.level_row.pack_start(self.mic_mute, False, False, 0)
        box.pack_start(self.win.label("Speak: the bar moves when the microphone hears you."), False, False, 0)
        self.meter_bar = Gtk.LevelBar(min_value=0, max_value=1)
        box.pack_start(self.meter_bar, False, False, 0)
        box.pack_start(self.win.button("Back", self.on_back), False, False, 0)
        return box

    def on_mic(self, _widget):
        self.show("mic")
        self.ensure_sound()
        ins = [d for d in self.devices if d["capture"]]
        if not ins:
            self.mic_msg.set_text("No microphone found.")
        elif not self.out_key:
            self.mic_msg.set_text("Set up Sound first.")
        else:
            self.mic_msg.set_text("Changes are used right away and kept after a restart.")
        self.fill(self.in_list, [(d["key"], d["label"]) for d in ins], self.in_key)
        self.load_level()
        self.start_meter()

    def load_level(self):
        dev = self.find(self.in_key)
        self.mic_ctl = mic_control(dev["card"]) if dev else None
        vol, on = mixer_get(dev["card"], self.mic_ctl) if self.mic_ctl else (None, None)
        self.filling = True
        self.level.set_sensitive(vol is not None)
        self.level.set_value(vol or 0)
        self.mic_mute.set_sensitive(on is not None)
        self.mic_mute.set_active(on is False)
        self.filling = False
        if dev and vol is None:
            self.mic_msg.set_text("This microphone has no level setting.")

    def on_input_selected(self, _listbox, row):
        if row is None or self.filling or row.key == self.in_key or not self.out_key:
            return
        self.stop_meter()
        use_input(self.find(row.key), self.out_key)
        self.in_key = row.key
        self.mic_msg.set_text("Using the microphone of %s." % self.find(row.key)["label"])
        self.load_level()
        self.start_meter()

    def on_level(self, scale):
        dev = self.find(self.in_key)
        if not self.filling and dev and self.mic_ctl:
            self.later("level", lambda: (mixer_set(dev["card"], self.mic_ctl, "%d%%" % scale.get_value()),
                                         save_mixer()))

    def on_mic_mute(self, button):
        dev = self.find(self.in_key)
        if not self.filling and dev and self.mic_ctl:
            mixer_set(dev["card"], self.mic_ctl, "nocap" if button.get_active() else "cap")
            save_mixer()

    def start_meter(self):
        self.stop_meter()
        if not self.in_key:
            return
        try:
            proc = subprocess.Popen(["arecord", "-q", "-D", "default", "-t", "raw", "-f", "S16_LE",
                                     "-r", "16000", "-c", "1"],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            return
        self.meter = proc

        def work():
            while True:
                chunk = proc.stdout.read(1600)  # 50 ms
                if not chunk:
                    break
                samples = array.array("h", chunk[:len(chunk) // 2 * 2])
                peak = max((abs(s) for s in samples), default=0) / 32768
                GLib.idle_add(self.meter_bar.set_value, min(1.0, peak ** 0.5))  # quiet speech shows too
            if self.meter is proc and proc.wait() != 0:
                err = proc.stderr.read().decode(errors="replace").strip()
                GLib.idle_add(self.mic_msg.set_text, "Could not listen to the microphone: " + err[-200:])
        threading.Thread(target=work, daemon=True).start()

    def stop_meter(self):
        if self.meter:
            proc, self.meter = self.meter, None
            proc.terminate()
        self.meter_bar.set_value(0)

    # camera

    def build_camera(self):
        box, self.cam_msg = self.page("Camera")
        box.pack_start(self.win.label("Camera the kiosk may use", "section"), False, False, 0)
        self.cam_list = self.chooser(box, self.on_camera_selected, height=130)
        self.preview_box = Gtk.Box()
        self.preview_box.set_size_request(400, 225)
        self.preview_box.set_halign(Gtk.Align.CENTER)
        box.pack_start(self.preview_box, False, False, 0)
        box.pack_start(self.win.button("Back", self.on_back), False, False, 0)
        return box

    def on_camera(self, _widget):
        self.show("camera")
        self.cameras = cameras()
        saved = current_camera()
        items = [(c["key"], c["label"]) for c in self.cameras]
        items.append(("off", "No camera (turned off)"))
        if saved is None:
            items.append(("all", "Any camera (the browser picks)"))
        self.fill(self.cam_list, items, saved or "all")
        if not self.cameras:
            self.cam_msg.set_text("No camera found.")
        elif saved and saved != "off" and saved not in [c["key"] for c in self.cameras]:
            self.cam_msg.set_text("The chosen camera is not connected. Pick another one.")
        else:
            self.cam_msg.set_text("The kiosk can only use the camera picked here.")
        self.preview(next((c for c in self.cameras if c["key"] == saved), None)
                     or (self.cameras[0] if saved is None and self.cameras else None))

    def on_camera_selected(self, _listbox, row):
        if row is None or self.filling:
            return
        cam = next((c for c in self.cameras if c["key"] == row.key), None)
        self.stop_preview()
        if row.key == "all":
            use_camera(None, all_cameras=True)
            self.cam_msg.set_text("The kiosk may use any camera.")
        else:
            use_camera(cam)
            self.cam_msg.set_text("Camera turned off." if cam is None else
                                  "The kiosk now uses %s." % cam["label"])
        self.preview(cam)

    def preview(self, cam):
        self.stop_preview()
        for child in self.preview_box.get_children():
            self.preview_box.remove(child)
        if cam is None:
            self.preview_box.pack_start(self.win.label("No preview"), True, True, 0)
        elif not HAVE_GST:
            self.preview_box.pack_start(self.win.label("Preview is not available on this system."),
                                        True, True, 0)
        else:
            try:
                pipeline = Gst.parse_launch("v4l2src device=%s ! decodebin ! videoconvert ! "
                                            "gtksink name=sink sync=false" % cam["dev"])
            except GLib.Error as e:
                self.preview_box.pack_start(self.win.label("No preview: " + e.message), True, True, 0)
            else:
                widget = pipeline.get_by_name("sink").props.widget
                widget.set_size_request(400, 225)
                self.preview_box.pack_start(widget, True, True, 0)
                bus = pipeline.get_bus()
                bus.add_signal_watch()
                bus.connect("message::error", self.on_preview_error)
                self.pipeline = pipeline
                pipeline.set_state(Gst.State.PLAYING)
        self.preview_box.show_all()

    def on_preview_error(self, _bus, message):
        err, _debug = message.parse_error()
        self.stop_preview()
        self.cam_msg.set_text("No preview: " + err.message)

    def stop_preview(self):
        if self.pipeline:
            pipeline, self.pipeline = self.pipeline, None
            pipeline.get_bus().remove_signal_watch()
            pipeline.set_state(Gst.State.NULL)

    # brightness

    def build_brightness(self):
        box, self.bright_msg = self.page("Screen brightness")
        self.bright_row, self.bright = self.slider(box, "Brightness", self.on_bright, MIN_BRIGHTNESS)
        box.pack_start(self.win.button("Back", self.on_back), False, False, 0)
        return box

    def on_brightness(self, _widget):
        self.show("brightness")
        dev = backlight()
        pct = get_brightness(dev) if dev else None
        self.bright_row.set_sensitive(pct is not None)
        self.filling = True
        self.bright.set_value(pct or MIN_BRIGHTNESS)
        self.filling = False
        self.bright_msg.set_text("Kept after a restart." if pct is not None else
                                 "This screen does not let the computer change its brightness.")

    def on_bright(self, scale):
        dev = backlight()
        if not self.filling and dev:
            self.later("bright", lambda: set_brightness(dev, int(scale.get_value())))
