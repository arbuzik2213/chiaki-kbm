#!/usr/bin/env python3
"""
chiaki-kbm: play PS5 Remote Play (chiaki-ng) with keyboard and mouse on Linux.

Reads physical keyboards/mice with evdev, turns them into a virtual gamepad
(uinput) according to a JSON profile, and grabs the devices only while the
chiaki-ng window is focused (reported by a small KWin script over D-Bus).
Keys are read by physical position, so the active keyboard layout does not matter.
"""
import argparse
import json
import os
import selectors
import subprocess
import sys
import threading
import time

import evdev
from evdev import ecodes as e

APP = "chiaki-kbm"
VIRTUAL_NAME = "chiaki-kbm virtual gamepad"
VIRTUAL_KBD_NAME = "chiaki-kbm passthrough keyboard"
# pid.codes test VID/PID — a neutral id that SDL maps via SDL_GAMECONTROLLERCONFIG
VENDOR, PRODUCT, VERSION = 0x1209, 0x5053, 0x0001

# ---------------------------------------------------------------- gamepad ----

PAD_BUTTONS = {
	"CROSS": e.BTN_SOUTH, "CIRCLE": e.BTN_EAST, "TRIANGLE": e.BTN_NORTH, "SQUARE": e.BTN_WEST,
	"L1": e.BTN_TL, "R1": e.BTN_TR, "SHARE": e.BTN_SELECT, "OPTIONS": e.BTN_START,
	"PS": e.BTN_MODE, "L3": e.BTN_THUMBL, "R3": e.BTN_THUMBR,
	"DPAD_UP": e.BTN_DPAD_UP, "DPAD_DOWN": e.BTN_DPAD_DOWN,
	"DPAD_LEFT": e.BTN_DPAD_LEFT, "DPAD_RIGHT": e.BTN_DPAD_RIGHT,
	"TOUCHPAD": e.BTN_TRIGGER_HAPPY1,
}
STICK_DIRS = {
	"LS_UP": ("ly", -1), "LS_DOWN": ("ly", 1), "LS_LEFT": ("lx", -1), "LS_RIGHT": ("lx", 1),
	"RS_UP": ("ry", -1), "RS_DOWN": ("ry", 1), "RS_LEFT": ("rx", -1), "RS_RIGHT": ("rx", 1),
}
TRIGGERS = {"L2": e.ABS_Z, "R2": e.ABS_RZ}
AXIS_CODES = {"lx": e.ABS_X, "ly": e.ABS_Y, "rx": e.ABS_RX, "ry": e.ABS_RY}

# SDL evdev numbers buttons in key-code order: BTN_SOUTH.. then BTN_DPAD_*, then BTN_TRIGGER_HAPPY1
SDL_GUID = "03000000" + "0912" + "0000" + "5350" + "0000" + "0100" + "0000"
SDL_MAPPING = (f"{SDL_GUID},{VIRTUAL_NAME},platform:Linux,"
	"a:b0,b:b1,y:b2,x:b3,leftshoulder:b4,rightshoulder:b5,back:b6,start:b7,guide:b8,"
	"leftstick:b9,rightstick:b10,dpup:b11,dpdown:b12,dpleft:b13,dpright:b14,touchpad:b15,"
	"leftx:a0,lefty:a1,lefttrigger:a2,rightx:a3,righty:a4,righttrigger:a5,")


def make_gamepad():
	absinfo = lambda lo, hi: evdev.AbsInfo(0, lo, hi, 0, 0, 0)
	cap = {
		e.EV_KEY: sorted(PAD_BUTTONS.values()),
		e.EV_ABS: [
			(e.ABS_X, absinfo(-32768, 32767)), (e.ABS_Y, absinfo(-32768, 32767)),
			(e.ABS_Z, absinfo(0, 255)),
			(e.ABS_RX, absinfo(-32768, 32767)), (e.ABS_RY, absinfo(-32768, 32767)),
			(e.ABS_RZ, absinfo(0, 255)),
		],
	}
	return evdev.UInput(cap, name=VIRTUAL_NAME, vendor=VENDOR, product=PRODUCT,
		version=VERSION, bustype=e.BUS_USB)


class Pad:
	"""Virtual gamepad that only writes changed values."""

	def __init__(self):
		self.ui = make_gamepad()
		self.sent = {}

	def apply(self, buttons, sticks, triggers):
		changed = False
		for name, code in PAD_BUTTONS.items():
			v = 1 if name in buttons else 0
			if self.sent.get(code) != v:
				self.ui.write(e.EV_KEY, code, v)
				self.sent[code] = v
				changed = True
		for axis, code in AXIS_CODES.items():
			v = int(max(-1.0, min(1.0, sticks.get(axis, 0.0))) * 32767)
			if self.sent.get(("a", code)) != v:
				self.ui.write(e.EV_ABS, code, v)
				self.sent[("a", code)] = v
				changed = True
		for name, code in TRIGGERS.items():
			v = 255 if name in triggers else 0
			if self.sent.get(("a", code)) != v:
				self.ui.write(e.EV_ABS, code, v)
				self.sent[("a", code)] = v
				changed = True
		if changed:
			self.ui.syn()

	def release(self):
		self.apply(set(), {}, set())

# ----------------------------------------------------------------- mouse -----

class MouseStick:
	"""Mouse velocity -> right stick, with smoothing and anti-deadzone."""

	def __init__(self, cfg):
		self.sens = cfg.get("sensitivity", 1.0)          # stick per 1000 px/s
		self.smooth_ms = cfg.get("smoothing_ms", 14)     # EMA time constant
		self.curve = cfg.get("curve", 0.85)              # <1 boosts small motions
		self.anti_dz = cfg.get("anti_deadzone", 0.22)    # game deadzone to jump over
		self.invert_y = cfg.get("invert_y", False)
		self.y_ratio = cfg.get("y_ratio", 1.0)
		self.dx = self.dy = 0.0
		self.vx = self.vy = 0.0

	def move(self, code, value):
		if code == e.REL_X:
			self.dx += value
		elif code == e.REL_Y:
			self.dy += value

	def reset(self):
		self.dx = self.dy = self.vx = self.vy = 0.0

	def tick(self, dt):
		ix, iy = self.dx / dt, self.dy / dt   # px/s
		self.dx = self.dy = 0.0
		a = pow(0.5, dt * 1000.0 / max(1.0, self.smooth_ms))
		self.vx = self.vx * a + ix * (1 - a)
		self.vy = self.vy * a + iy * (1 - a)
		return self._shape(self.vx), self._shape(self.vy * self.y_ratio * (-1 if self.invert_y else 1))

	def _shape(self, v):
		s = v * self.sens / 1000.0
		m = abs(s)
		if m < 0.01:
			return 0.0
		m = min(1.0, m) ** self.curve
		m = self.anti_dz + (1 - self.anti_dz) * m
		return min(1.0, m) * (1 if s > 0 else -1)

# --------------------------------------------------------------- profile -----

def code_of(name):
	c = e.ecodes.get(name)
	if c is None:
		raise ValueError(f"unknown key name {name!r} (use evdev names like KEY_W, BTN_LEFT, WHEEL_UP)")
	return c


WHEEL_UP, WHEEL_DOWN = "WHEEL_UP", "WHEEL_DOWN"


class Profile:
	def __init__(self, path):
		with open(path, encoding="utf-8") as f:
			raw = json.load(f)
		self.name = raw.get("name", os.path.basename(path))
		self.mouse = raw.get("mouse", {})
		self.turbo_hz = raw.get("turbo_hz", 8)
		self.start_mode = raw.get("start_mode", "foot")
		self.toggle_key = code_of(raw.get("pause_key", "KEY_F8"))
		self.modes = {}
		for mode, binds in raw["modes"].items():
			table = {}
			for key, actions in binds.items():
				if key.startswith("_"):
					continue
				if isinstance(actions, str):
					actions = [actions]
				table[key if key in (WHEEL_UP, WHEEL_DOWN) else code_of(key)] = actions
			self.modes[mode] = table
		self.mode_names = raw.get("mode_names", {})
		self.global_binds = {code_of(k): (v if isinstance(v, list) else [v])
			for k, v in raw.get("global", {}).items() if not k.startswith("_")}

# ---------------------------------------------------------------- engine -----

def notify(text):
	try:
		subprocess.Popen(["notify-send", "-a", APP, "-t", "1500", "-i", "input-gaming", "PS5", text],
			stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
	except FileNotFoundError:
		pass
	print(text, flush=True)


class Engine:
	TICK = 0.004  # 250 Hz

	def __init__(self, profile, verbose=False):
		self.p = profile
		self.verbose = verbose
		self.pad = Pad()
		self.passthrough = evdev.UInput(name=VIRTUAL_KBD_NAME)
		self.mouse = MouseStick(profile.mouse)
		self.mode = profile.start_mode
		self.held = set()          # physical codes currently held
		self.wheel_until = {}      # WHEEL_UP/DOWN -> release time
		self.forwarding = set()    # keys forwarded to the desktop while grabbed
		self.focus_chiaki = False
		self.paused = False
		self.grabbed = False
		self.devices = {}
		self.sel = selectors.DefaultSelector()
		self.lock = threading.Lock()
		self.pending_focus = None
		self.last_scan = 0.0

	# ----- devices -----

	def scan(self):
		for path in evdev.list_devices():
			if path in self.devices:
				continue
			try:
				d = evdev.InputDevice(path)
			except OSError:
				continue
			if d.name in (VIRTUAL_NAME, VIRTUAL_KBD_NAME) or d.name.startswith("input-remapper"):
				d.close()
				continue
			caps = d.capabilities()
			keys = set(caps.get(e.EV_KEY, []))
			rels = set(caps.get(e.EV_REL, []))
			is_kbd = e.KEY_A in keys and e.KEY_SPACE in keys
			is_mouse = e.REL_X in rels and e.BTN_LEFT in keys
			if not (is_kbd or is_mouse):
				d.close()
				continue
			self.devices[path] = d
			self.sel.register(d, selectors.EVENT_READ)
			if self.grabbed:
				self._grab(d)
			if self.verbose:
				print(f"using {path}: {d.name} ({'kbd' if is_kbd else ''}{' mouse' if is_mouse else ''})", flush=True)

	def drop(self, path):
		d = self.devices.pop(path, None)
		if d:
			try:
				self.sel.unregister(d)
			except Exception:
				pass
			d.close()

	def _grab(self, d):
		try:
			d.grab()
		except OSError:
			pass

	def set_grab(self, on):
		if on == self.grabbed:
			return
		self.grabbed = on
		for d in list(self.devices.values()):
			try:
				d.grab() if on else d.ungrab()
			except OSError:
				pass
		self.held.clear()
		self.mouse.reset()
		self._release_forwarded()
		self.pad.release()
		notify(f"Управление PS5: ВКЛ ({self.p.mode_names.get(self.mode, self.mode)})" if on
			else "Управление PS5: выкл")

	def update_grab(self):
		self.set_grab(self.focus_chiaki and not self.paused)

	# ----- passthrough for Alt/Super combos so Alt+Tab still works -----

	PASS_MODS = {e.KEY_LEFTALT, e.KEY_RIGHTALT, e.KEY_LEFTMETA, e.KEY_RIGHTMETA}

	def _forward(self, code, value):
		self.passthrough.write(e.EV_KEY, code, value)
		self.passthrough.syn()
		if value:
			self.forwarding.add(code)
		else:
			self.forwarding.discard(code)

	def _release_forwarded(self):
		for c in list(self.forwarding):
			self._forward(c, 0)

	# ----- events -----

	def on_key(self, code, value):
		if value == 2:  # autorepeat
			return
		if code == self.p.toggle_key and value == 1:
			self.paused = not self.paused
			if self.focus_chiaki:
				self.update_grab()
			return
		if not self.grabbed:
			return
		if code in self.PASS_MODS or (self.forwarding & self.PASS_MODS) or code in self.forwarding:
			if code in self.PASS_MODS or value == 1 or code in self.forwarding:
				self._forward(code, value)
				return
		if value:
			self.held.add(code)
			self.run_instant(code)
		else:
			self.held.discard(code)

	def run_instant(self, code):
		"""Mode switches fire on press."""
		for action in self.binds().get(code, []) + self.p.global_binds.get(code, []):
			if action.startswith("mode:"):
				target = action[5:]
				names = list(self.p.modes)
				if target == "toggle":
					target = names[(names.index(self.mode) + 1) % len(names)]
				if target in self.p.modes and target != self.mode:
					self.mode = target
					# keys held across the switch should not leak into the new mode
					self.held = {c for c in self.held if c == code}
					notify(self.p.mode_names.get(target, target))

	def binds(self):
		return self.p.modes[self.mode]

	def on_wheel(self, value):
		k = WHEEL_UP if value > 0 else WHEEL_DOWN
		self.wheel_until[k] = time.monotonic() + 0.09

	# ----- state -----

	def compute(self, now, mouse_xy):
		buttons, triggers = set(), set()
		sticks = {"lx": 0.0, "ly": 0.0, "rx": 0.0, "ry": 0.0}
		active = list(self.held) + [k for k, t in self.wheel_until.items() if t > now]
		turbo_on = int(now * self.p.turbo_hz * 2) % 2 == 0
		walk = 1.0
		table = self.binds()
		for code in active:
			for action in table.get(code, []) + self.p.global_binds.get(code, []):
				if action.startswith("mode:"):
					continue
				if action == "WALK":
					walk = 0.45
					continue
				turbo = action.endswith("@turbo")
				name = action[:-6] if turbo else action
				if turbo and not turbo_on:
					continue
				if name in PAD_BUTTONS:
					buttons.add(name)
				elif name in TRIGGERS:
					triggers.add(name)
				elif name in STICK_DIRS:
					axis, sign = STICK_DIRS[name]
					sticks[axis] += sign
		# normalize keyboard diagonals
		for x, y in (("lx", "ly"), ("rx", "ry")):
			m = (sticks[x] ** 2 + sticks[y] ** 2) ** 0.5
			if m > 1:
				sticks[x] /= m
				sticks[y] /= m
		sticks["lx"] *= walk
		sticks["ly"] *= walk
		mx, my = mouse_xy
		if abs(mx) > abs(sticks["rx"]):
			sticks["rx"] = mx
		if abs(my) > abs(sticks["ry"]):
			sticks["ry"] = my
		return buttons, sticks, triggers

	# ----- main loop -----

	def set_focus(self, info):
		with self.lock:
			self.pending_focus = info

	def run(self):
		self.scan()
		next_tick = time.monotonic()
		while True:
			with self.lock:
				info, self.pending_focus = self.pending_focus, None
			if info is not None:
				focused = "chiaki" in info.lower()
				if focused != self.focus_chiaki:
					self.focus_chiaki = focused
					self.paused = False
					self.update_grab()

			timeout = max(0.0, next_tick - time.monotonic())
			for key, _ in self.sel.select(timeout):
				d = key.fileobj
				try:
					for ev in d.read():
						if ev.type == e.EV_KEY:
							self.on_key(ev.code, ev.value)
						elif ev.type == e.EV_REL and self.grabbed:
							if ev.code in (e.REL_X, e.REL_Y):
								self.mouse.move(ev.code, ev.value)
							elif ev.code == e.REL_WHEEL:
								self.on_wheel(ev.value)
				except OSError:
					self.drop(d.path)

			now = time.monotonic()
			if now >= next_tick:
				next_tick = now + self.TICK
				if self.grabbed:
					self.pad.apply(*self.compute(now, self.mouse.tick(self.TICK)))
				if now - self.last_scan > 2.0:
					self.last_scan = now
					self.scan()

# ------------------------------------------------------------------ dbus -----

def start_dbus(engine):
	try:
		import dbus
		import dbus.service
		from dbus.mainloop.glib import DBusGMainLoop
		from gi.repository import GLib
	except ImportError:
		print("dbus-python/PyGObject missing: auto-activation disabled, use the pause key", file=sys.stderr)
		return

	DBusGMainLoop(set_as_default=True)
	bus = dbus.SessionBus()

	class Service(dbus.service.Object):
		@dbus.service.method("io.github.chiakikbm", in_signature="s")
		def SetFocus(self, info):
			engine.set_focus(str(info))

	name = dbus.service.BusName("io.github.chiakikbm", bus)
	Service(bus, "/")
	loop = GLib.MainLoop()
	t = threading.Thread(target=loop.run, daemon=True)
	t.start()
	t._keep = (name,)

# ------------------------------------------------------------------ main -----

def main():
	here = os.path.dirname(os.path.abspath(__file__))
	ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	ap.add_argument("--profile", default=os.path.join(here, "profiles", "gta.json"))
	ap.add_argument("--always-on", action="store_true", help="grab immediately, ignore window focus")
	ap.add_argument("--print-sdl-mapping", action="store_true")
	ap.add_argument("-v", "--verbose", action="store_true")
	args = ap.parse_args()

	if args.print_sdl_mapping:
		print(SDL_MAPPING)
		return

	try:
		engine = Engine(Profile(args.profile), verbose=args.verbose)
	except PermissionError:
		sys.exit("No access to /dev/input or /dev/uinput. Run install.sh, then log out and back in.")
	print(f"{APP}: profile '{engine.p.name}', pause key {e.KEY[engine.p.toggle_key]}", flush=True)
	start_dbus(engine)
	if args.always_on:
		engine.set_focus("chiaki")
	try:
		engine.run()
	except KeyboardInterrupt:
		pass
	finally:
		engine.set_grab(False)


if __name__ == "__main__":
	main()
