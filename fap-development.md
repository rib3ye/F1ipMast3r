# FAP development (native C, ufbt, Furi)

Everything for building a native Flipper Application Plugin: project layout, the manifest, the core idiomatic patterns, drawing, audio, storage, threading rules, game architecture, and debugging via the Wi-Fi Devboard.

## Project skeleton

```
my_app/
├── application.fam      # build manifest, REQUIRED, in repo root
├── my_app.c             # entry point: my_app_main(void* p)
├── my_app.h
├── icons/               # 1-bit PNGs auto-compiled to icon assets
│   └── my_app_10px.png  # 10x10 app menu icon
└── images/              # extra image assets (set via fap_icon_assets)
    └── .gitkeep
```

## `application.fam`

```python
App(
    appid="my_app",
    name="My App",
    apptype=FlipperAppType.EXTERNAL,
    entry_point="my_app_main",
    stack_size=2 * 1024,
    fap_category="Tools",                # bucket on SD card under apps/<category>/
    fap_icon="icons/my_app_10px.png",
    fap_icon_assets="images",            # build all PNGs in this folder into icons
    fap_version="0.1",
    fap_description="Does the thing",
    fap_author="you",
    fap_weburl="https://example.com",
    requires=["gui", "storage", "notification"],
)
```

Other useful fields:

- `apptype=FlipperAppType.PLUGIN` + `fal_embedded=True` — plugin packaged inside a host FAP, extracted to `apps_assets/<host_appid>/` at startup.
- `apptype=FlipperAppType.EXTERNAL` is what you want for normal user apps. `MENUEXTERNAL` puts it in the main menu.
- `sources=["*.c*", "!plugins"]` — exclude subfolders from the build.
- `fap_extbuild=[ExtFile(path="generated.c", command="python gen.py ${FAP_SRC_DIR}")]` — preprocessor / codegen step.
- `fap_libs=["mbedtls"]` — link against firmware-provided libs.

## Entry point

```c
#include <furi.h>

int32_t my_app_main(void* p) {
    UNUSED(p);
    // ... build context, run loop, cleanup ...
    return 0;
}
```

The function name in `entry_point=` must match. Return 0 on clean exit, nonzero to surface an error.

## Idiomatic FAP architecture (ViewDispatcher pattern)

Most apps are: an app context struct + ViewDispatcher juggling 2–6 named views, with optional SceneManager when the navigation graph gets non-trivial.

```c
// scenes.h — usually generated. Each scene needs on_enter / on_event / on_exit.
typedef enum { MyAppSceneStart, MyAppSceneSettings, MyAppSceneCount } MyAppScene;

void my_app_scene_start_on_enter(void* ctx);
bool my_app_scene_start_on_event(void* ctx, SceneManagerEvent event);
void my_app_scene_start_on_exit(void* ctx);
// ...repeat for each scene...

void (*const my_app_scene_on_enter_handlers[])(void*) = {
    my_app_scene_start_on_enter,
    my_app_scene_settings_on_enter,
};
bool (*const my_app_scene_on_event_handlers[])(void*, SceneManagerEvent) = {
    my_app_scene_start_on_event,
    my_app_scene_settings_on_event,
};
void (*const my_app_scene_on_exit_handlers[])(void*) = {
    my_app_scene_start_on_exit,
    my_app_scene_settings_on_exit,
};
const SceneManagerHandlers app_scene_handlers = {
    .on_enter_handlers = my_app_scene_on_enter_handlers,
    .on_event_handlers = my_app_scene_on_event_handlers,
    .on_exit_handlers  = my_app_scene_on_exit_handlers,
    .scene_num = MyAppSceneCount,
};

typedef enum { ViewMain, ViewSettings, ViewAbout, ViewCount } AppView;

typedef struct {
    Gui* gui;
    NotificationApp* notifications;
    Storage* storage;
    ViewDispatcher* view_dispatcher;
    SceneManager* scene_manager;

    Submenu* submenu;
    Widget* about;
    // ... your custom views ...
} App;

static bool app_back_event(void* ctx) {
    App* app = ctx;
    return scene_manager_handle_back_event(app->scene_manager);
}

static bool app_custom_event(void* ctx, uint32_t event) {
    App* app = ctx;
    return scene_manager_handle_custom_event(app->scene_manager, event);
}

static void app_tick_event(void* ctx) {
    App* app = ctx;
    scene_manager_handle_tick_event(app->scene_manager);
}

int32_t my_app_main(void* p) {
    UNUSED(p);
    App* app = malloc(sizeof(App));

    app->gui = furi_record_open(RECORD_GUI);
    app->notifications = furi_record_open(RECORD_NOTIFICATION);
    app->storage = furi_record_open(RECORD_STORAGE);

    app->view_dispatcher = view_dispatcher_alloc();
    app->scene_manager = scene_manager_alloc(&app_scene_handlers, app);

    view_dispatcher_set_event_callback_context(app->view_dispatcher, app);
    view_dispatcher_set_navigation_event_callback(app->view_dispatcher, app_back_event);
    view_dispatcher_set_custom_event_callback(app->view_dispatcher, app_custom_event);
    view_dispatcher_set_tick_event_callback(app->view_dispatcher, app_tick_event, 100);

    view_dispatcher_attach_to_gui(app->view_dispatcher, app->gui, ViewDispatcherTypeFullscreen);

    app->submenu = submenu_alloc();
    view_dispatcher_add_view(app->view_dispatcher, ViewMain, submenu_get_view(app->submenu));
    // ... add more views ...

    scene_manager_next_scene(app->scene_manager, MyAppSceneStart);
    view_dispatcher_run(app->view_dispatcher);

    // Teardown — order matters: remove from dispatcher before freeing each view.
    view_dispatcher_remove_view(app->view_dispatcher, ViewMain);
    submenu_free(app->submenu);
    scene_manager_free(app->scene_manager);
    view_dispatcher_free(app->view_dispatcher);

    furi_record_close(RECORD_NOTIFICATION);
    furi_record_close(RECORD_STORAGE);
    furi_record_close(RECORD_GUI);
    free(app);
    return 0;
}
```

In real apps each scene goes in its own file under `scenes/`, and `application.fam` lists them via `sources=["*.c", "scenes/*.c"]`. Look at firmware's `applications/main/subghz/scenes/` for canonical examples.

Available view types (modules): `Submenu`, `VariableItemList`, `TextInput`, `ByteInput`, `NumberInput`, `Popup`, `DialogEx`, `Widget`, `TextBox`, `Loading`, `Menu`, `ButtonMenu`, `ButtonPanel`, `EmptyScreen`, `FileBrowser`. Each has a `*_alloc` / `*_free` / `*_get_view` triplet.

For "I just want to draw stuff myself" apps, skip ViewDispatcher and use a raw `ViewPort` with a `FuriMessageQueue<InputEvent>`.

## Drawing on the canvas (raw ViewPort path)

```c
static void draw_callback(Canvas* canvas, void* ctx) {
    GameState* state = ctx;
    canvas_clear(canvas);
    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, 2, 10, "Hello, dolphin");
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_box(canvas, state->x, state->y, 4, 4);
    canvas_draw_frame(canvas, 0, 0, 128, 64);
}

static void input_callback(InputEvent* event, void* ctx) {
    FuriMessageQueue* q = ctx;
    furi_message_queue_put(q, event, FuriWaitForever);
}

ViewPort* vp = view_port_alloc();
view_port_draw_callback_set(vp, draw_callback, state);
view_port_input_callback_set(vp, input_callback, queue);
gui_add_view_port(gui, vp, GuiLayerFullscreen);
```

Canvas API highlights:

- `canvas_draw_str / _aligned`, `canvas_draw_str_n` (length-bounded)
- `canvas_draw_dot / _box / _frame / _line / _circle / _disc / _rbox / _rframe`
- `canvas_draw_icon / _icon_animation / _xbm` (XBM lets you embed inline bitmaps)
- `canvas_set_color(canvas, ColorBlack | ColorWhite)`
- `canvas_set_font(canvas, FontPrimary | FontSecondary | FontKeyboard | FontBigNumbers)`
- `canvas_invert_color`, `canvas_set_bitmap_mode`

After updating state, call `view_port_update(vp)` to request a redraw. The GUI service throttles to ~30 FPS.

## Furi primitives

| API | What it is |
| --- | --- |
| `FuriThread` | Wrapped FreeRTOS task. Set name, stack, callback, run. Always `furi_thread_join + free`. |
| `FuriMutex` | Recursive or non-recursive mutex. `acquire/release` with timeout. |
| `FuriMessageQueue` | Thread-safe queue of fixed-size items. Use for input events, work items, IPC. |
| `FuriTimer` | One-shot or periodic. Fires on the timer service thread (not ISR). |
| `FuriEventFlag` | 32-bit flag set, like a tiny eventfd. |
| `FuriSemaphore` | Counting / binary semaphore. |
| `FuriRecord` | The system service registry. `furi_record_open(RECORD_GUI)` etc. Always pair `_open` with `_close`. |
| `FuriString` | `mlib`-backed string with COW; use `furi_string_alloc/printf/cat/free`. |
| `furi_hal_random_*` | Hardware RNG. |
| `furi_log_print_format` | Logger, surfaced via the Flipper log CDC / `log` CLI, or via the Black Magic Devboard log CDC when debugging through the board. |

Do NOT call FreeRTOS APIs directly from app code — use the Furi wrappers for portability.

### Threading rules

- App entry runs on its own task. Most things (drawing, GUI, NotificationService calls) are fine to do inline.
- The GUI is a service: do not block its callbacks. Drawing must be fast (<16 ms ideally). Keep heavy work on a worker thread and `view_port_update` from there.
- ISR context is rare in app code, but if you write a custom GPIO interrupt: use `_isr` variants (`furi_message_queue_put` is ISR-safe), keep it short, never call `printf` / `furi_log`.
- Stack defaults are tight. If you crash with weird memory corruption inside string ops, bump `stack_size` to 4 KiB first.

## Storage

```c
Storage* storage = furi_record_open(RECORD_STORAGE);
File* f = storage_file_alloc(storage);
storage_file_open(f, EXT_PATH("apps_data/my_app/save.dat"),
                  FSAM_WRITE, FSOM_CREATE_ALWAYS);
storage_file_write(f, &state, sizeof(state));
storage_file_close(f);
storage_file_free(f);
furi_record_close(RECORD_STORAGE);
```

Path macros:

- `EXT_PATH("…")` → `/ext/…` (microSD)
- `INT_PATH("…")` → `/int/…` (internal flash, ~30 KB free, careful)
- `ANY_PATH("…")` → searches both
- `APP_DATA_PATH("file")` inside a FAP → `/ext/apps_data/<appid>/file` (auto-namespaced)
- `APP_ASSETS_PATH("file")` → `/ext/apps_assets/<appid>/file` (read-only assets bundled via `fap_extbuild`)

For Flipper Format Files, prefer the higher-level `flipper_format_*` API (handles versioning + key=value parsing for you).

## NotificationService

```c
NotificationApp* notifications = furi_record_open(RECORD_NOTIFICATION);
notification_message(notifications, &sequence_success);    // green LED + happy chirp
notification_message(notifications, &sequence_error);      // red LED + sad chirp
notification_message_block(notifications, &sequence_blink_red_100);  // synchronous
furi_record_close(RECORD_NOTIFICATION);
```

You can compose your own `NotificationSequence`:

```c
const NotificationSequence my_seq = {
    &message_red_255, &message_blue_255, &message_delay_50,
    &message_red_0,   &message_blue_0,   &message_delay_100,
    &message_vibro_on, &message_delay_50, &message_vibro_off,
    NULL,
};
```

## GPIO

```c
#include <furi_hal_gpio.h>
#include <furi_hal_resources.h>

furi_hal_gpio_init(&gpio_ext_pa7, GpioModeOutputPushPull, GpioPullNo, GpioSpeedLow);
furi_hal_gpio_write(&gpio_ext_pa7, true);

furi_hal_gpio_init(&gpio_ext_pa6, GpioModeInterruptRise, GpioPullUp, GpioSpeedLow);
furi_hal_gpio_add_int_callback(&gpio_ext_pa6, my_isr, ctx);

// Important: always restore Analog/NoPull when done so you don't leak power.
furi_hal_gpio_init(&gpio_ext_pa6, GpioModeAnalog, GpioPullNo, GpioSpeedLow);
```

The `gpio_ext_*` symbols map to the external GPIO header — see [SKILL.md](SKILL.md) cheatsheet for pin numbers.

For SPI/I2C/UART, prefer the high-level APIs (`furi_hal_spi_acquire/release`, `furi_hal_i2c_*`, `furi_hal_serial_*`). The peripheral is bus-managed — don't `furi_hal_bus_disable` anything from the always-on or on-demand list.

## Audio

Single oscillator buzzer. No PCM, no mixing — you sequence pure tones.

```c
if (furi_hal_speaker_acquire(1000)) {  // ms timeout
    furi_hal_speaker_start(440.0f, 1.0f);  // freq Hz, volume 0–1
    furi_delay_ms(200);
    furi_hal_speaker_stop();
    furi_hal_speaker_release();
}
```

Always `acquire` before `start`. The `acquire` call can fail if another app holds the speaker (e.g. NotificationService). For chiptune, just sequence frequencies on a `FuriTimer`. If you need polyphony… you don't have polyphony. Pick a lead voice or fake it with arpeggios.

## Game patterns

Architectural template that fits Snake, Tetris, T-Rex, asteroids, breakout, and most jam-scale games:

```c
typedef struct {
    int32_t player_x, player_y;
    bool game_over;
    uint32_t score;
} GameState;

typedef enum {
    EventTypeTick,
    EventTypeInput,
} EventType;

typedef struct {
    EventType type;
    InputEvent input;
} GameEvent;

typedef struct {
    GameState state;
    FuriMutex* mutex;
} GameCtx;

static void render(Canvas* canvas, void* ctx) {
    GameCtx* g = ctx;
    furi_mutex_acquire(g->mutex, FuriWaitForever);
    canvas_clear(canvas);
    canvas_draw_box(canvas, g->state.player_x, g->state.player_y, 3, 3);
    char buf[16];
    snprintf(buf, sizeof(buf), "Score %lu", g->state.score);
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 2, 8, buf);
    furi_mutex_release(g->mutex);
}

static void on_input(InputEvent* e, void* ctx) {
    FuriMessageQueue* q = ctx;
    GameEvent ev = {.type = EventTypeInput, .input = *e};
    furi_message_queue_put(q, &ev, FuriWaitForever);
}

static void on_tick(void* ctx) {
    FuriMessageQueue* q = ctx;
    GameEvent ev = {.type = EventTypeTick};
    furi_message_queue_put(q, &ev, 0);  // drop if full
}

int32_t snake_main(void* p) {
    UNUSED(p);
    GameCtx g = {
        .state = {.player_x = 64, .player_y = 32},
        .mutex = furi_mutex_alloc(FuriMutexTypeNormal),
    };
    FuriMessageQueue* queue = furi_message_queue_alloc(8, sizeof(GameEvent));

    ViewPort* vp = view_port_alloc();
    view_port_draw_callback_set(vp, render, &g);
    view_port_input_callback_set(vp, on_input, queue);

    Gui* gui = furi_record_open(RECORD_GUI);
    gui_add_view_port(gui, vp, GuiLayerFullscreen);

    FuriTimer* tick = furi_timer_alloc(on_tick, FuriTimerTypePeriodic, queue);
    furi_timer_start(tick, furi_kernel_get_tick_frequency() / 30);  // ~30 FPS

    GameEvent ev;
    while (!g.state.game_over) {
        if (furi_message_queue_get(queue, &ev, 100) != FuriStatusOk) continue;
        furi_mutex_acquire(g.mutex, FuriWaitForever);
        if (ev.type == EventTypeInput) {
            if (ev.input.type == InputTypePress) {
                if (ev.input.key == InputKeyBack)  g.state.game_over = true;
                if (ev.input.key == InputKeyRight) g.state.player_x++;
                // ...
            }
        } else {  // tick
            // physics, AI, score
        }
        furi_mutex_release(g.mutex);
        view_port_update(vp);
    }

    furi_timer_stop(tick); furi_timer_free(tick);
    gui_remove_view_port(gui, vp); view_port_free(vp);
    furi_record_close(RECORD_GUI);
    furi_mutex_free(g.mutex);
    furi_message_queue_free(queue);
    return 0;
}
```

The mutex protects `g.state` from being read mid-update by the GUI service's draw thread. `furi_mutex_acquire` returns a `FuriStatus`, not a state pointer — pull the state through the context, not the mutex return value.

Tips:

- Game tick around 25–30 Hz, separate from render. Inputs are async and join the same queue with a discriminator field.
- 128×64 mono is generous: 1 px ≈ 1 character of state. Sprites are XBM byte arrays — use the [XBM converter in `compile_assets`](https://github.com/flipperdevices/flipperzero-firmware) or just hand-write 8×8 glyphs.
- Use `FontBigNumbers` for the score, `FontPrimary` for menus, `FontSecondary` for HUD.
- High scores live in `APP_DATA_PATH("highscore.fff")` — write as a Flipper Format File so qFlipper can edit it.
- For audio, queue note events on the same tick handler. A single voice + percussion via clicks is plenty for a chip-aesthetic game.
- For a bigger canvas (640×480) and IMU control, route through the Video Game Module — see [video-game-module.md](video-game-module.md).

Reference open-source games to study: `Snake_Game` (in firmware), `flipper-zero-tetris`, `flipper-zero-asteroids`, `dab_timer`, `air_arkanoid` (VGM IMU game). Most are single-file FAPs <1000 LOC.

## Plugins (`fap_libs` / `PLUGIN`)

For apps that load runtime extensions (e.g. `ESubGhz Chat`, multi-protocol decoders), use the plugin pattern:

1. Host FAP defines an interface struct (function pointers + a magic number).
2. Each plugin is a separate `.fal` built from a sub-folder, with `apptype=FlipperAppType.PLUGIN` and `requires=["host_appid"]`.
3. Host loads them via `flipper_application_alloc` + `flipper_application_load_name_and_type` + `flipper_application_get_api`.
4. Set `fal_embedded=True` to bundle plugins inside the host's `.fap` (extracted to `apps_assets/<host>/` at startup).

## Debugging via the Wi-Fi Developer Board

Full setup (SWD pinout, Black Magic Wi-Fi/USB modes, GDB session, VS Code launch configs, `furi_assert` recovery, log CDC) lives in [wifi-devboard.md](wifi-devboard.md). The 60-second version:

```bash
# Flipper: Settings → System → Debug = ON, then plug the Devboard in
./fbt blackmagic                             # spawn local proxy in firmware checkout
arm-none-eabi-gdb -ex 'target extended-remote tcp:blackmagic.local:2345' \
                  build/f7-firmware-D/firmware.elf
(gdb) monitor swdp_scan
(gdb) attach 1
(gdb) c
```

For an external FAP, attach to the running firmware, then `add-symbol-file dist/my_app.elf 0x<load_addr>` (the load address is printed in the CLI when the FAP starts, with Debug on).

`ufbt vscode_dist` drops a `.vscode/launch.json` with **Attach FW (blackmagic)** (Wi-Fi or USB CDC) and **Attach FW (DAP)** (USB-only). F5 → freeze at current PC → `c` → reproduce → `bt`.

When `furi_assert` fires, the CPU is halted. Attach, `c` once to reach the assert site, `bt`/`info locals`/`up`/`down`. The message lives in `__furi_check_message` and `__furi_crash_message` globals.

The Devboard's second CDC interface streams `furi_log_print_format` output. In Black Magic mode on macOS, use `/dev/cu.usbmodemblackmagic3` at 230400 baud for logs; direct-Flipper `usbmodemflip_*` ports are a separate USB connection.

The same Devboard hardware also runs Marauder / Ghost ESP / Bruce / Evil Portal — see [wifi-devboard.md](wifi-devboard.md) for that surface.

## Tooling tips

- `ufbt update` syncs the SDK to your firmware's API version. If the user is on Momentum / Unleashed / RogueMaster, point `ufbt` at their SDK with `ufbt update --index-url=<fork_index>`.
- `ufbt cli` opens the on-device CLI without a separate terminal — handy for `loader open MyApp` to launch an installed FAP.
- `ufbt fap_deploy` copies all built FAPs from `dist/` to the SD card without launching.
- Always check `Target: 7, API: <n>` in the build output. If API mismatches the SD-card SDK, the FAP refuses to load with `App is not compatible`.
