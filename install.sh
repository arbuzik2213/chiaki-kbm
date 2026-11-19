#!/bin/bash
# chiaki-kbm installer (Fedora / Ubuntu / Arch, KDE Plasma 6 for auto-activation)
set -e
cd "$(dirname "$0")"
DEST="$HOME/.local/share/chiaki-kbm"
FLATPAK_ID="io.github.streetpea.Chiaki4deck"

echo "==> Python dependencies"
if ! python3 -c "import evdev, dbus, gi" 2>/dev/null; then
    if command -v dnf >/dev/null; then sudo dnf install -y python3-evdev python3-dbus python3-gobject
    elif command -v apt >/dev/null; then sudo apt install -y python3-evdev python3-dbus python3-gi
    elif command -v pacman >/dev/null; then sudo pacman -S --needed python-evdev python-dbus python-gobject
    else echo "Install python evdev, dbus-python and PyGObject manually"; exit 1; fi
fi

echo "==> Access to keyboard/mouse and virtual gamepad (needs sudo once)"
echo 'KERNEL=="uinput", GROUP="input", MODE="0660", OPTIONS+="static_node=uinput"' \
    | sudo tee /etc/udev/rules.d/99-chiaki-kbm.rules >/dev/null
echo uinput | sudo tee /etc/modules-load.d/chiaki-kbm.conf >/dev/null
sudo modprobe uinput
sudo udevadm control --reload-rules
sudo udevadm trigger --name-match=uinput || true
NEED_RELOGIN=0
if ! id -nG "$USER" | grep -qw input; then
    sudo usermod -aG input "$USER"
    NEED_RELOGIN=1
fi

echo "==> Files"
mkdir -p "$DEST/profiles"
cp chiaki_kbm.py "$DEST/"
[ -f "$DEST/profiles/gta.json" ] && cp "$DEST/profiles/gta.json" "$DEST/profiles/gta.json.bak"
cp profiles/*.json "$DEST/profiles/"

echo "==> Autostart"
mkdir -p "$HOME/.config/systemd/user"
cp chiaki-kbm.service "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable chiaki-kbm.service

echo "==> KWin focus script (auto on/off when chiaki-ng is focused)"
if command -v kpackagetool6 >/dev/null; then
    kpackagetool6 --type=KWin/Script -i kwin >/dev/null 2>&1 || kpackagetool6 --type=KWin/Script -u kwin >/dev/null
    kwriteconfig6 --file kwinrc --group Plugins --key chiakikbmEnabled true
    (qdbus6 org.kde.KWin /KWin reconfigure || qdbus org.kde.KWin /KWin reconfigure) >/dev/null 2>&1 || true
else
    echo "   Not KDE Plasma: no auto-activation. Edit the service to add --always-on and use F8 to pause."
fi

echo "==> Tell chiaki-ng (SDL) the button layout of the virtual gamepad"
MAPPING="$(python3 chiaki_kbm.py --print-sdl-mapping)"
if command -v flatpak >/dev/null && flatpak info "$FLATPAK_ID" >/dev/null 2>&1; then
    flatpak override --user --env=SDL_GAMECONTROLLERCONFIG="$MAPPING" "$FLATPAK_ID"
else
    echo "   chiaki-ng flatpak not found. For a native build, export before starting chiaki:"
    echo "   export SDL_GAMECONTROLLERCONFIG='$MAPPING'"
fi

if [ "$NEED_RELOGIN" = 1 ]; then
    echo
    echo "Done. LOG OUT AND LOG BACK IN once (new 'input' group), chiaki-kbm then starts by itself."
else
    systemctl --user restart chiaki-kbm.service
    echo
    echo "Done. chiaki-kbm is running. Focus the chiaki-ng window to play."
fi
