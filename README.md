# chiaki-kbm

Клавиатура и мышь для PS5 Remote Play на Linux через [chiaki-ng](https://github.com/streetpea/chiaki-ng). Есть готовый профиль для GTA.
*Keyboard & mouse for PS5 Remote Play on Linux (chiaki-ng), with a ready GTA profile. English below.*

> **Бета.** Проверено на Fedora 44 + KDE Plasma 6 (Wayland). Профиль GTA сделан по схеме управления GTA V на PS5: если в GTA 6 какое-то действие на другой кнопке, поправь `profiles/gta.json`.

## Что умеет
- **Включается само**, когда активно окно chiaki-ng, и отключается по Alt+Tab. Ничего не надо нажимать вручную.
- **Мышь управляет камерой и прицелом** со сглаживанием и «перепрыгиванием» мёртвой зоны игры, поэтому без рывков.
- **Режимы «пешком» и «в машине»**: в машине W — газ (R2), S — тормоз (L2), Space — ручник. Режим переключается сам на F (сесть/выйти), вручную — на F2.
- **Бег на Shift**: быстро «тапает» ✕, как нужно в GTA.
- **Раскладка не важна** (ua/ru/en): клавиши читаются по физическому положению.
- **F8** — пауза: временно вернуть обычную мышь.

## Установка
1. Установи chiaki-ng и подключи PS5 (Flathub: `io.github.streetpea.Chiaki4deck`).
2. Установи chiaki-kbm:
   ```bash
   git clone https://github.com/arbuzik2213/chiaki-kbm
   cd chiaki-kbm
   ./install.sh
   ```
3. **Выйди из системы и зайди снова** (один раз, чтобы применилась группа `input`).
4. Запусти chiaki-ng, подключись к PS5 и играй.

Удаление: `./uninstall.sh`.

## Управление (профиль GTA)

### Везде
| Клавиша | PS5 | | Клавиша | PS5 |
|---|---|---|---|---|
| Esc | Options (пауза/карта) | | V | Тачпад (вид камеры) |
| Enter | ✕ (меню) | | Backspace | ○ (назад в меню) |
| Стрелки / 1–4 | Крестовина (↑ телефон) | | Home | PS |
| F2 | сменить режим вручную | | F8 | пауза chiaki-kbm |

### Пешком
| Клавиша / мышь | PS5 | Действие в GTA |
|---|---|---|
| W A S D | Левый стик | Ходьба |
| Мышь | Правый стик | Камера / прицел |
| ЛКМ | R2 | Стрелять / атаковать |
| ПКМ | L2 | Целиться |
| Shift | ✕ (авто-тап) | Бег |
| Caps Lock (зажать) | — | Медленный шаг |
| Space | □ | Прыжок |
| R | ○ | Перезарядка / удар |
| F | △ | Сесть в машину → режим «в машине» |
| E | Крестовина → | Действие / подобрать |
| Q | R1 | Укрытие |
| Tab | L1 | Колесо оружия (выбирать мышью) |
| Ctrl | L3 | Присесть / скрытность |
| C, средняя кнопка | R3 | Правый стик (вид) |
| Колесо мыши | Крестовина ← / → | |
| Боковые кнопки мыши | ○ / △ | Удар / действие |

### В машине
| Клавиша / мышь | PS5 | Действие в GTA |
|---|---|---|
| W | R2 | Газ |
| S | L2 | Тормоз / назад |
| A D | Левый стик | Руль |
| Space | R1 | Ручник |
| Shift | ✕ | |
| F | △ | Выйти → режим «пешком» |
| ЛКМ | L1 | Стрельба из машины |
| ПКМ / C | R3 | Смотреть назад |
| E / средняя кнопка | L3 | Сигнал |
| Q / H | Крестовина ← / → | Радио / действие |
| Мышь | Правый стик | Камера |

Если F не сработал (машины рядом не было) и режим сбился, нажми **F2**.

## Настройка
Профиль: `~/.local/share/chiaki-kbm/profiles/gta.json`. После правки выполни `systemctl --user restart chiaki-kbm`.

- Действия: `CROSS CIRCLE SQUARE TRIANGLE L1 R1 L2 R2 L3 R3 OPTIONS SHARE PS TOUCHPAD DPAD_UP/DOWN/LEFT/RIGHT LS_UP/DOWN/LEFT/RIGHT RS_UP/DOWN/LEFT/RIGHT WALK mode:foot mode:vehicle mode:toggle`
- `@turbo` после кнопки — авто-тап (например `CROSS@turbo`), частота `turbo_hz`.
- Клавиши — имена evdev: `KEY_W`, `KEY_LEFTSHIFT`, `BTN_LEFT`, `BTN_SIDE`, `WHEEL_UP`…
- Мышь: `sensitivity` — скорость, `smoothing_ms` — плавность (больше = плавнее, но с задержкой), `anti_deadzone` — увеличь, если мелкие движения не доходят до игры, `invert_y`.

Профиль для другой игры: скопируй `gta.json` и запусти `chiaki_kbm.py --profile путь.json`.

## Как это работает
chiaki-kbm читает клавиатуру и мышь через evdev и создаёт виртуальный геймпад (uinput). chiaki-ng видит его как обычный контроллер: `install.sh` передаёт ему раскладку кнопок через `SDL_GAMECONTROLLERCONFIG`. Небольшой скрипт KWin сообщает, какое окно активно, и пока это chiaki-ng, клавиатура и мышь захватываются. Alt и Super всегда проходят в систему, поэтому Alt+Tab работает.

Не на KDE: добавь `--always-on` в `~/.config/systemd/user/chiaki-kbm.service` и переключай на F8.

## Проблемы
- **Не реагирует:** `journalctl --user -u chiaki-kbm -f` — смотри ошибки; проверь, что выполнил выход/вход после установки.
- **Камера дёргается:** понизь частоту опроса мыши до 250–500 Гц или увеличь `smoothing_ms`.
- **Нажатия двоятся:** выключи раскладку клавиатуры в настройках chiaki-ng и остановленный Input Remapper.

---

## English
chiaki-kbm turns your keyboard and mouse into a virtual gamepad for chiaki-ng (PS5/PS4 Remote Play) on Linux. It auto-activates while the chiaki-ng window is focused (KDE Plasma 6 via a KWin script), offers smooth mouse aim, on-foot/vehicle modes (W = R2 throttle, S = L2 brake in vehicles), Shift sprint with auto-tap, and is layout-independent. Install with `./install.sh`, then log out and back in once. Profiles are JSON (`profiles/gta.json`).

Not affiliated with Sony Interactive Entertainment or Rockstar Games. MIT license.
