# Video Game Module (RP2040, DVI-D, IMU)

The Video Game Module ("VGM") is a daughterboard that plugs into the Flipper's GPIO header and adds three new toys: a Raspberry Pi RP2040, a DVI-D output, and a 6-axis motion sensor. Officially open-source hardware + firmware, made in collaboration with Raspberry Pi.

You can think of it three ways:

1. **A peripheral controlled by a host FAP.** The Flipper sends commands over UART; the VGM does the heavy work and outputs video.
2. **An almost-Pico.** Standalone RP2040 dev board with USB-C, 14-pin GPIO breakout, and an IMU. Drop a `.uf2` over USB and run any Pico SDK / MicroPython / CircuitPython project.
3. **A second screen for the Flipper.** The default firmware mirrors the 128×64 LCD up to a 640×480 DVI-D output.

## Hardware specs

| Part | Detail |
| --- | --- |
| MCU | Raspberry Pi RP2040 — dual-core ARM Cortex-M0+ @ 133 MHz (slightly overclocked from the 125 MHz Pico baseline to get DVI timings clean) |
| RAM | 264 KB on-chip SRAM |
| Flash | 16 MB external QSPI |
| Video | DVI-D 640×480 @ 60 Hz over a full-size HDMI connector (driven by PIO using the [PicoDVI](https://github.com/Wren6991/PicoDVI) approach) |
| IMU | TDK **ICM-42688-P** — 6-axis (3-axis gyro + 3-axis accel), connected over SPI to BOTH the RP2040 and the Flipper STM32WB55 |
| USB | USB-C, RP2040's native USB. Acts as device or host (no PD support, so external power = unsupported) |
| Buttons | BOOT (UF2 mode) + RESET |
| Connectors | 14-pin GPIO breakout, full-size HDMI, USB-C, plus the Flipper GPIO mating header underneath |
| Power | 3.3 V from Flipper or 5 V from USB |

## GPIO map (RP2040 numbering)

| GP | Purpose | Exposed where? |
| --- | --- | --- |
| GP0–GP7 | Free GPIO | 14-pin breakout (and pins 2–7 also wire to the IMU's CS / interrupts) |
| GP8–GP15 | DVI-D video out (PIO-driven) | INTERNAL — do not touch |
| GP16, GP17 | Free GPIO | 14-pin breakout |
| GP18–GP20 | DVI-D video out | INTERNAL |
| GP21, GP22 | Free GPIO | 14-pin breakout |
| GP23–GP25 | Used internally on a Pi Pico, **free on VGM** | 14-pin breakout |
| GP26–GP28 | Free GPIO, ADC-capable | 14-pin breakout |
| GP29 | Used on a Pi Pico for VSYS sense, **free on VGM** | 14-pin breakout |

So if you're porting a Pi Pico project to the VGM:

- Anything that wanted GP8–GP15 or GP18–GP20 has to move (those are video pins).
- Anything that used GP23/24/25/29 (which the Pico hides) is now actually wired to a header pin — bonus pins!

## Operating modes

### Mode 1 — Default firmware: Flipper screen mirror + Air Mouse + Air Arkanoid

Out of the box, the VGM ships with firmware that:

- Detects the Flipper over UART, mirrors the 128×64 screen scaled up to 640×480.
- Streams IMU data back to the Flipper for built-in apps (`Air Mouse`, `Air Arkanoid`).
- Exposes a USB CDC console for diagnostics.

You don't need to write any code to use this — the user just plugs it in and starts an `Air *` app on the Flipper.

### Mode 2 — Custom RP2040 firmware (your own `.uf2`)

This is where the fun lives. You write firmware for the RP2040 with the Pico SDK (or MicroPython, CircuitPython, Rust embassy, whatever), then flash it via UF2.

Flash flow:

1. Hold BOOT on the VGM, tap RESET, release BOOT — RP2040 mounts as `RPI-RP2` USB drive.
2. Drag your `.uf2` onto it.
3. Drive remounts as your firmware. Done.

Or via `picotool` over USB.

A minimal Pico SDK template that uses PicoDVI for video:

```cmake
# CMakeLists.txt
cmake_minimum_required(VERSION 3.13)
include(pico_sdk_import.cmake)
project(vgm_demo)
pico_sdk_init()

# PicoDVI as a fetchcontent / submodule:
add_subdirectory(libdvi)

add_executable(vgm_demo main.c)
target_link_libraries(vgm_demo
    pico_stdlib
    pico_multicore
    hardware_pio
    hardware_dma
    libdvi)

pico_add_extra_outputs(vgm_demo)   # generates .uf2
```

```c
// main.c — sketch only; refer to PicoDVI examples for full timings
#include "pico/stdlib.h"
#include "dvi.h"
#include "dvi_serialiser.h"

#define DVI_DEFAULT_SERIAL_CONFIG vgm_dvi_cfg

static const struct dvi_serialiser_cfg vgm_dvi_cfg = {
    .pio = pio0,
    .sm_tmds = {0, 1, 2},
    .pins_tmds = {12, 18, 14},   // VGM-specific lane mapping
    .pins_clk = 8,
    .invert_diffpairs = true,
};

int main() {
    set_sys_clock_khz(252000, true);   // overclock for clean 640x480
    dvi_init(&vgm_dvi_cfg);
    while (true) {
        // render scanline
    }
}
```

The exact `pins_tmds` mapping for the VGM is documented in the [official VGM firmware repo](https://github.com/flipperdevices/flipperzero-game-engine-vgm-fw) — copy from there rather than guessing. The internal video pins are GP8–GP15 + GP18–GP20.

### Mode 3 — Host FAP + VGM peripheral

Most "Flipper game with a TV out" apps split work across two MCUs:

- **STM32WB55 (host FAP):** game logic, score, persistence, GUI on the 128×64 LCD.
- **RP2040 (VGM firmware):** rendering at 640×480 + reading the IMU + sending input back.

They talk over UART (USART1 on Flipper pins 13/14, which when the VGM is mounted maps to a free RP2040 UART).

Recommended starting point: the official **flipper-game-engine-vgm-fw** project, which provides a 320×240 framebuffer abstraction (upscaled to 640×480 for clean pixel doubling), a sprite/tilemap layer, and a UART command protocol.

```c
// host FAP: send a "draw sprite" command to VGM
typedef struct __attribute__((packed)) {
    uint8_t  cmd;       // 0x10 = draw_sprite
    uint8_t  sprite_id;
    int16_t  x, y;
    uint8_t  flags;     // flip, palette
} VgmDrawSprite;

void vgm_send(VgmDrawSprite* s) {
    furi_hal_serial_tx(serial_handle, (uint8_t*)s, sizeof(*s));
}
```

If you go this route, version your protocol from day one — the VGM and host can be flashed independently.

## ICM-42688-P IMU

A high-precision 6-axis MEMS IMU (3-axis gyro + 3-axis accel). It sits on the SPI bus shared between the Flipper STM32 and the RP2040. Whichever MCU has `CS` low at the moment owns the conversation; the host FAP and VGM firmware have to coordinate.

Datasheet defaults that matter:

- Gyro full-scale options: ±15.625 / 31.25 / 62.5 / 125 / 250 / 500 / 1000 / 2000 dps.
- Accel full-scale options: ±2 / 4 / 8 / 16 g.
- Output Data Rate up to 32 kHz; for games, 200–500 Hz is plenty.
- 16-bit ADC on each axis.

Reading from a host FAP:

```c
// pseudocode — wrap furi_hal_spi_acquire / _release / _bus_trx
uint8_t tx[2] = { ICM42688_REG_WHO_AM_I | 0x80, 0 };
uint8_t rx[2] = {0};
furi_hal_spi_acquire(&furi_hal_spi_bus_handle_external);
furi_hal_spi_bus_trx(&furi_hal_spi_bus_handle_external, tx, rx, 2, FuriHalSpiTimeout);
furi_hal_spi_release(&furi_hal_spi_bus_handle_external);
// rx[1] should be 0x47 for ICM-42688-P
```

The IMU is mounted on the same package as the radio — it uses the SPI lines the Flipper exposes on the GPIO header (pins 2–5).

## IMU game patterns

The IMU is what makes the VGM more than "tiny console". Use it:

- **Tilt steering** (Air Arkanoid clone): low-pass the accel, map X-axis tilt to paddle position.
- **Aiming reticle** (Air Mouse pattern): integrate gyro for relative pointing, recenter on a button press to fight drift.
- **Gesture detection**: shake-to-shuffle, flick-to-fire. Threshold on accel magnitude minus gravity, debounce ~150 ms.
- **Spaceflight roll/pitch/yaw**: Madgwick or Mahony filter on host. Send orientation quaternion to VGM as the camera matrix.

Drift management: integrating raw gyro will drift several degrees per minute. Either complementary-filter against accel (cheap) or do proper sensor fusion (Madgwick, ~150 lines of C). For party games, raw integration with a "press to recenter" button is fine.

## USB-C port (host or device)

The RP2040's USB peripheral is exposed on the VGM's USB-C connector. Per-mode use:

- **Device:** appears to a host PC as whatever you implement. UF2 bootloader, CDC console, HID gamepad, mass storage, MIDI, custom vendor class.
- **Host:** plug a USB joystick or keyboard into the VGM and consume HID. RP2040 USB host is well-supported in TinyUSB.

USB-C **PD is not supported** — don't try to negotiate higher voltages. The RP2040 just expects 5 V.

A common combo for a Flipper game is "VGM presents itself as a USB HID gamepad to a separate host PC, while still running the Flipper game on the LCD" — the VGM acts as a USB-shaped translator.

## Standalone use (no Flipper attached)

The VGM stands alone if you power it via USB-C. You lose:

- Communication with the Flipper UI (obviously).
- Power from the Flipper battery.

You keep:

- All RP2040 GPIO on the breakout.
- DVI-D output.
- The IMU (still on SPI; the Flipper-side CS becomes meaningless).
- USB-C (device or host).

Great for using the VGM as a generic Pi Pico clone with HDMI when you don't want to build out a PicoDVI board yourself.

## Useful repos and references

- [flipperdevices/flipperzero-game-engine-vgm-fw](https://github.com/flipperdevices/flipperzero-game-engine-vgm-fw) — official VGM-side firmware with sprite/tilemap engine.
- [flipperdevices/flipper-game-engine](https://github.com/flipperdevices/flipper-game-engine) — host-side library, integrates with FAPs.
- [Wren6991/PicoDVI](https://github.com/Wren6991/PicoDVI) — the PIO-based DVI driver everything builds on.
- [TDK ICM-42688-P datasheet](https://invensense.tdk.com/products/motion-tracking/6-axis/icm-42688-p/) — register map and timing diagrams.
- [Pi Pico C/C++ SDK](https://www.raspberrypi.com/documentation/microcontrollers/c_sdk.html) — anything that compiles for the Pico generally compiles for the VGM if you avoid the video pins.

If you're prototyping a game and you keep getting "the screen is too small": use the VGM. If you're prototyping a sensor / radio / IO project: skip it; the bare Flipper is faster to iterate on.
