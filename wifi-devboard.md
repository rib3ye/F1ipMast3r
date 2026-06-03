# Wi-Fi Developer Board (ESP32-S2 — debugger AND 2.4 GHz attack platform)

The Wi-Fi Devboard is two things at once and the skill should never collapse them into one. Pick the firmware that matches the job:

- **Black Magic / CMSIS-DAP firmware** → SWD/JTAG into the Flipper STM32 (or any ARM target on its 14-pin header). Default ship state.
- **Marauder / Ghost ESP / Bruce / Evil Portal firmware** → 2.4 GHz attack platform driven from the Flipper's UI or a host browser/CLI.

Same hardware, swap the firmware via the on-board web UI or `esptool.py`. The Flipper itself never reflashes the ESP32 automatically — you do that yourself.

## Hardware

| Part | Detail |
| --- | --- |
| MCU | Espressif **ESP32-S2-WROVER**, single-core Xtensa LX7 @ 240 MHz, ~320 KB SRAM, 4 MB PSRAM, 4 MB flash |
| Wireless | Wi-Fi 2.4 GHz only (b/g/n). **No 5 GHz, no Bluetooth radio** (the S2 has no BT silicon — beware tutorials assuming `BluetoothSerial`) |
| USB | USB-C, native USB peripheral on S2 |
| SWD pins to Flipper | Pin 10 → SWCLK (ESP32 GPIO1), Pin 12 → SWDIO (ESP32 GPIO2), Pin 9 → 3V3, Pin 11 → GND |
| External SWD header | 14-pin 0.05" (TC2050-style) for non-Flipper ARM targets |
| Buttons | BOOT (download mode) + RESET |
| Power | 3V3 from Flipper or 5 V from its own USB-C. Don't power both rails simultaneously if you can avoid it |
| Networking | mDNS hostname `blackmagic.local` in BM mode; SSID changes per firmware |

Rev1 vs rev2 silicon: identical from the operator's perspective; rev2 fixes a USB-C reversibility quirk. Third-party clones (DSTIKE WiFi Devboard, FZEasyMarauder, Marauder Mini) are pin-compatible — flash any of these firmwares onto them.

## Firmware mode matrix

| Firmware | What it turns the Devboard into | Default access |
| --- | --- | --- |
| **Black Magic Probe** (stock) | GDB server on TCP 2345, SWD to Flipper STM32 or external target | Wi-Fi AP `blackmagic` / pwd `iamwitcher`, mDNS `blackmagic.local`, USB CDC0 |
| **CMSIS-DAP** | DAP-Link USB-only debugger (use with `pyocd`, OpenOCD, VS Code cortex-debug) | USB only |
| **Marauder** (justcallmekoko/ESP32Marauder) | Wi-Fi pen-test suite: deauth, beacon flood, probe sniff, EAPOL/PMKID capture, evil portal, Karma | Driven from Flipper (`Apps → GPIO → ESP32 Marauder` FAP) or USB CDC |
| **Ghost ESP** | Modern Marauder fork with cleaner UI, BLE spam (S3 only — won't run BT on S2 silicon, but Wi-Fi side is current) | Same Flipper companion FAP path |
| **Bruce** | Multi-purpose: Wi-Fi attacks + IR + sub-GHz over GPIO + RFID — kitchen-sink offensive firmware | Standalone web UI / Flipper companion |
| **Evil Portal** | Single-purpose captive portal with templated landing pages on the SD card | Web UI + companion FAP |

Switching firmware: hold BOOT, tap RESET (release BOOT) -> S2 enters download mode -> use the firmware project's own flasher / `flash_args`. Do **not** write an arbitrary app `.bin` at `0x1000`; on ESP32-S2 that is the bootloader slot. For split images the usual Devboard layout is:

```bash
esptool.py --chip esp32s2 write_flash -z \
  0x1000 bootloader.bin \
  0x8000 partitions.bin \
  0xE000 boot_app0.bin \
  0x10000 firmware.bin
```

If the project ships one merged flash image, write it at the offset its docs specify (commonly `0x0`) or drag it into the on-board web flasher most of these projects ship.

## SWD / debugger flow (was in fap-development.md)

### One-time setup

1. Flipper: **Settings → System → Debug = ON**.
2. Plug Devboard into Flipper. Power it from USB-C (your PC).
3. Connect to Wi-Fi AP `blackmagic` / password `iamwitcher`. Or just use USB CDC.
4. mDNS hostname: `blackmagic.local`. GDB server on port `2345`. Web UI on port 80 to switch USB mode (BlackMagic vs DAP) and Wi-Fi STA/AP.

### Quick GDB session

```bash
# inside flipperzero-firmware checkout
./fbt get_blackmagic                        # auto-detect; prints connection string
./fbt blackmagic                            # spawn local proxy
arm-none-eabi-gdb -ex 'target extended-remote tcp:blackmagic.local:2345' \
                  build/f7-firmware-D/firmware.elf
(gdb) monitor swdp_scan
(gdb) attach 1
(gdb) c
```

For an external FAP, attach to the running firmware then `add-symbol-file dist/my_app.elf 0x<load_addr>` (load address printed in the CLI when the FAP starts; turn on Debug in Flipper Settings to see it).

### VS Code

`ufbt vscode_dist` drops `.vscode/launch.json` with two configurations:

- **Attach FW (blackmagic)** — works over Wi-Fi or USB CDC, autodetects.
- **Attach FW (DAP)** — USB-only, requires Devboard in DAP mode (web UI → switch).

Hit F5 → Flipper freezes at current PC → `c` to continue → reproduce the bug → backtrace as usual.

### When `furi_assert` fires

The assert handler stops the CPU. Attach the debugger, type `c` once to reach the assert point, then `bt` for the call stack. `info locals` and `up`/`down` work as you'd expect. The assert message is in `__furi_check_message` / `__furi_crash_message` globals — print them via `p __furi_check_message`.

### Reading logs

The Devboard exposes a second USB CDC interface dedicated to Flipper firmware logs (`furi_log_print_format`). In Black Magic mode on macOS, the Devboard usually appears as `/dev/cu.usbmodemblackmagic1` for GDB/console and `/dev/cu.usbmodemblackmagic3` for logs. Open the log port with `screen` or `minicom` at 230400 baud; Devboard log capture requires the Devboard's USB connection, not Wi-Fi.

### Debugging non-Flipper ARM targets

The 14-pin header is generic SWD. Wire SWCLK / SWDIO / GND / 3V3 to any Cortex-M target, scan with `monitor swdp_scan`, and you've turned the Devboard into a $30 BMP. Useful for reversing other dev boards, smart-locks with exposed test points, etc.

## Marauder / Ghost ESP / Bruce — the attack-platform side

This is where most operators spend their time with the Devboard. Below is the working surface; protocol detail and hashcat conversion live in the official Marauder wiki.

### Companion FAP

`Apps → GPIO → ESP32 Marauder` (or `Ghost ESP`, `Bruce` — same pattern, different menu tree). The FAP is a thin UART terminal: it forwards the on-screen menu to the ESP32 over the GPIO USART (pins 13/14) and renders status. SD-card config and capture files live on the **Devboard side** (its 4 MB flash) until you copy them off via web UI.

If the FAP isn't installed, every offensive feature is also reachable from the Devboard's USB CDC console — connect with `screen /dev/cu.usbmodem* 115200` and type the same commands.

### Wi-Fi attack workflow surface

| Operation | Marauder verb | Output |
| --- | --- | --- |
| Scan APs | `Sniff APs` | AP list with BSSID, channel, RSSI |
| Scan stations | `Sniff Stations` | Client MACs per AP |
| **Deauth** target AP/client | `Attack → Deauth` | Forged 802.11 deauth frames |
| **Beacon flood** | `Attack → Beacon Spam (List/Random/Rickroll)` | Visible SSID storm |
| **Probe spam** | `Attack → Probe` | Forged probe-request flood |
| **EAPOL / PMKID capture** | `Sniff → EAPOL` (handshake) or `PMKID` (single frame) | `.pcap` on Devboard SD/flash |
| **Evil Portal** | `Attack → Evil Portal` | Open AP + captive portal serving HTML/CSS/JS templates |
| **Karma / Probe-respond** | `Attack → Karma` | Replies to client probes claiming to be every requested SSID |
| Channel hop | `Settings → Channel` | Manual or auto |

PMKID / EAPOL → hashcat: pull the `.pcap` off the Devboard, run `hcxpcapngtool` to convert to `.hc22000`, feed `hashcat -m 22000`. None of that runs on the Devboard itself.

### Evil Portal templates

Templates are HTML/CSS/JS triplets stored on the Devboard flash under `marauder/portals/<name>/`. Common bundled set: `google`, `microsoft`, `starbucks`, `wifi`. Drop your own folder with `index.html` / `style.css` / `script.js`; pick it from `Attack → Evil Portal → <name>`. Captured form posts go to a log file pulled via web UI.

### Channel and regulatory notes

The ESP32-S2 is region-flexible — it transmits on the channels its firmware enables, not whatever the Flipper STM32's region setting says. The CC1101 region block on the Flipper does NOT apply to the Devboard. (Different MCU, different radio, different rules; the Devboard does what its firmware tells it.)

## BLE adjacency — where it actually lives

The S2 chip on the Wi-Fi Devboard **has no Bluetooth radio**. Anything BLE — Continuity spam, AirTag spoof, BadKB — comes from one of:

- The **Flipper's own** STM32WB55 BLE stack, via the `blebeacon` JS module (Momentum) or community FAPs (`BLE Spam`, `BLE Lego` etc.).
- A separate ESP32-S3 / ESP32-WROOM board (full BT/BLE-capable). Ghost ESP and Bruce both have ESP32-S3 builds for the boards that have BT silicon. The **stock Flipper Wi-Fi Devboard does not**.

Don't tell the operator "flash Ghost ESP for BLE spam on the WiFi Devboard." That doesn't work on rev1/rev2 hardware.

## CDC numbering when both are plugged

Plugging the Flipper AND a USB-C cable into the Devboard at once gives you four CDC interfaces on the host:

| Interface | Comes from | Default macOS path | Purpose |
| --- | --- | --- | --- |
| Flipper CDC0 | STM32 | `/dev/cu.usbmodemflip_*1` | CLI / RPC |
| Flipper CDC1 | STM32 | `/dev/cu.usbmodemflip_*3` | Flipper logs |
| Devboard CDC0 | ESP32-S2 | `/dev/cu.usbmodemblackmagic1` in Black Magic mode | BM GDB / console |
| Devboard CDC1 | ESP32-S2 | `/dev/cu.usbmodemblackmagic3` in Black Magic mode | Flipper logs via Devboard UART (Marauder firmwares use their own device names) |

`ls /dev/cu.usbmodem*` after plugging each one in separately is the fastest way to disambiguate.

## Compatible third-party boards

Wire-compatible with the same firmwares (Marauder / Ghost ESP / Bruce / Black Magic):

- **DSTIKE Flipper Wi-Fi Devboard** — most common clone, same ESP32-S2.
- **FZEasyMarauder** — kit form, sometimes ships with Marauder pre-flashed.
- **Marauder Mini** — smaller form factor, same chip.
- **ESP32-S3 boards** — *not* pin-compatible with the Flipper header but run the same Marauder/Ghost ESP/Bruce codebases with BT/BLE bonus.

## Useful repos

- [flipperdevices/flipperzero-firmware](https://github.com/flipperdevices/flipperzero-firmware) — for SDK-side debugging.
- [justcallmekoko/ESP32Marauder](https://github.com/justcallmekoko/ESP32Marauder) — Marauder source + flash binaries.
- [Spooks4576/Ghost_ESP](https://github.com/Spooks4576/Ghost_ESP) — Ghost ESP fork.
- [pr3y/Bruce](https://github.com/pr3y/Bruce) — multi-purpose Bruce firmware.
- [bigbrodude6119/flipper-zero-evil-portal](https://github.com/bigbrodude6119/flipper-zero-evil-portal) — Evil Portal companion FAP + ESP firmware.
- [UberGuidoZ/Flipper](https://github.com/UberGuidoZ/Flipper) — sprawling community resource pack including Marauder builds.

## When to use what

| Goal | Devboard firmware |
| --- | --- |
| Debug a FAP crash | Black Magic |
| Debug an external ARM dev board | Black Magic (14-pin header) |
| Set up a CI/headless debug rig | CMSIS-DAP |
| Wi-Fi recon / handshake capture | Marauder or Ghost ESP |
| Captive-portal demo | Evil Portal |
| One-firmware-does-many-things | Bruce |
| BLE spam | NOT this board — see [host-side.md](host-side.md) and JS `blebeacon` instead |
