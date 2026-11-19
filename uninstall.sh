#!/bin/bash
systemctl --user disable --now chiaki-kbm.service 2>/dev/null
rm -f "$HOME/.config/systemd/user/chiaki-kbm.service"
rm -rf "$HOME/.local/share/chiaki-kbm"
kpackagetool6 --type=KWin/Script -r chiakikbm 2>/dev/null
kwriteconfig6 --file kwinrc --group Plugins --key chiakikbmEnabled --delete 2>/dev/null
flatpak override --user --unset-env=SDL_GAMECONTROLLERCONFIG io.github.streetpea.Chiaki4deck 2>/dev/null
echo "Removed. (udev rule /etc/udev/rules.d/99-chiaki-kbm.rules and 'input' group membership left in place)"
