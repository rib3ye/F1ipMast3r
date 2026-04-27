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

Flipper Zero **receives** anywhere in 300–348 / 387–464 / 779–928 MHz. It **transmits** only on bands the active region marks legal for civilian use. The block is enforced inside the firmware before the CC1101 is keyed, so it applies equally to the Sub-GHz app, `furi_hal_subghz_set_frequency`, the JS `subghz` module, the CLI/RPC surfaces, and any custom FAP. When blocked the UI shows: *"Transmission is blocked. Transmission on this frequency is restricted in your region."*

The full per-region table and notes live in [limits.md](limits.md) → "Region transmit blocks". Authoritative external source: [docs.flipper.net/zero/sub-ghz/frequencies](https://docs.flipper.net/zero/sub-ghz/frequencies). Region toggle: `Settings → System → Region`; Momentum/Unleashed/RogueMaster expose a "world" option that lifts the block.

## Sub-GHz operator workflows

Knowing the protocols isn't the job — knowing what to do when you don't yet know which protocol is. Pre-canned playbooks:

### Frequency Analyzer first

`Sub-GHz → Frequency Analyzer` is the first tool you reach for against an unknown remote. It sweeps the operational windows watching RSSI and snaps to the strongest carrier when you hold the FOB's button. If it locks 433.92 MHz, you're in Princeton/CAME/Nice country; 315 MHz says US-market garage/automotive; 868.35 MHz says EU-market alarm/gate.

If the FOB never lights it up, suspect: out-of-band (e.g. 869.85 MHz "European SRD" — in window but not popular), DSSS / FHSS (won't decode regardless — see [limits.md](limits.md)), or you're holding the wrong button.

### `Read` vs `Read RAW`

| Mode | Use when |
| --- | --- |
| `Sub-GHz → Read` | You expect a known protocol (Princeton, CAME, Nice, KeeLoq, etc.). Returns parsed key+button+TE — small, replayable, editable in qFlipper |
| `Sub-GHz → Read RAW` | Decoder doesn't lock, or you need the timing array verbatim (custom modulation, weird preamble) |
| `Read RAW` then convert | Capture once, analyze on host with [Universal Radio Hacker](https://github.com/jopohl/urh), then synthesize a parsed `.sub` |

`Read RAW` files are larger, won't show a friendly key on the Flipper, but transmit faithfully. They're also how you preserve a rolling-code transmission for later analysis (even though you can't replay it productively against a synced receiver).

### Sub-GHz Bruteforcer / OpenGarages

For 12-bit fixed-code gates (Princeton-family `PT2240`, `PT2262`, `EV1527` with the classic 4096-state keyspace), the community **Sub-GHz Bruteforcer** FAP enumerates the entire keyspace in ~3 minutes per frequency. It ships with `.sub` payload files for the common encodings under `apps_data/subbrute/`. Still useless against rolling-code receivers.

### TPMS

Tire-pressure sensors broadcast every ~30–60 seconds at 315 MHz (US) or 433.92 MHz (EU/JP). Each sensor's ID is unique and unencrypted. **TPMS Reader** community FAPs decode Schrader, Continental, Toyota, Pacific Industries, Renault, GM and a few others — mostly useful for fleet/asset tracking, parking-lot recon, or vehicle re-identification.

### POCSAG / FLEX

Pager traffic on 138 / 153 / 158 / 163 / 450 MHz (region-dependent) is plaintext POCSAG or FLEX. Flipper FAPs (e.g. **Sub-GHz Pagers**, decoder forks) demodulate POCSAG-512/1200/2400 at 433.92 / 868 MHz where it overlaps the operational windows. Hospitals, restaurants, and a surprising amount of legacy industrial telemetry still ride this.

### Continuous-TX (jammer pattern)

The CC1101 supports continuous unmodulated carrier via `furi_hal_subghz_tx_continuous` (or by setting the chip into TX mode without an async source). It's the lowest-level hammer: full-band RF noise on the configured frequency until you stop it.

Caveats that always apply:

- Region block applies. The firmware refuses to key the CC1101 outside the region's TX bands.
- Drains the battery in roughly 10–20 minutes flat.
- Effective range is the same ~50 m as a normal TX — it's not a wide-area jammer.
- "RollJam" against rolling-code receivers (jam + capture + replay-with-stored) is a *concept* not a stock feature; needs custom firmware AND physical proximity to the legitimate FOB owner.

The takeaway for any operator question about jamming: the API exists, the band is enforced, the range is short, and the battery costs are real.

### Replay attacks against the obvious targets

| Target class | Outcome of straight replay |
| --- | --- |
| Princeton / CAME / Nice fixed-code gate | Works (often) |
| KeeLoq HCS-family rolling-code FOB | **Fails** against synced receiver — see [limits.md](limits.md) |
| Tesla 315 MHz charge-port latch (pre-2021ish) | Replay works on older firmware; Tesla patched the rolling code on newer cars. Worth `Read` + try, useful as a known case study |
| Doorbell / weather sensor / cheap remote | Almost always works |
| Faac SLH / Beninca / Somfy Telis | Rolling, fails |
| Industrial RF remote (overhead crane, cement mixer) | Mixed — many use fixed-code ASK, replay works |

### Sub-GHz Chat

`subghz chat <freq>` (CLI) or **Sub-GHz Chat** app turns two Flippers within ~50 m into walkie-talkies on a chosen frequency in the region's TX band. Slow, lossy, but it's a covert side channel that doesn't touch IP, BLE, or anything monitorable from the network. **ESubGhz Chat** (community FAP) adds AES encryption with a pre-shared key.

### External CC1101 module

If the receiver's >50 m, swap to an external CC1101 module on the GPIO header with an SMA antenna. `subghz.isExternal()` (JS) or the on-device "External Module" toggle reroutes TX/RX through it. Gain budget: +6 to +12 dB depending on the antenna; line-of-sight ~150 m at 433 MHz becomes plausible.

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

### Hotel keycard families

Most hotel locks are MIFARE Classic 1k variants with a vendor-specific sector layout. Flipper handles the chip; the *interpretation* of the data is what differs.

| Family | Chip | Interesting because |
| --- | --- | --- |
| **Saflok / Dormakaba** | MIFARE Classic 1k or Ultralight C | **Unsaflok** (March 2024, CVE-2024-32877 cluster) — derive a master key from a single guest card, forge any keycard for that property. Affects ~3M doors globally. Patches rolling out slowly. |
| **VingCard** (Assa Abloy) | MIFARE Classic 1k / DESFire / iCLASS | Older Vision/Signature locks have known fixed-key sectors; newer Allure/Essence series moved to DESFire AES (out of reach without keys) |
| **Salto** | MIFARE Classic, DESFire EV1/2, BLE add-on | "Carrier" model encodes access on the card itself — interesting target for offline analysis. Newer SVN-flex moves auth on-line |
| **Kaba** (now Dormakaba) | shares Saflok-side chips | See Saflok |
| **Onity** | proprietary IR DC port (NOT NFC) | Famously Cody Brocious / "Black Hat 2012" sidechannel — that was the IR DC barrel-jack on the lock body. Flipper IR can speak it; see [infrared](#infrared-tx-led--rx-photodiode) |

Workflow against an unknown hotel card: read with the dedicated NFC app → check `Mifare Classic type` and `UID` length in the saved `.nfc` → run a dictionary scan → if all sectors crack, look at sector layout (lots of `00 00 00 ...` is suspicious; `key_a` reuse across rooms says the lock uses a property-wide master). The Unsaflok work was published — search current public writeups for the master-key derivation if the property hasn't patched yet.

### HID iCLASS / PicoPass

iCLASS is HID's 13.56 MHz line, *not* MIFARE-compatible. Flipper supports it via the **PicoPass** community FAP (and increasingly natively in OFW).

| Variant | Crypto | Realistic |
| --- | --- | --- |
| **iCLASS Legacy** ("Standard") | Single-DES with a customer-shared master key | Master key is publicly known (HID had a key-leak ~2012). Flipper reads + writes via PicoPass / **Seader** apps |
| **iCLASS SE** | AES with per-card derived keys | Out of reach without the customer's master |
| **iCLASS SEOS** | AES; mobile-credential capable (HID Mobile Access) | Out of reach; SEOS is the modern HID enterprise badge |

Workflow: read with PicoPass FAP → save → write to a **PicoPass blank** (sold as "SE blank" or "iCLASS blank" — search "iCLASS PicoPass blank card"). Standard MIFARE T5577/Magic blanks won't hold an iCLASS personality.

The **Seader** app exposes the iCLASS reader/emulator to a host PC over USB — useful for hooking into Proxmark3 workflows when you want to do bigger crypto work the Flipper can't.

### MIFARE Classic key recovery — `mfkey32` walkthrough

Skip if you already have a known key (then dictionary or Hardnested).

1. Save a target card with `Read` (saves UID + ATQA + SAK; keys still unknown).
2. `Apps → NFC → Detect Reader` → tap the Flipper to the **legitimate reader** (not the card). Reader sends nonces + auth attempts; Flipper logs them to `/ext/nfc/.mfkey32.log`.
3. After ~10–30 reader interactions, the log holds enough nonce pairs.
4. Run `mfkey32` on the saved log on the Flipper itself (`NFC → mfkey32` menu in OFW; in older firmware, copy the log off and run `mfkey32 v2` on a host).
5. Keys get appended to `/ext/nfc/assets/mf_classic_dict_user.nfc`.
6. Re-read the original card → those keys now in the dictionary unlock the sectors → full dump.

Alternatives:

- **Dictionary attack first** — Flipper auto-runs the system dictionary on every Classic read. Many cheap badges still ship with default `FF FF FF FF FF FF` or a known-vendor key.
- **Hardnested** — needs at least one known key for one sector. Flipper has it built in (`Read with debug`).
- **Static-nonce / nested classic** — older variants, also built in.

### Built-in dictionaries

| Path | What's in it |
| --- | --- |
| `nfc/assets/mf_classic_dict.nfc` | Stock dictionary shipped with firmware — default keys, common transit, vending, common access-control families |
| `nfc/assets/mf_classic_dict_user.nfc` | Your additions. Auto-grown by `mfkey32` runs |
| `nfc/assets/mf_ul_dict.nfc` | MIFARE Ultralight C / NTAG21x passwords |

Extend the user dictionary by appending hex strings (one key per line, 12 hex chars):

```
A0A1A2A3A4A5
D3F7D3F7D3F7
4B791BEA7BCC
```

The community-curated **flipper_mfkey** dictionary (UberGuidoZ pack) merges keys from public dumps; drop into the user file to massively widen first-pass coverage.

### NTAG215 / Amiibo

Amiibo are NTAG215 with a 540-byte payload signed by Nintendo's master key. Flipper's NFC app reads them directly; for *generating* arbitrary Amiibo you need:

- The Amiibo master keys (`unfixed-info.bin` + `locked-secret.bin`) from Nintendo. Public.
- A serializer like **Amiitool** or the **Amiibomb** community FAP that bakes them on-Flipper.

Write target: NTAG215 blanks, or **Magic Ultralight / "DirectWrite"** for full UID control. Flipper preserves the dynamic lock bytes correctly when cloning genuine Amiibo.

### Other useful NFC FAPs

| FAP | Job |
| --- | --- |
| **NFC Magic** | Direct magic-card writes (Gen1A backdoor, Gen2 CUID, Gen3, Gen4 personality switch). The proper tool for cloning to magic blanks |
| **Mifare Fuzzer** | Automated brute-force / fuzz against unknown MIFARE Classic key spaces — slow but unattended-runs-friendly |
| **PicoPass** / **Seader** | iCLASS Legacy read/write + Proxmark3 bridge |
| **Amiibomb** / **AmiiGo** | On-Flipper Amiibo generation |
| **Apple Pay Express** | Reads the public Apple Pay transit data from EMV transit cards |

### Workflow tips

- For DESFire research, the Flipper exposes raw `iso14443_4a_*` APIs in C — build your own APDU explorer if you need to talk to a specific applet.
- "Read with debug" mode is gated behind `Settings → System → Debug = ON` and exposes more raw frame info.
- After cloning to a magic card, **always verify by reading the clone**, not just by trusting the write status.

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

### Polarity / contact gotcha

The single biggest "why doesn't this work?" with iButton is contact polarity. The **flat side** of the Dallas-style button is the data line; the rim is GND. The Flipper's iButton pad has a center disc (data) surrounded by a ring (GND). Press the **flat face down** onto the pad so the center disc touches the flat side. Coming in at an angle, or pressing the rim side, gets you intermittent reads or no read at all. RW1990 / TM2004 blanks have the same orientation as the original keys; visually identical, mark them so you don't confuse "read" and "write" stock.

## Infrared (5-LED omnidirectional TX + RX photodiode)

Hardware: **5 IR LEDs arranged in a star** at the top edge so the Flipper TXs in roughly every direction at once. RX is a single photodiode behind the same window. You don't need to aim carefully when transmitting — practical range is ~5 m and the omnidirectional pattern means a 30° miss still works. RX is much more directional; line up the source remote square-on for clean captures.

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
