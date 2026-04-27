# Apps Catalog, community repos, and GPIO add-ons

The first question for any "I want the Flipper to do X" task is **"is there already a FAP for that?"** Most of the time the answer is yes. This file is the index.

## Apps Catalog (`lab.flipper.net`)

The official store: [https://lab.flipper.net](https://lab.flipper.net) (also reachable as the **Apps** tab in qFlipper and the Flipper Mobile App). 600+ vetted FAPs, browsable by category, installable in one click over USB or BLE.

Always check the catalog before writing a new FAP. Categories that map to the SD-card layout:

| Catalog category | SD path | Examples |
| --- | --- | --- |
| Sub-GHz | `apps/Sub-GHz/` | Frequency Analyzer extensions, TPMS readers, SubBrute |
| NFC | `apps/NFC/` | NFC Magic, Mifare Fuzzer, PicoPass, Seader, Amiibomb |
| RFID | `apps/RFID/` | LF-RFID Fuzzer, Hitag2 readers |
| Infrared | `apps/Infrared/` | TV-B-Gone, AC remotes, IR scope |
| iButton | `apps/iButton/` | iButton Fuzzer |
| Bluetooth | `apps/Bluetooth/` | BLE Spam, BLE Beacon, BLE Lego |
| GPIO | `apps/GPIO/` | NRF24 Mousejack, Marauder companion, Logic Analyzer, GPIO scope |
| Tools | `apps/Tools/` | TOTP, Authenticator, MetroNome |
| Media | `apps/Media/` | MP3 Player (over GPIO add-ons), Music Player |
| Games | `apps/Games/` | Snake, Tetris, Solitaire, Air Arkanoid |
| Examples | `apps/Examples/` | Reference code, drop-in study material |

### Publishing to the catalog

The catalog ships from [github.com/flipperdevices/flipper-application-catalog](https://github.com/flipperdevices/flipper-application-catalog). Submission requires:

- Your `application.fam` with these fields filled in: `appid`, `name`, `apptype=FlipperAppType.EXTERNAL` (or `MENUEXTERNAL`), `entry_point`, `fap_category`, `fap_icon`, `fap_version` (`MAJOR.MINOR`), `fap_description`, `fap_author`, `fap_weburl`.
- A `manifest.yml` in your repo describing the app, screenshots, changelog.
- A clean public GitHub repo. The catalog builds your FAP server-side against multiple SDK versions; you don't ship binaries.
- An icon PNG (10×10, 1-bit, transparent) — `fap_icon=` and `fap_icon_assets=` for any extra art.

The catalog auto-rebuilds your FAP whenever a new firmware SDK drops, so users always get a binary that matches their firmware's API version. That's the **whole point** of going through the catalog instead of distributing `.fap` files directly.

## Community fork app repos

When the catalog doesn't have it (because it's region-block-evading, or because the maintainer didn't submit), check fork-specific apps:

| Repo | Fork | Notable contents |
| --- | --- | --- |
| [Next-Flip/Momentum-Apps](https://github.com/Next-Flip/Momentum-Apps) | Momentum | Maintained pack matching Momentum firmware. Inherits most of what Xtreme had. |
| [DarkFlippers/unleashed-extra-pack](https://github.com/DarkFlippers/unleashed-extra-pack) | Unleashed | Big, slightly older bundle |
| [RogueMaster/RogueMaster-Custom-Pack](https://github.com/RogueMaster/RogueMaster-Custom-Pack) | RogueMaster | Kitchen-sink (some apps duplicated across forks) |
| [flipperdevices/flipperzero-good-faps](https://github.com/flipperdevices/flipperzero-good-faps) | OFW | Curated "good" FAPs that ship in OFW builds |
| [UberGuidoZ/Flipper](https://github.com/UberGuidoZ/Flipper) | All | Mega-collection: dictionaries, IR DBs, sub-GHz captures, asset packs |

If you're going to copy-paste a FAP idea, **read its source** in the appropriate repo first — the manifest fields and Furi APIs change between SDK versions, and an unmaintained `.fap` will refuse to load with `App is not compatible`.

## GPIO add-on ecosystem

The 18-pin GPIO header is the second-largest hardware surface on the device. Stuff that plugs in:

| Add-on | Connector | What it adds |
| --- | --- | --- |
| **Wi-Fi Devboard** (ESP32-S2) | 18-pin matched | SWD debugger + Marauder/Ghost ESP/Bruce/Evil Portal — see [wifi-devboard.md](wifi-devboard.md) |
| **Video Game Module** | 18-pin matched | RP2040 + DVI-D + IMU — see [video-game-module.md](video-game-module.md) |
| **NRF24L01+PA+LNA module** | bare 7 wires (VCC/GND/SCK/MISO/MOSI/CSN/CE) | 2.4 GHz proprietary radio: MouseJack, generic NRF sniffing — see [host-side.md](host-side.md) "MouseJack" |
| **External CC1101 module + SMA antenna** | bare 6 wires + GD0 | Better Sub-GHz range (+6 to +12 dB), removes the internal-antenna matching network constraints somewhat |
| **CC1101 + NRF24 combo board** | one PCB | Both of the above; common DIY breakouts for sale on Tindie/AliExpress |
| **iCE40 FPGA board** (Flipper FPGA Devboard / community) | 18-pin | Lattice iCE40-UP5K — actual FPGA fabric for custom radio DSP, logic, or HDL learning |
| **NMEA GPS module** (NEO-6M / NEO-M8) | TX/RX/3V3/GND | UART GPS — paired with **GPS NMEA** FAP for NMEA decode + lat/lon display |
| **CO2 / temperature / humidity sensors** (BME280, SCD30, etc.) | I2C | One-off sensor projects via I2C JS module or native FAP |
| **MicroSD breakout for second card slot** (rare) | SPI | Persistence offload |
| **Audio I2S DAC** (PCM5102 etc.) | I2S over GPIO | Polyphonic / sampled audio output that the on-board buzzer can't deliver |
| **SD card readers / smart-card readers** | various | ISO7816 contact smart cards (PIV, CAC) — out-of-band from the ST25R3916 NFC frontend |
| **Sentry Safe / Vaultek "key" emulator** | 1-Wire / TX line | Replays the published electronic-lock unlock patterns |

When the user describes "what they're trying to do" rather than "the hardware they have", first answer: which add-on?

## Useful out-of-the-box FAPs to know exist

These come up often enough that the agent should recognize the names rather than try to invent equivalents.

### Sub-GHz

- **Sub-GHz Bruteforcer / SubBrute** — fixed-code 12-bit enumeration.
- **Sub-GHz Remote** — multi-button "universal remote" for saved captures.
- **Frequency Analyzer (continuous)** — extended FA with logging.
- **TPMS Reader / TPMS Sniffer** — vehicle tire-pressure decode.
- **Weather Station** — 433 MHz weather sensor decode (Acurite, Oregon Scientific, etc.).
- **Sub-GHz Pagers / POCSAG decoders** — pager traffic.

### NFC

- **NFC Magic** — write to Gen1A/Gen2/Gen3/Gen4 magic blanks.
- **PicoPass** — iCLASS Legacy read/write.
- **Seader** — iCLASS bridge for Proxmark3.
- **Mifare Fuzzer** — automated MIFARE Classic key fuzz.
- **Amiibomb / AmiiGo** — on-Flipper Amiibo generation.
- **Apple Pay Express** — public EMV transit data dump.

### RFID / iButton

- **LF-RFID Fuzzer** — brute-force EM4100 / HID Prox spaces.
- **iButton Fuzzer** — brute-force Dallas / Cyfral / Metakom.

### Bluetooth

- **BLE Spam** — Apple Continuity / Google Fast Pair / Microsoft Swift Pair / Samsung popup spam.
- **BLE Beacon** — generic BLE advertiser.
- **BLE Lego** — control the Lego Powered-Up hubs.

### GPIO / hardware

- **NRF24 Mousejack** + **NRF24 Sniffer** — wireless keyboard/mouse attack & survey.
- **Logic Analyzer** — turn the Flipper GPIO into a 4–8 channel sigrok-compatible LA.
- **GPIO Reader** — quick pin-state monitor.
- **Wi-Fi Marauder companion** — see [wifi-devboard.md](wifi-devboard.md).
- **ESP32 Camera** companion — feed an ESP32-CAM into the Flipper screen.

### Tools

- **TOTP / Authenticator** — Flipper as a 2FA device for TOTP/HOTP.
- **MetroNome** — for music nerds.
- **UART Terminal** — basic serial console without rebuilding firmware.

### Games (worth studying as code)

- **Snake** (in-firmware), **Tetris**, **Solitaire**, **2048**, **Asteroids**, **DOOM** ports, **GameBoy emulator** (limited), **Flappy Bird**.
- **Air Arkanoid** — VGM IMU game; canonical example of host-FAP ↔ VGM split.

## Decision tree

```
Question: "How do I do X with my Flipper?"
  ├── Is X a known protocol or attack?
  │     ├── YES → Check Apps Catalog (lab.flipper.net) first.
  │     │        If found → install, configure, done.
  │     │        If not in OFW catalog → check Momentum / Unleashed / RogueMaster repos.
  │     └── NO → Treat as research; build a FAP from scratch (fap-development.md)
  │              or prototype in JS (javascript.md).
  └── Does X need extra hardware?
        ├── 2.4 GHz Wi-Fi → Wi-Fi Devboard + Marauder/Ghost ESP
        ├── 2.4 GHz proprietary (Logitech / Microsoft) → NRF24 module + Mousejacker FAP
        ├── External Sub-GHz range → External CC1101 + SMA
        ├── HDMI / 640×480 video → Video Game Module
        ├── GPS / NMEA → NEO-6M/M8 module + GPS NMEA FAP
        └── Custom RF / DSP → iCE40 FPGA board (steepest learning curve)
```

If the answer to "is there a FAP" is "no", and the user is a firmware fork user, also check that fork's monthly release notes — new FAPs land constantly and the catalog lags behind community forks by a few weeks.
