#!/usr/bin/python3
"""Tests for keeping device settings on a run-from-stick kiosk (kiosk_devices.py snapshot/remember/restore).
Uses a fake /proc/asound, backlight and fake amixer/udevadm/aplay/alsactl/kiosk-live. Run: python3 -I tests/kiosk_devices_restore_test.py"""
import os, sys, json, stat, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
R = tempfile.mkdtemp(prefix="kiosk-devices-test-")
for d in ("proc", "bin", "sys/bl/intel_backlight", "etc/kiosk", "udev"):
    os.makedirs(os.path.join(R, d))
open(R + "/proc/cards", "w").write(" 0 [PCH            ]: HDA-Intel - HDA Intel PCH\n                      HDA Intel PCH at 0xf7f10000 irq 30\n 1 [C920           ]: USB-Audio - HD Pro Webcam C920\n")
open(R + "/proc/pcm", "w").write("00-00: ALC3234 Analog : ALC3234 Analog : playback 1 : capture 1\n00-03: HDMI 0 : HDMI 0 : playback 1\n01-00: USB Audio : USB Audio : capture 1\n")
for name, value in (("max_brightness", "100"), ("brightness", "30"), ("type", "raw")):
    open(R + "/sys/bl/intel_backlight/" + name, "w").write(value)
FAKE = """#!/bin/sh
echo "%s $*" >> """ + R + """/calls
case "$*" in
  *sget*) echo "  Front Left: Playback 45 [45%%] [on]";;
  *scontents*) printf "Simple mixer control 'Master',0\\n  Capabilities: pvolume pswitch\\nSimple mixer control 'Capture',0\\n  Capabilities: cvolume cswitch\\n";;
esac
"""
for c in ("amixer", "udevadm", "aplay", "alsactl", "kiosk-live"):
    p = os.path.join(R, "bin", c)
    open(p, "w").write(FAKE % c)
    os.chmod(p, 0o755)
os.environ["KIOSK_DEVICES_NO_GUI"] = "1"
os.environ["PATH"] = R + "/bin:" + os.environ["PATH"]
sys.path.insert(0, os.path.join(HERE, "..", "agent"))
import kiosk_devices as k
k.PROC_ASOUND = R + "/proc"; k.ASOUND_CONF = R + "/etc/asound.conf"; k.CAMERA_RULES = R + "/udev/71-kiosk-camera.rules"
k.SYS_BACKLIGHT = R + "/sys/bl"; k.SYS_V4L = R + "/sys/v4l"; k.SAVED_CHOICES = R + "/etc/kiosk/devices.json"
def calls():
    try: c = open(R + "/calls").read()
    except OSError: c = ""
    open(R + "/calls", "w").close(); return c
# 1) normal round trip
json.dump({"output": "PCH,0", "input": "C920,0", "volume": 35, "muted": False, "mic_level": 80, "mic_muted": True,
           "camera": "usb:046d_HD_Pro_Webcam_C920_ABC123:00", "brightness": 60}, open(k.SAVED_CHOICES, "w"))
print(k.restore())
conf = open(k.ASOUND_CONF).read(); assert "kiosk-output=PCH,0" in conf and 'hw:CARD=C920,DEV=0' in conf
c = calls(); assert "sset Kiosk 35% unmute" in c and "-c C920 sset Capture,0 80% nocap" in c, c
rules = open(k.CAMERA_RULES).read(); assert 'ENV{ID_SERIAL}!="046d_HD_Pro_Webcam_C920_ABC123"' in rules, rules
assert open(R + "/sys/bl/intel_backlight/brightness").read() == "60"
# 2) tampered values are ignored; a camera limit that can't be read stays a limit (off)
json.dump({"output": 'PCH,0" } pcm.x { type file file "/tmp/x', "camera": 'usb:x", RUN+="/bin/sh -c evil":1', "brightness": 0, "volume": "999"}, open(k.SAVED_CHOICES, "w"))
os.remove(k.ASOUND_CONF)
print(k.restore())
assert not os.path.exists(k.ASOUND_CONF)
rules = open(k.CAMERA_RULES).read(); assert "kiosk-camera=off" in rules and "RUN" not in rules, rules
assert open(R + "/sys/bl/intel_backlight/brightness").read() == "5", "never below 5%"
# 3) saved output not connected any more: left alone
json.dump({"output": "Gone,0", "volume": 50}, open(k.SAVED_CHOICES, "w")); calls()
print(k.restore()); assert "Kiosk" not in calls()
# 4) not json / missing file
open(k.SAVED_CHOICES, "w").write("{oops"); print(k.restore())
os.remove(k.SAVED_CHOICES); print(k.restore())
# 5) snapshot + remember writes plain values and asks kiosk-live to save
k.use_output({"key": "PCH,0", "card": "PCH", "playback": True}, "C920,0")
k.remember()
saved = json.load(open(k.SAVED_CHOICES)); print(saved)
assert saved["output"] == "PCH,0" and saved["volume"] == 45 and "kiosk-live save" in calls()
print("ALL OK")
