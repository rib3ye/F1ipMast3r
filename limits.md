# Hardware and protocol limits

What the Flipper Zero (and its modules) physically cannot do, refuses to do at the firmware level, or will fail at because the protocol itself doesn't allow it. Pure facts, useful when the user asks "why didn't this work?" or "is this even possible?"

## Region transmit blocks (firmware-level)

Flipper **receives** anywhere in 300–348 / 387–464 / 779–928 MHz. It **transmits** only on the bands the active region setting marks as legal for civilian use. The block is enforced inside the firmware before the CC1101 is keyed, so it applies equally to:

- The Sub-GHz app's TX / Send.
- `furi_hal_subghz_set_frequency` returning a different (snapped) frequency or refusing.
- `subghz.transmitFile()` from JS.
- The `subghz tx_from_file` CLI command and the matching RPC.

When blocked, the UI shows: *"Transmission is blocked. Transmission on this frequency is restricted in your region."*

Snapshot of common regions (authoritative table: [docs.flipper.net/zero/sub-ghz/frequencies](https://docs.flipper.net/zero/sub-ghz/frequencies)):

| Region | Allowed TX bands |
| --- | --- |
| EU / UK | 433.05–434.79 MHz, 868.15–868.55 MHz |
| US / CA / MX / AU / NZ / BR / AR | 304.10–321.95 MHz, 433.05–434.79 MHz, 915.00–928.00 MHz |
| JP | 312.00–315.25 MHz, 426.25–426.83 MHz, 920.50–923.50 MHz |
| Singapore | 304.50–321.95 MHz, 433.05–434.79 MHz, 444.40–444.80 MHz, 915.00–927.95 MHz |
| Israel | 433.05–434.79 MHz |
| India | 433.05–434.79 MHz |
| China | 314–316, 430–432, 433.05–434.79 MHz |
| Rest of world | 920.50–923.50 MHz |

Region is set at `Settings → System → Region`. The shipped region depends on where the device was sold; some firmware forks (Momentum, Unleashed, RogueMaster, Xtreme) expose a "world" / "developer" region option that lifts the table.

## Sub-GHz protocol limits

### Rolling codes

Replaying a captured rolling-code transmission **fails against a synchronized receiver**. The receiver's counter has already advanced past the captured code, so the recording becomes invalid the moment the legitimate FOB is pressed.

Flipper can read and save the raw signal of a rolling-code transmission, but cannot:

- Predict the next valid code without the manufacturer's secret key.
- Resync a receiver from outside (the receiver only resyncs to its own paired FOBs via a button-press procedure).
- Defeat KeeLoq's encryption (HCS200/300/301/400/410/412/473), Hi-Tag2, Hitag AES, Megamos Crypto, Atmel Hi-Sec, etc., because those use per-FOB secret keys held in the manufacturer's database.

The "rolling jam" / RollJam class of attacks is also not implemented in stock Flipper firmware — and even where it is technically possible, it requires holding the legitimate FOB owner's button while the Flipper jams, which is a physical scenario rather than a Flipper limit.

### Range

Stock internal antenna: ~50 m line-of-sight at 433 MHz with no obstructions. Through walls / outdoors with foliage: 5–20 m. External CC1101 modules with an SMA antenna get +6 to +12 dB.

### Modulation reach

The CC1101's matching network is tuned for the operational windows. Trying to "set 100 MHz" or "set 1.2 GHz" does not work — `furi_hal_subghz_is_frequency_valid` returns false outside 300–348 / 387–464 / 779–928 MHz.

### Bit rate ceiling

Async OOK/FSK with timer-captured GPIO tops out around ~250 kbit/s before timing jitter dominates. For higher-rate protocols, use the CC1101 packet engine (sync word + length + CRC) rather than async raw — but you give up arbitrary bit-level decoding.

## NFC limits

### Cryptography is not magic

Flipper cannot read or clone:

- **MIFARE DESFire EV1/EV2/EV3** application files protected by AES master keys you don't have.
- **MIFARE Plus SL2/SL3** in AES mode.
- **HID iCLASS SE / SEOS** — these use Authentic-Mode-2 with per-card AES keys derived from a customer master key.
- **PIV / CAC / FIDO2 cards** — secure elements, on-card key generation.
- **EMV payment cards beyond their public application data** — the live cryptogram requires the card's secret key, which the card doesn't expose.

This isn't a firmware shortcoming; it's the cipher. If the card holds a secret the Flipper has never seen, the Flipper cannot derive it from outside.

### Things that DO work

- **MIFARE Classic 1k/4k** Crypto-1 keys are recoverable via dictionary, nested attack, or Hardnested when you have at least one known key (or via mfkey32 capturing a real reader's nonces). Flipper has all three built in.
- **MIFARE Ultralight / Ultralight C / NTAG 21x** — read everything, write to NTAG21x or to magic Ultralight blanks. NTAG215 is the Amiibo target.
- **DESFire** — reading the application directory and unauthenticated files works fine.
- **ISO15693 SLI / SLIX** — read and write user memory; SLIX privacy-mode passwords are usually default.
- **FeliCa unencrypted areas** (Suica balance, transit history) — read-only.

### Magic card capabilities

| Magic class | What flips | Use it for |
| --- | --- | --- |
| Gen1A ("backdoor") | Block 0 (UID) writable via vendor commands | Cloning a Classic 1k card you already extracted keys for |
| Gen2 / CUID | UID writable but block 0 has standard auth | Cleaner clones |
| Gen3 | UID-set commands without a backdoor | Newer reader compatibility |
| Gen4 ("ultimate magic") | Personality switch: 1k/4k/Ultralight/NTAG | One blank for any tag family |
| DirectWrite Ultralight | Writable OTP / lock bytes | Amiibo cloning |

### EMV (bank cards)

Flipper reads:

- The card's PAN (primary account number) — when exposed in plaintext, which is most of the time.
- The cardholder name / expiration when included in the public application data.
- Transaction history blocks if the card writes them in plaintext (some do, most don't).

Flipper does NOT (and the protocol does not allow without the card's keys):

- Generate a valid Application Cryptogram for a new transaction.
- Emulate a card such that a contactless terminal accepts the transaction.
- Recover the card's symmetric/asymmetric keys.

EMV emulation in any tooling is "replay-window" at best — i.e. capture the card responding to a specific reader challenge, then replay to that exact reader within seconds. That isn't cloning; it's a relay attack and it requires both ends physically present.

## 125 kHz LF limits

Almost all 125 kHz protocols are open / weakly authenticated. Flipper reads and clones the entire common list (EM4100, HID Prox H10301/H10302/H10304/Corp1000, Indala 26/27/224, AWID, Pyramid, Viking, Jablotron, Paradox, Securakey, GProx II, Nexwatch, Presco, Idteck) onto T5577 or EM4305 blanks.

What 125 kHz fundamentally cannot do:

- Authenticate. There is no challenge/response in EM4100 or HID Prox — the badge transmits its ID continuously when energized. A clone is a clone.
- Hide from a reader if the reader doesn't expect that format.

## iButton limits

Same story as 125 kHz LF. Dallas DS1990A (family code 0x01) is a 64-bit ID with a CRC byte; it's on a 1-Wire bus; it doesn't authenticate. Flipper reads and writes RW1990 / TM2004 / TM01C blanks for any of Dallas / Cyfral / Metakom.

## Infrared limits

- The TX LED is omnidirectional but its useful range is ~5 m. Aiming matters.
- Default carrier is 38 kHz (consumer IR). AC remotes commonly use 36 / 40 kHz; use Pronto Hex or RAW to set carrier explicitly.
- Bidirectional protocols (HDMI-CEC, some smart-TV wake-on-LAN-over-IR variants) have a back channel the Flipper doesn't sit on, so capturing one direction won't reproduce the conversation.
- Long codes (Air conditioner remotes with 100+ bits encoding all state in one transmission) save fine but take noticeable time to TX (~200 ms per send).

## Speaker / audio limits

- Single oscillator. No PCM, no waveform synthesis, no two notes at once.
- Frequency range is roughly 100 Hz – 15 kHz, but the resonant peak of the buzzer is around 2.7 kHz. Tones too far from that are quiet.
- Volume is software-controlled but the hardware has effectively ~3 useful steps; treat `furi_hal_speaker_start(freq, volume)` as on/off in practice.

## Display limits

- 128×64 monochrome. No greyscale, no alpha. Half-tones are dither only.
- Practical refresh rate ~30 FPS; pushing higher works but burns battery and steals CPU from your game logic.
- The backlight is a single white LED on/off, no brightness curve worth noting.

## RAM / flash budget for FAPs

- Default `stack_size = 2 * 1024` (2 KiB). Bump to 4 KiB if you crash inside string ops; 8 KiB+ is rare and suggests you should heap-allocate instead.
- Heap is shared with the OS. `furi_hal_memory_get_free()` typically reports 30–80 KiB free when no other apps are running. Big radio buffers (full-second 1 µs samples = ~4 MB) won't fit.
- A `.fap` over ~256 KiB takes a noticeable fraction of a second to load from SD.

## CC1101 packet engine vs async

| | Async (timer-captured GPIO) | Packet engine |
| --- | --- | --- |
| Bit rate | Up to ~250 kbit/s | Up to ~600 kbit/s |
| Use for | Arbitrary protocols, raw timing replay | Standard sync word / length / CRC frames |
| CPU cost | High (per-edge ISR) | Low (DMA from FIFO) |
| Code complexity | Decode it yourself | Configure registers, read packets |

## Wi-Fi Devboard limits

- ESP32-S2-WROVER, single-core 240 MHz, ~320 KB SRAM. Plenty for Black Magic + a tiny web UI.
- GDB server tops out around 1 Mbit/s effective over Wi-Fi, more over USB CDC.
- 2.4 GHz only. No 5 GHz, no Bluetooth (the S2 has no BT radio).
- Power: from Flipper 3V3, or from the Devboard's own USB-C. Don't power both at once if you can avoid it (the boards handle it but it's cleaner to pick one).

## Video Game Module limits

- DVI-D 640×480@60 fixed. No 720p, no 1080p, no scaling beyond the firmware's framebuffer logic.
- The HDMI port on the VGM is electrically DVI-D — fine for monitors / TVs that accept DVI over HDMI (almost all). Some HDMI-only gear (capture cards, splitters) refuses DVI signaling. If your monitor shows "no signal", try a different sink first.
- USB-C does NOT support Power Delivery — 5 V only.
- The IMU and the PIO video output share SPI / DMA resources with the RP2040 USB stack. Heavy USB host traffic + 60 FPS rendering + 1 kHz IMU polling will drop frames. Keep one of the three light.
- GP8–GP15 and GP18–GP20 are reserved for video. Anything you wired there in a Pi Pico project must move.

## What "won't work" usually means

- Tried to TX on 850 MHz: region block (firmware), or out of band (hardware) — check region first.
- Replayed a car key, doesn't open the car: rolling code (protocol), as expected.
- Read a corporate badge and it didn't open the door: secure element (cipher), the Flipper saw a different surface than the reader needs.
- Captured a `.sub` with `Protocol: RAW` and emulation looks correct on a logic analyzer but the receiver ignores it: check modulation / preset, not protocol.
- A FAP loads then immediately exits: API mismatch — `ufbt update` against the firmware fork's SDK index.

When something fails, it's almost always one of: region block, rolling code, secure-element cipher, mismatched preset/modulation, or API version drift. Diagnose in that order.
