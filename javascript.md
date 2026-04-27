# JavaScript on Flipper Zero (mJS)

The Flipper firmware ships a tiny JavaScript engine — **mJS** by Cesanta — wrapped as a system app (`js_app`). You drop a `.js` file into `apps/Scripts/` on the SD card, run it from `Apps → Scripts`, and the script can import C-backed modules through `require()`.

This is the right tool when you want quick prototypes, scripted radio/IO sequences, or a one-off prank. For low-latency loops or anything graphically dense, build a native FAP instead — see [fap-development.md](fap-development.md).

## What mJS is and isn't

mJS is **ES5.1-ish** with a bunch of stuff missing. Treat it as "JavaScript shaped" rather than full JS.

Supported:

- `let`, `const`, `var` (`let`/`const` aren't really block-scoped, just available syntactically)
- Functions, closures, recursion
- Strings, numbers (doubles), booleans, null, undefined
- Object literals, array literals
- `for`, `while`, `do/while`, `if/else`, `switch`, `?:`
- `try/catch/finally`, `throw new Error("…")`
- `require()` — Flipper's loader for native modules

Not supported (or trapdoors):

- `Promise`, `async`/`await`. Use the `event_loop` module's callbacks for async work.
- Classes (`class Foo {}`). Use prototype-based constructors if you need OO.
- Template literals (backticks). Concatenate with `+`.
- Spread / rest (`...args`).
- `Map`, `Set`, `WeakMap`, generators, iterators.
- `JSON.parse` / `JSON.stringify` — present in some forks (Momentum), absent in stock OFW. Don't rely on it. Roll your own or use FFF format.
- `RegExp` — extremely limited or missing depending on firmware. Avoid.
- `for…of`. Use `for (let i = 0; i < arr.length; i++)`.
- `console.log` — use `print(...)` instead. The output goes to the on-device debug console and CLI `log`.

When in doubt, check what compiles. mJS will throw at parse time on unsupported syntax.

## Hello world

```javascript
// Save as: apps/Scripts/hello.js
print("hello, dolphin");
let n = 3 + 4;
print("n =", n);
```

Run from `Apps → Scripts → hello.js`. Output appears on screen and on the CLI `log` stream.

## `require()` — module loader

```javascript
let badusb = require("badusb");
let math   = require("math");
let notify = require("notification");
```

Modules are compiled C/C++ shipped as `.fal` files in firmware. Loading one allocates RAM (~1–32 KiB depending on module). Some modules **must be required after** another — most notably any `gui/*` submodule must come after `event_loop` and `gui`:

```javascript
let eventLoop = require("event_loop");      // ALWAYS before gui
let gui       = require("gui");
let submenu   = require("gui/submenu");     // gui submodules require gui first
```

## Module reference

Module availability varies by firmware fork. The matrix below is a rough snapshot — when in doubt, check `applications/system/js_app/modules/` in the firmware you target.

| Module | OFW | Momentum | Unleashed | RogueMaster | Xtreme |
| --- | --- | --- | --- | --- | --- |
| `event_loop` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `gui` + submodules | ✅ | ✅ | partial | partial | partial |
| `gpio` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `badusb` | ✅ | ✅ (+`quit`/`altPrint`) | ✅ | ✅ | ✅ |
| `subghz` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `serial` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `storage` | ✅ | ✅ (+`append`) | partial | partial | partial |
| `notification` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `math` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `flipper` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `usbdisk` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `keyboard` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `blebeacon` | — | ✅ | partial | partial | — |
| `widget` (legacy) | partial | partial | partial | — | partial |

### `event_loop` — the async backbone

mJS has no `Promise`. The `event_loop` module gives you an explicit run loop with subscriptions and timers.

```javascript
let eventLoop = require("event_loop");

let timer = eventLoop.timer("periodic", 1000);  // 1 Hz
eventLoop.subscribe(timer, function (sub, _, ctx) {
    print("tick", ctx.count++);
    if (ctx.count > 5) eventLoop.stop();
}, { count: 0 });

eventLoop.run();
```

Methods:

- `eventLoop.subscribe(source, callback, ...ctx)` — `source` is an event-bearing object (timer, GUI view's signal, GPIO interrupt). Extra args are forwarded to the callback as positional context. Returns a `Subscription` you can `.cancel()`.
- `eventLoop.timer(kind, ms)` — `kind` is `"periodic"` or `"oneshot"`.
- `eventLoop.run()` / `eventLoop.stop()` — must call `run()` to actually pump.

### `gui` — full UI like a native FAP

```javascript
let eventLoop = require("event_loop");
let gui       = require("gui");
let submenu   = require("gui/submenu");
let dialog    = require("gui/dialog");

let views = {
    menu: submenu.makeWith({
        header: "Mischief Menu",
        items: ["Beep", "Flash LED", "Bail"],
    }),
    confirmExit: dialog.makeWith({
        header: "Bail?",
        text: "Sure you want to leave?",
        left: "No", right: "Yes",
    }),
};

eventLoop.subscribe(views.menu.chosen, function (_sub, idx) {
    if (idx === 0) require("notification").success();
    else if (idx === 1) require("notification").blink("blue", "short");
    else gui.viewDispatcher.switchTo(views.confirmExit);
});

eventLoop.subscribe(views.confirmExit.chosen, function (_sub, choice) {
    if (choice === "right") eventLoop.stop();
    else gui.viewDispatcher.switchTo(views.menu);
});

eventLoop.subscribe(gui.viewDispatcher.navigation, function () {
    gui.viewDispatcher.switchTo(views.menu);
});

gui.viewDispatcher.switchTo(views.menu);
eventLoop.run();
```

Submodules (each `require("gui/<name>")` returns a factory with `.make()` / `.makeWith({...})`):

- `gui/loading` — animated hourglass (full screen)
- `gui/empty_screen` — blank view, useful as a placeholder
- `gui/submenu` — scrollable list of strings
- `gui/text_input` — on-screen keyboard, returns a string. Props: `header`, `defaultText`, `defaultTextClear`, `minLength`, `maxLength`.
- `gui/byte_input` — hex bytes, fixed length
- `gui/text_box` — read-only multiline text
- `gui/dialog` — header + text + up to 3 button labels (left/center/right)
- `gui/file_picker` — browses `/ext`, returns chosen path
- `gui/widget` — composite of small elements (text frags, icons, buttons, scroll boxes); add via `addText("hello", { x:0, y:0, font:"primary", align:"left" })` and friends

The factory's `make()` instances expose signals (`chosen`, `input`, `navigation`) that you `.subscribe(...)` through `event_loop`.

### `gpio` — GPIO control

```javascript
let gpio = require("gpio");

let pa7 = gpio.get("PA7");        // by Flipper pin name
pa7.init({ direction: "out", outMode: "push_pull" });
pa7.write(true);

let pa6 = gpio.get("PA6");
pa6.init({ direction: "in", pull: "up" });
print("PA6 =", pa6.read());

let pc3 = gpio.get("PC3");
pc3.init({ direction: "in", pull: "no", edge: "rising" });
let eventLoop = require("event_loop");
eventLoop.subscribe(pc3.events, function () { print("edge!"); });
```

ADC variant (`PA1`, `PC0`–`PC3` etc.):

```javascript
pc3.init({ direction: "in", pull: "no" });
let mv = pc3.readAnalog();   // millivolts
```

### `subghz` — Sub-GHz radio scripting

```javascript
let subghz = require("subghz");

subghz.setup();                                 // power up CC1101
print("freq", subghz.getFrequency(), "Hz");
print("rssi", subghz.getRssi(), "dBm");

subghz.setFrequency(433920000);
subghz.setRx();
delay(2000);
subghz.setIdle();

subghz.transmitFile("/ext/subghz/garage.sub");  // replays a saved capture
```

Key methods:

- `setup()`, `setIdle()`, `setRx()` — power state.
- `setFrequency(hz)` → returns the actually-set frequency (it snaps to the CC1101 step).
- `getFrequency()`, `getRssi()`, `getState()`, `isExternal()`.
- `transmitFile(path)` → replays a `.sub` file. Returns `true` on success, `undefined`/error if the file is invalid or the band is region-blocked.

Region transmit blocks apply equally to JS — if the region forbids it, `transmitFile` errors out. See [limits.md](limits.md) → "Region transmit blocks".

### `badusb` — keyboard emulation

```javascript
let badusb = require("badusb");

badusb.setup({ vid: 0x1234, pid: 0x5678,
               mfrName: "Flipper", prodName: "Mischief",
               layoutPath: "/ext/badusb/assets/layouts/en-US.kl" });

while (!badusb.isConnected()) delay(100);

badusb.println("echo hello from a dolphin");
badusb.press("CTRL", "ALT", "T");           // open a terminal
delay(500);
badusb.print("uname -a", 50);               // 50 ms between keys (slow typists)
badusb.press("ENTER");
badusb.quit();                              // release USB so usbdisk etc. can take over
```

Modifier set: `CTRL`, `SHIFT`, `ALT`, `GUI`. Special keys: arrow keys, `ENTER`, `ESC`, `BACKSPACE`, `TAB`, `DELETE`, `HOME`, `END`, `INSERT`, `PAGEUP/DOWN`, `CAPSLOCK`, `NUMLOCK`, `SCROLLLOCK`, `PRINTSCREEN`, `PAUSE`, `SPACE`, `MENU`, `F1`–`F24`, `NUM0`–`NUM9`. Or pass a numeric HID code: `badusb.press(0x47)`.

`altPrint` / `altPrintln` use the Alt+Numpad input method on Windows for Unicode characters.

### `serial` — UART scripting

```javascript
let serial = require("serial");
serial.setup("usart", 115200);

serial.write("AT\r\n");
let line = serial.readln(2000);    // 2000 ms timeout, returns string or undefined
print("got:", line);

serial.end();
```

Targets: `"usart"` (USART1 on pins 13/14), `"lpuart"` (LPUART1, only on some hardware revs / forks).

### `notification`

```javascript
let n = require("notification");
n.success();        // green LED + chirp
n.error();          // red LED + sad
n.blink("blue", "short");   // colors: red/green/blue/yellow/cyan/magenta; lengths: short/long
```

### `storage` — SD card files

```javascript
let storage = require("storage");

let f = storage.openFile("/ext/apps_data/my_script/state.fff", "w", "create_always");
f.write("Filetype: My state\nVersion: 1\nCount: 7\n");
f.close();

let r = storage.openFile("/ext/apps_data/my_script/state.fff", "r", "open_existing");
let txt = r.read("string", 1024);   // read up to 1024 bytes as a string
r.close();
print(txt);
```

Older firmware uses different verbs (`storage.read(path)`, `storage.write(path, data)`). Check your fork.

### `flipper` — device info

```javascript
let f = require("flipper");
print(f.getModel(), f.getName(), f.getBatteryCharge());
```

### `math` — numeric helpers

```javascript
let m = require("math");
print(m.sin(m.PI / 2), m.sqrt(2), m.floor(3.7));
```

mJS's built-in `Math` is incomplete. Use this module.

### `keyboard` — text input from inside a script

```javascript
let kb = require("keyboard");
let s = kb.text({ header: "Your name", default: "anon", maxLen: 16 });
print("hi", s);
```

### `usbdisk` — expose an .img as a USB mass-storage device

```javascript
let disk = require("usbdisk");
require("badusb").quit();        // free the USB stack first
disk.start("/ext/disks/payload.img");
delay(60000);
disk.stop();
```

Useful for "appear as a thumb drive, autorun on the host". Pair with BadUSB to type `wmic diskdrive ...`.

### `blebeacon` (Momentum)

```javascript
let beacon = require("blebeacon");
beacon.setData([0x02, 0x01, 0x06, 0x09, 0x09, 0x46, 0x6c, 0x69, 0x70, 0x70, 0x65, 0x72]);
beacon.start();
delay(10000);
beacon.stop();
```

Used for Apple "Continuity" pranks (AirTag spoof, Bluetooth Find My noise). Some forks ship a built-in app; from JS it's a low-level primitive.

## Sleep / delay

`delay(ms)` is a global blocking sleep. For non-blocking, use an `event_loop` timer.

## Error handling

```javascript
try {
    require("subghz").setFrequency(99000000);   // outside Flipper bands
} catch (e) {
    print("nope:", e.message);
}
```

Native modules `throw` an error with a `.message` string when something is structurally wrong. Region-block errors look like `"frequency 99000000 is not in operational bands"` or similar.

## Distribution

JS scripts are just files. Drop them in `apps/Scripts/` (or `apps_data/<your_namespace>/`). They show up under `Apps → Scripts`. No build step, no signing, no API version dance — but they tie you to the available modules in your firmware.

For shareable JS apps, ship a folder under `apps/Scripts/<name>/` with `main.js` plus any `*.fff` data files, and document the firmware fork(s) you tested on.
