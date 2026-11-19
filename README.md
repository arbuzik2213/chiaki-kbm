# chiaki-kbm

Клавиатура и мышь для PS5 Remote Play на Linux через [chiaki-ng](https://github.com/streetpea/chiaki-ng). Есть готовый профиль для GTA.
*Keyboard & mouse for PS5 Remote Play on Linux (chiaki-ng), with a ready GTA profile. English below.*

> **Бета.** Сделано для Fedora 44 + KDE Plasma 6 (Wayland). Кнопки GTA 6 взяты из опубликованных гайдов по управлению на PS5; если что-то не совпадает, поправь `profiles/gta.json` или открой issue.

## Что умеет
- **Включается по F8** в окне chiaki-ng (уже в игре). Сама мышь никогда не захватывается. Вернуть обычную мышь: **F8**, **Ctrl+Esc** или Alt+Tab в другое окно.
- **Мышь управляет камерой и прицелом** со сглаживанием и «перепрыгиванием» мёртвой зоны игры, поэтому без рывков.
- **Режимы «пешком» и «в машине»**: в машине W — газ (R2), S — тормоз (L2), Space — ручник. Режим переключается сам на F (сесть/выйти), вручную — на F2.
- **Бег на Shift**: быстро «тапает» ✕, как нужно в GTA.
- **Раскладка не важна** (ua/ru/en): клавиши читаются по физическому положению.

## Установка
1. Установи chiaki-ng и подключи PS5 (Flathub: `io.github.streetpea.Chiaki4deck`).
2. Установи chiaki-kbm:
   ```bash
   git clone https://github.com/arbuzik2213/chiaki-kbm
   cd chiaki-kbm
   ./install.sh
   ```
3. **Выйди из системы и зайди снова** (один раз, чтобы применилась группа `input`).
4. Запусти chiaki-ng, подключись к PS5, кликни в окно стрима и нажми **F8**.

Удаление: `./uninstall.sh`.

## Управление: клавиши как в GTA 5 на ПК → GTA 6 на PS5
Профиль `gta.json` рассчитан на схему управления GTA 6 **«Стандартная» (Default)**: бег на L3, прыжок на ✕.
Если в настройках игры выбрана **«Классическая» (Classic)**, используй `gta6-classic.json` (см. «Настройка»).

### Везде
| Клавиша | PS5 | GTA 6 |
|---|---|---|
| Esc / P | Options | Пауза |
| M | Тачпад | Карта |
| ↑ | Крестовина ↑ | Телефон |
| ↓ / Z | Крестовина ↓ | Задание / миникарта |
| ← → | Крестовина ← → | Радио; в машине поворотники |
| Enter / Backspace | ✕ / ○ | Выбрать / назад в меню |
| Home | PS | Меню PS5 |
| F2 | — | Сменить режим пешком/машина вручную |
| F8 | — | Включить / выключить управление |
| Ctrl+Esc | — | Аварийно вернуть мышь и клавиатуру |

### Пешком
| Клавиша / мышь | PS5 | GTA 6 |
|---|---|---|
| W A S D | Левый стик | Ходьба |
| Мышь | Правый стик | Камера / прицел |
| Shift | L3 ×2 | Бег → спринт |
| Caps Lock (зажать) | — | Медленный шаг |
| Space | ✕ | Прыжок / залезть |
| Ctrl | ○ | Присесть |
| R, боковая кнопка «назад» | □ | Ближний бой |
| E, боковая кнопка «вперёд» | △ | Взаимодействие |
| F | △ | Сесть в машину → режим «в машине» |
| ЛКМ | R2 | Стрелять |
| ПКМ | L2 | Целиться |
| Q | R1 | Укрытие |
| Tab | L1 | Убрать оружие |
| C, средняя кнопка | R3 | Посмотреть назад |
| G | Крестовина → | Взорвать заряд |
| . (точка) | Крестовина ← | Радио |

### В машине
| Клавиша / мышь | PS5 | GTA 6 |
|---|---|---|
| W | R2 | Газ |
| S | L2 | Тормоз / назад |
| A D | Левый стик | Руль |
| Space | ✕ | Ручник |
| E / Shift | L3 | Сигнал / нитро |
| ЛКМ | R1 | Стрелять |
| H | ○ | Фары |
| F | △ | Выйти → режим «пешком» |
| C, средняя кнопка | R3 | Смотреть назад |
| R | □ | Ближний бой |
| Мышь | Правый стик | Камера |

Если режим сбился (нажал F, а машины рядом не было), нажми **F2**.
Взаимодействие с людьми и предметами делай на **E**, а не на F: F ещё и переключает режим.

## Настройка
Профиль: `~/.local/share/chiaki-kbm/profiles/gta.json`. После правки выполни `systemctl --user restart chiaki-kbm`.

- Действия: `CROSS CIRCLE SQUARE TRIANGLE L1 R1 L2 R2 L3 R3 OPTIONS SHARE PS TOUCHPAD DPAD_UP/DOWN/LEFT/RIGHT LS_UP/DOWN/LEFT/RIGHT RS_UP/DOWN/LEFT/RIGHT WALK mode:foot mode:vehicle mode:toggle`
- `@turbo` после кнопки — авто-тап (например `CROSS@turbo`), частота `turbo_hz`.
- Клавиши — имена evdev: `KEY_W`, `KEY_LEFTSHIFT`, `BTN_LEFT`, `BTN_SIDE`, `WHEEL_UP`…
- Мышь: `sensitivity` — скорость, `smoothing_ms` — плавность (больше = плавнее, но с задержкой), `anti_deadzone` — увеличь, если мелкие движения не доходят до игры, `invert_y`.

Классическая схема GTA 6: в `~/.config/systemd/user/chiaki-kbm.service` допиши в ExecStart `--profile %h/.local/share/chiaki-kbm/profiles/gta6-classic.json`, затем `systemctl --user daemon-reload && systemctl --user restart chiaki-kbm`.

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
