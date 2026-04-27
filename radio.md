# Radio reference (Sub-GHz, NFC, 125 kHz LF, iButton, Infrared)

This is the deep dive. Anything radio-shaped routes here.

## Sub-GHz (CC1101, 300–928 MHz)

### Hardware

- TI CC1101 transceiver, controlled over SPI, with the GD0 line wired into a GPIO/timer for async OOK/FSK capture.
- Internal antenna covers three operational windows: **300–348 MHz**, **387–464 MHz**, **779–928 MHz**. Outside those windows you get attenuation/no lock — there is no "tune to 100 MHz" mode, the matching network won't cooperate.
- External CC1101 modules (the official "Sub-GHz extension" boards) plug into the GPIO and add an SMA antenna for ~+10 dB.

### Modulation presets (`FuriHalSubGhzPreset*`)

| Preset | Modulation | Bandwidth | Use it for |
| --- | --- | --- | --- |
| `Ook270Async` | OOK | 270 kHz | Tight, narrow OOK gates and weather stations |
| `Ook650Async` | OOK | 650 kHz | The default workhorse — most garage doors, PT2262, CAME, Nice |
| `2FSKDev238Async` | 2-FSK | 270 kHz, ±2.38 kHz | Slow narrow FSK (some sensors, ADS-something hobbyist RX) |
| `2FSKDev476Async` | 2-FSK | 270 kHz, ±47.6 kHz | Fast wide FSK — KeeLoq HCS2/3, some Nice FloR |
| `MSK99_97KbAsync` | MSK | 99.97 kbps | Industrial telemetry (rare) |
| `GFSK9_99KbAsync` | GFSK | 9.99 kbps | LoRaWAN-ish narrowband |
| `Custom` | user-supplied register table | — | Load a 16-entry uint8_t register array via `furi_hal_subghz_load_custom_preset` |

If you need a wholly custom modulation (e.g. ASK with a weird symbol rate), build it as a register table and feed it to `furi_hal_subghz_load_custom_preset`. The async-TX path takes a callback that yields `LevelDuration` records — that's the lever for arbitrary protocols.

### Async TX/RX in C

```c
#include <furi_hal_subghz.h>

furi_hal_subghz_reset();
furi_hal_subghz_load_preset(FuriHalSubGhzPresetOok650Async);
furi_hal_subghz_set_frequency_and_path(433920000);   // also picks the matching path

static void rx_capture(bool level, uint32_t duration, void* ctx) {
    // duration is in usec, level is the new state
}
furi_hal_subghz_start_async_rx(rx_capture, NULL);
// ... later
furi_hal_subghz_stop_async_rx();

// Async TX: callback yields LevelDuration entries, end with level_duration_reset()
LevelDuration tx_yield(void* ctx) { ... }
furi_hal_subghz_start_async_tx(tx_yield, NULL);
while (!furi_hal_subghz_is_async_tx_complete()) furi_thread_yield();
furi_hal_subghz_stop_async_tx();
```

### Protocols Flipper decodes natively

Static / fixed-code (Flipper can read AND TX-replay):

- Princeton (PT2262, PT2272, EV1527, RT1527, HS1527, HX2262, SC5262, SC2272)
- CAME, CAME TwEE, CAME Atomo
- Nice Flo (12 / 24 bit)
- BETT
- Doitrand
- Gate TX
- Hörmann HSM
- Holtek HT12X family
- Linear Multicode, Magicode, Marantec, Megacode, Power Smoke, Security+ 1.0/2.0 (read only on 2.0)
- SMC5326, Smartstop, UNILARM
- Aprimatic, Phoenix V2

Rolling-code (Flipper reads or saves the raw, but does NOT defeat the rolling-code logic — emulation will fail against a sync'd receiver):

- KeeLoq family (HCS101 / HCS200/300/301 / HCS400/410/412 / HCS473)
- Nice FloR-S
- Faac SLH / SLH Spa
- Beninca
- Centurion Nova
- Somfy Telis / Keytis
- Chamberlain Security+ 2.0

A captured rolling-code transmission cannot be replayed against a synced receiver — the receiver has already advanced past that counter value. See [limits.md](limits.md) → "Rolling codes" for what that means in practice.

### `.sub` file format (Flipper Format File)

```
Filetype: Flipper SubGhz Key File
Version: 1
Frequency: 433920000
Preset: FuriHalSubGhzPresetOok650Async
Protocol: Princeton
Bit: 24
Key: 00 00 00 00 00 12 34 56
TE: 391
Repeat: 5
```

Raw signal variant uses `Protocol: RAW` plus `RAW_Data:` lines of signed integers (positive = level high N µs, negative = level low N µs). Files live in `subghz/` on the SD card; `subghz/assets/setting_user.txt` lets advanced users add custom frequencies (some forks expose this; on stock OFW, region table is enforced).

### Region transmit table

Flipper Zero **receives** anywhere in 300–348 / 387–464 / 779–928 MHz. It **transmits** only on bands the active region marks legal for civilian use. The block is enforced inside the firmware before the CC1101 is keyed, so it applies to the Sub-GHz app, `furi_hal_subghz_set_frequency`, the JS `subghz` module, and the CLI/RPC surfaces alike. When blocked the UI shows: *"Transmission is blocked. Transmission on this frequency is restricted in your region."* Full table and the reasons each band is or isn't permitted lives in [limits.md](limits.md) → "Region transmit blocks". Authoritative source: [docs.flipper.net/zero/sub-ghz/frequencies](https://docs.flipper.net/zero/sub-ghz/frequencies). Quick snapshot:

| Region | Allowed TX bands |
| --- | --- |
| EU / UK | 433.05–434.79 MHz, 868.15–868.55 MHz |
| US / CA / MX / AU / NZ / BR / AR | 304.10–321.95 MHz, 433.05–434.79 MHz, 915.00–928.00 MHz |
| JP | 312.00–315.25 MHz, 426.25–426.83 MHz, 920.50–923.50 MHz |
| Rest of the world | varies — see [limits.md](limits.md) |

Region is set at `Settings → System → Region`. Some firmware forks (Momentum, Unleashed, RogueMaster, Xtreme) expose a "world" / "developer" region option that lifts the table.

## NFC (13.56 MHz, ST25R3916)

### Tag families

- **ISO14443A** (most common):
  - **MIFARE Classic 1k / 4k / Mini** — Crypto-1 cipher, key-A / key-B per sector. Vulnerable to nested attack and Hardnested. Flipper has built-in `mfkey32` collection during reads against a real reader, plus dictionary attack.
  - **MIFARE Ultralight, Ultralight C, Ultralight EV1, NTAG203/210/213/215/216** — open or 3DES auth (Ultralight C). NTAG215 is the Amiibo target.
  - **MIFARE DESFire EV1 / EV2 / EV3** — 3DES / AES, ISO/IEC 7816-4 APDU. Flipper can read the application directory and unauthenticated files; full app cloning needs the AES master key (which you should not have).
  - **MIFARE Plus** — Crypto-1 (SL1) or AES (SL2/3).
- **ISO14443B** — read-only support for some transit cards.
- **ISO15693 / NFC-V** — SLI / SLIX (Tag-it / I-Code), used in some library / inventory systems.
- **FeliCa (JIS X 6319-4)** — Suica, PASMO, Octopus. Flipper reads service codes + block data when the area is unencrypted.
- **EMV (bank cards)** — Flipper reads the public application list and primary account number where exposed. Live transaction emulation is not possible without the card's per-card secret key, which the chip doesn't expose; "EMV emulation" in any tooling is at best a relay attack with both ends physically present. See [limits.md](limits.md) → "EMV (bank cards)".

### Magic cards (copy targets)

- **Gen1A / "Magic" Classic** — backdoor at block 0 lets you write the UID. Detect with `RC500 unlock` or "Read with debug" in the NFC menu.
- **Gen2 / CUID** — UID is writable but block 0 has standard auth.
- **Gen3** — accepts vendor-specific commands to set UID without backdoor.
- **Gen4 / "ultimate magic"** — Full personality switching: can pretend to be 1k / 4k / Ultralight / NTAG. Clone target of choice for hobbyists.
- **Magic Ultralight / "DirectWrite"** — writable OTP / lock bytes, used to clone NTAG215 / Amiibo.

### `.nfc` file shape

```
Filetype: Flipper NFC device
Version: 4
# Device type can be UID, Mifare Ultralight, NTAG215, Mifare Classic
Device type: Mifare Classic
# UID is common for all formats
UID: A1 B2 C3 D4
ATQA: 00 04
SAK: 08
Mifare Classic type: 1K
Block 0: A1 B2 C3 D4 ...
Block 1: ...
Key A sector 0: FF FF FF FF FF FF
Key B sector 0: FF FF FF FF FF FF
```

### Workflow tips

- For MIFARE Classic key recovery without a known key, capture an authentic interaction with the real reader (`Detect Reader`) — the Flipper records reader nonces, then `mfkey32 v2` cracks them offline. Default-key dictionary scans first; Hardnested only if you already know one key.
- For dumping NTAG215 / Amiibo, use the dedicated NTAG menu — Flipper preserves dynamic lock bytes correctly.
- For DESFire research, the Flipper exposes raw `iso14443_4a_*` APIs in C — you can build your own APDU explorer.

## 125 kHz LF RFID

### Supported protocols

| Family | Notes |
| --- | --- |
| **EM4100 / EM4102** | 64-bit Manchester, the most common cheap badge |
| **HID Prox** | H10301 (26-bit), H10302 (37-bit), H10304, Corporate-1000, etc. |
| **Indala** | 26 / 27 / 224 bit variants |
| **AWID** | 26 / 50 bit |
| **Pyramid** | 26 / 39 bit |
| **Viking** | proprietary |
| **Jablotron** | EU access systems |
| **Paradox**, **Securakey**, **GProx II**, **Nexwatch / Honeywell**, **Presco**, **Idteck** | various |

### Universal write target

**T5577** (a.k.a. ATA5577) is the universal 125 kHz blank — it can emulate basically every 125 kHz protocol the Flipper reads. Buy them in bulk on AliExpress for ~$0.30 each. Flipper writes the right modulation/bit count automatically when you choose "Write T5577" from a saved card. EM4305 is the second-best alternative (cheaper, fewer protocol options).

**EM4305** is the alternative blank — slower to clone, fewer formats supported.

### Workflow

1. Read the source card → save with a memorable name.
2. Place blank T5577 on the antenna → Saved → Write.
3. Verify by reading the freshly-written T5577 — should match exactly.

### `.rfid` shape

```
Filetype: Flipper RFID key
Version: 1
Key type: EM4100
Data: 12 34 56 78 9A
```

## iButton (1-Wire, pin 17)

### Supported keys

- **Dallas DS1990A** — 64-bit ROM (8-bit family code, 48-bit serial, 8-bit CRC). Family code `0x01` = standard. Most common in Eastern European apartment intercoms.
- **Cyfral** — proprietary 9-bit-per-nibble pulse-width encoding, Russian intercom standard.
- **Metakom** — another Russian standard, ~16 hex chars.

### Blank key targets

- **RW1990, RW1990.2, RW2004, RW2007** — writable Dallas-compatible.
- **TM2004** — 64-bit Dallas-compatible, popular blank.
- **TM01C** — Cyfral / Metakom-capable blank that also emulates Dallas.

### `.ibtn` shape

```
Filetype: Flipper iButton key
Version: 1
Key type: Dallas
Data: 01 12 34 56 78 9A BC DE
```

Programming a blank: Saved → Write — Flipper handles the protocol-specific timing.

## Infrared (TX LED + RX photodiode)

### Decoded protocols

- **NEC**, **NEC extended**, **NEC42**, **NEC42 extended**
- **Samsung32**
- **RC5**, **RC5X**, **RC6**
- **Sony SIRC** (12 / 15 / 20 bit)
- **Kaseikyo** (Panasonic / JVC / Mitsubishi / Denon family)
- **Pioneer**
- **Pronto Hex** — universal raw frequency+timings dump (works for anything)
- **RAW** — fallback: just the timing array

### `.ir` file shape

```
Filetype: IR signals file
Version: 1
#
name: Power
type: parsed
protocol: NEC
address: 04 00 00 00
command: 08 00 00 00
#
name: Vol+
type: raw
frequency: 38000
duty_cycle: 0.330000
data: 9024 4512 564 564 564 1692 564 564 ...
```

Multiple buttons live in the same file. Universal remote DBs ship under `infrared/assets/{tv,audio,ac,projector,...}.ir` — community-curated, growing all the time.

### Tips

- Carrier frequency defaults to 38 kHz (consumer IR). AC remotes often use 36/40 kHz — use Pronto or RAW.
- Don't expect to clone the bidirectional handshake of a smart TV's HDMI-CEC remote — the back channel is on a different bus.
- TV-B-Gone-style "shut up" databases (every common TV-off code in one file) live under `infrared/assets/tv-universal.ir`.

## Cross-protocol file API

In C: `flipper_format_*` reads/writes any FFF document. Open with `flipper_format_file_open_existing` or `_new`, then `flipper_format_read_string`, `_read_uint32`, `_read_hex`, etc. by key.

In JS: `let storage = require("storage");` then read the file as text and parse — or shell out to a CLI command.

When defining a new file type, follow the FFF convention strictly: `Filetype:` + `Version:` on the first two lines, then key=value, with arrays as space-separated bytes. This is what makes the qFlipper / Flipper Mobile App / firmware all interoperate.
