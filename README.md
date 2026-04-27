# F1ipMast3r

> Last verified against OFW 1.4.x / SDK API ~86 · Momentum dev-rolling (April 2026). Firmware moves fast; if you're seeing API mismatch errors, run `ufbt update` against your fork's index.

A Cursor / Claude Agent skill that turns the AI into a curious, mischievous, gaming-obsessed Flipper Zero engineering expert — equally at home building tiny games and running an offensive-security engagement.

The skill teaches the agent:

- The full hardware surface of the Flipper Zero (STM32WB55, CC1101 Sub-GHz, ST25R3916 NFC, 125 kHz LF RFID, 1-Wire iButton, IR, GPIO, BLE, microSD).
- The Wi-Fi Developer Board (ESP32-S2 Black Magic Probe / CMSIS-DAP for GDB over Wi-Fi or USB).
- The Video Game Module (RP2040, DVI-D 640×480 over HDMI, ICM-42688-P 6-axis IMU, Pico SDK).
- All radio protocols Flipper natively decodes — Sub-GHz vendor list (Princeton, CAME, Nice, KeeLoq family, …), NFC tag taxonomy (MIFARE Classic / Ultralight / DESFire / NTAG / FeliCa / ISO15693), 125 kHz LF (EM4100, HID, Indala, T5577 as universal blank), iButton (Dallas, Cyfral, Metakom), Infrared (NEC, RC5/6, SIRC, Pronto).
- The native development surface — `ufbt` build tool, `application.fam` manifest, Furi HAL/GUI/ViewDispatcher/SceneManager, threading rules, drawing on the 128×64 canvas, audio via the speaker, Storage, NotificationService.
- The JavaScript surface — mJS engine and every `require()` module (`event_loop`, `gui`, `gpio`, `subghz`, `badusb`, `serial`, `storage`, `notification`, `usbdisk`, `keyboard`, `math`, `flipper`, `blebeacon`).
- Host-side tooling — USB CDC CLI, RPC protobuf protocol, `pyflipper`, BadUSB Rubber Ducky DSL with full key set, U2F as a second factor.
- The hardware/protocol limits that actually matter — region TX blocks (firmware-level), rolling-code replay vs synced receivers, secure-element NFC ciphers (DESFire AES, iCLASS SEOS, EMV), RAM/flash budgets for FAPs, CC1101 packet engine vs async, VGM video and IMU constraints.

## Persona

The agent answers as a curious, slightly silly dolphin-shaped engineer. It loves building tiny games, poking at the invisible world of radio waves, and convincing dumb electronics to do new tricks. It writes real code, names protocols precisely, knows the hardware limits cold, and ships the technical answer instead of hand-waving.

## Install

### As a Cursor personal skill

```bash
git clone https://github.com/rib3ye/F1ipMast3r ~/Documents/Projects/F1ipMast3r
mkdir -p ~/.cursor/skills
ln -sfn ~/Documents/Projects/F1ipMast3r ~/.cursor/skills/flipper-zero-dev
```

The skill activates automatically whenever you talk to a Cursor agent about anything Flipper-related (FAP, ufbt, Sub-GHz, NFC, KeeLoq, BadUSB, mJS, Video Game Module, etc.).

### As a Claude Code skill

```bash
git clone https://github.com/rib3ye/F1ipMast3r ~/.claude/skills/flipper-zero-dev
```

### As a project skill

```bash
cd your-flipper-project
git submodule add https://github.com/rib3ye/F1ipMast3r .cursor/skills/flipper-zero-dev
```

Anyone who clones the project then gets the skill bundled with the repo.

## Files

The canonical file index with per-file summaries lives in [SKILL.md](SKILL.md) → "Reference index". At a glance:

- [SKILL.md](SKILL.md) — persona, hardware cheatsheet, triage table, file-format map.
- [fap-development.md](fap-development.md) — native FAPs in C.
- [javascript.md](javascript.md) — mJS scripting.
- [radio.md](radio.md) — Sub-GHz / NFC / LF RFID / iButton / IR.
- [host-side.md](host-side.md) — CLI / RPC / BadUSB / BadKB / U2F.
- [wifi-devboard.md](wifi-devboard.md) — ESP32-S2 debugger and Wi-Fi attack platform.
- [video-game-module.md](video-game-module.md) — RP2040 / DVI-D / IMU.
- [apps-and-modules.md](apps-and-modules.md) — Apps Catalog and GPIO add-on ecosystem.
- [limits.md](limits.md) — what won't work and why.

## Hardware assumed

The skill assumes you own:

- A Flipper Zero (any firmware: OFW, Momentum, Unleashed, RogueMaster; Xtreme builds folded into Momentum in 2024).
- The Wi-Fi Developer Board (ESP32-S2 with Black Magic Probe firmware).
- The Video Game Module (RP2040 + DVI-D + ICM-42688-P).
- A reasonably-sized microSD (FAT32 or exFAT).

The skill still works without the modules — it just won't push you toward features you can't use.

## Contributing

Pull requests welcome, especially for:

- Firmware fork parity tables that have drifted (`javascript.md`).
- New Sub-GHz protocols or NFC tag families that the firmware now supports (`radio.md`).
- New `gui/*` JS submodules (`javascript.md`).
- More IMU game patterns or Pico SDK tips (`video-game-module.md`).
- Updated hardware/protocol limits when firmware or hardware changes (`limits.md`).

## License

MIT — see [LICENSE](LICENSE).

The Flipper Zero name and dolphin mascot are trademarks of Flipper Devices Inc. This is a community-authored skill, not an official project.
