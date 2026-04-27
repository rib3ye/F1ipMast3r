# F1ipMast3r

A Cursor / Claude Agent skill that turns the AI into a curious, mischievous, gaming-obsessed Flipper Zero engineering expert.

The skill teaches the agent:

- The full hardware surface of the Flipper Zero (STM32WB55, CC1101 Sub-GHz, ST25R3916 NFC, 125 kHz LF RFID, 1-Wire iButton, IR, GPIO, BLE, microSD).
- The Wi-Fi Developer Board (ESP32-S2 Black Magic Probe / CMSIS-DAP for GDB over Wi-Fi or USB).
- The Video Game Module (RP2040, DVI-D 640×480 over HDMI, ICM-42688-P 6-axis IMU, Pico SDK).
- All radio protocols Flipper natively decodes — Sub-GHz vendor list (Princeton, CAME, Nice, KeeLoq family, …), NFC tag taxonomy (MIFARE Classic / Ultralight / DESFire / NTAG / FeliCa / ISO15693), 125 kHz LF (EM4100, HID, Indala, T5577 as universal blank), iButton (Dallas, Cyfral, Metakom), Infrared (NEC, RC5/6, SIRC, Pronto).
- The native development surface — `ufbt` build tool, `application.fam` manifest, Furi HAL/GUI/ViewDispatcher/SceneManager, threading rules, drawing on the 128×64 canvas, audio via the speaker, Storage, NotificationService.
- The JavaScript surface — mJS engine and every `require()` module (`event_loop`, `gui`, `gpio`, `subghz`, `badusb`, `serial`, `storage`, `notification`, `usbdisk`, `keyboard`, `math`, `flipper`, `blebeacon`).
- Host-side tooling — USB CDC CLI, RPC protobuf protocol, `pyflipper`, BadUSB Rubber Ducky DSL with full key set, U2F as a second factor.
- A clear ethical line: green-light playgrounds (your own gear, CTFs, authorized pentests, hobby RX) versus the hard "no" list (rolling-code car cloning, secure HID badges, EMV, region TX-block bypasses).

## Persona

The agent answers as a curious, slightly silly dolphin-shaped engineer. It loves building tiny games, poking at the invisible world of radio waves, and convincing dumb electronics to do new tricks. It writes real code, names protocols precisely, respects hardware limits, and refuses to help with fraud, impersonation, or transmitting on prohibited bands.

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

| File | Contents |
| --- | --- |
| [SKILL.md](SKILL.md) | Persona, hardware cheatsheet, triage table, file-format map, hard limits |
| [radio.md](radio.md) | Sub-GHz / NFC / 125 kHz LF / iButton / Infrared protocol reference |
| [fap-development.md](fap-development.md) | Native FAPs in C — ufbt, manifest, Furi, GUI, drawing, audio, games, GDB via Wi-Fi Devboard |
| [javascript.md](javascript.md) | mJS engine and every `require()` module |
| [video-game-module.md](video-game-module.md) | RP2040 / DVI-D / IMU dev, Pico SDK, host-FAP ↔ VGM bridge, IMU game patterns |
| [host-side.md](host-side.md) | USB CDC CLI, RPC protobuf, `pyflipper`, BadUSB Ducky DSL, U2F |
| [opsec-and-limits.md](opsec-and-limits.md) | Ethics, refusal rules, region TX table, legitimate research framing |

## Hardware assumed

The skill assumes you own:

- A Flipper Zero (any firmware: official, Momentum, Unleashed, RogueMaster, Xtreme).
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

Please keep [opsec-and-limits.md](opsec-and-limits.md) intact when forking — the persona's value depends on the line being clearly drawn.

## License

MIT — see [LICENSE](LICENSE).

The Flipper Zero name and dolphin mascot are trademarks of Flipper Devices Inc. This is a community-authored skill, not an official project.
