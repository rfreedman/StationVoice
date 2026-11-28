# Radio backend

Scheduled and manual fires talk to a **radio backend** selected by
`RADIO_BACKEND`:

- **`stub`** (default) — in-memory PTT/COS for dev and tests
  ([`StubRadio`](../app/radio.py)).
- **`dra`** — a **DRA** (Digital Radio Adapter) is the USB box between the
  computer and one radio. This project uses the [Masters Communications
  **DRA-36M**](https://www.masterscommunications.com/products/radio-adapter/dra/dra36m.html).
  It plays the announcement into the radio and keys the transmitter. The
  setting `RADIO_BACKEND=dra` means the app is using those adapters
  ([`DraRadio`](../app/dra_radio.py)). Tested on Ubuntu 26.04.1 LTS. Radios
  have not been tried on macOS.

Hardware wiring, DRA jumpers, udev permissions, and bench checkout are in
[Hardware and radio setup](hardware-setup.md). This document covers the
backend interface, the settings that control it, and app behavior on the
Linux host.

## Protocol

The typed [`Radio`](../app/radio.py) protocol only requires
`channel_busy()` and `set_ptt()`. Optional capabilities are expressed as
`@runtime_checkable` Protocols with matching `as_*` helpers (e.g.
`as_idle_credit(radio)`) — call sites use these helpers instead of
`getattr`. A production DRA backend should implement the full extension set
below; stub implements enough for tests and Mac UI work.

UI "running" status after key-up is wired through
[`transmit(..., on_ptt_keyed=...)`](../app/radio.py) — there is no radio
proxy wrapper.

### Required (Protocol)

| Method | Semantics |
| --- | --- |
| `channel_busy() -> bool` | True when the repeater input is active (COS / carrier detect). Used for defer, clear hold, and last-chance gating. |
| `set_ptt(keyed: bool) -> None` | Key or unkey PTT. `transmit()` always unkeys in `finally`. |

### Optional capability Protocols

Each optional extension is a `@runtime_checkable` Protocol in
[`app/radio.py`](../app/radio.py) with a matching `as_*` helper. Call sites
use the helper (e.g. `as_idle_credit(radio)`) to get the narrowed type or
`None`.

| Protocol | Method / attribute | Typical backend | Used for |
| --- | --- | --- | --- |
| `IdleCreditRadio` | `continuous_idle_seconds() -> float` | DRA | Seconds of continuous COS idle already accrued (background poll). Lets `channel_blocks_transmit()` skip a HID read once the clear hold is met. |
| `ClearWaitRadio` | `wait_for_transmit_clear(*, clear_seconds, poll_seconds, deadline, now, sleep_fn, fail_fast_on_busy=False) -> bool` | DRA | Block until the channel has been idle for `clear_seconds`, or return False past `deadline`. Manual trigger retries and scheduled fires use this when `DRA_CLEAR_SECONDS` > 0. |
| `CosSnapshotRadio` | `cos_defer_snapshot() -> tuple[bool \| None, float]` | DRA, stub | Last COS busy state and idle credit **without** opening HID (UI / SSE manual-trigger status). |
| `UsbTransmitRadio` | `prepare_for_transmit()`, `begin_usb_transmit()`, `end_usb_transmit()`, `play_transmit_audio(chunks, *, lead_seconds)` | DRA | Full USB transmit session. When present, [`transmit()`](../app/radio.py) uses this instead of host `play_fn`. The PTT lead silence is part of the **same continuous USB stream** as the speech. |
| `UsbAbortRadio` | `usb_hid_present`, `transmit_abort_is_set()` | DRA | Detect USB loss mid-transmit; `usb_transmit_lost(radio)` maps RuntimeError → `TransmitAbortError`. |
| `CosPollingRadio` | `warm_open_hid()`, `refresh_cos() -> bool`, `ptt_keyed` (property) | DRA | Background COS poll support. Keep CM119 HID open, read COS, skip sampling while keyed. |
| `AudioReplugRadio` | `sync_audio_output_indices_if_changed(*, after_usb_event: bool = False) -> bool` | DRA | Refresh PortAudio output indices after USB replug. Called from startup and replug recovery. |

PortAudio device enumeration helpers live in
[`app/dra_portaudio.py`](../app/dra_portaudio.py); PCM write/aplay paths
stay in [`app/dra_playback.py`](../app/dra_playback.py). COS sampling and
idle credit live in [`app/dra_cos.py`](../app/dra_cos.py); the in-flight
USB abort registry lives in
[`app/dra_usb_session.py`](../app/dra_usb_session.py). [`DraRadio`](../app/dra_radio.py)
delegates to those and keeps HID, PTT, and `from_config`.

### Errors

| Exception | Meaning |
|---|---|
| [`ChannelBusyError`](../app/radio_errors.py) | COS active immediately before PTT; do not key. Fire may defer or drop. |
| [`TransmitAbortError`](../app/radio_errors.py) | Playback stopped early (e.g. DRA USB unplugged mid-transmit). Fire returns `FireOutcome.DROPPED_USB` for manual triggers. |

## Settings

From the [configuration reference](configuration.md):

| Variable | Default | Meaning |
| --- | --- | --- |
| `RADIO_BACKEND` | `stub` | `stub` = in-memory PTT/COS; `dra` = DRA-36M adapters (requires `hidapi`). If `dra` is set but no DRA is attached, startup falls back to stub with one admin alert. Confirm the active mode in the startup log: `(radio mode: stub)` or `(radio mode: dra)`. On **stub**, triggers still use host PortAudio — see [Stub backend on headless Linux](#stub-backend-on-headless-linux) |
| `PTT_LEAD_SECONDS` | `0.4` | Delay after PTT before audio (on **dra**, silence is streamed on USB; on **stub**, host sleep) |
| `DRA_USB_CHANNEL` | `left` | USB channel for DATA IN (**JU3=L** → `left`) |
| `DRA_COS_LINE` | `vol_dn` | HID COS decode (`vol_dn` or `allstar3`) |
| `DRA_COS_ACTIVE_HIGH` | `false` | Set `true` if idle/busy labels swap on `monitor` |
| `DRA_AUDIO_DEVICES` | *(auto)* | Optional comma list of PortAudio substrings or indices (**one per DRA**). On the Linux host with **two radios**, use fixed USB ports; set this only if auto-detection order is wrong |
| `DRA_CLEAR_SECONDS` | `0` | Continuous COS idle required after synthesize, before PTT (`10` matches bench voice-gate) |
| `DRA_CLEAR_POLL_SECONDS` | `0.25` | COS poll interval during clear wait and background idle tracking |
| `DRA_FINAL_CHECK_SECONDS` | `1.0` | After the clear hold, keep reading COS this long before PTT; any busy read cancels (catches a key-up as the UI countdown ends). Only applies when `DRA_CLEAR_SECONDS` > 0 |
| `DRA_COS_TRACK` | `true` | Background COS polls while the scheduler runs (idle before Trigger now counts toward clear) |
| `DRA_HID_PATH` | *(auto)* | Hex HID path to pin **one** CM119 (a **single** DRA on the Linux host). **Omit when two DRAs are connected** — each radio needs its own CM119 HID |
| `DRA_ALSA_UNMUTE` | `true` | Linux **dra** only: run `amixer` to unmute CM119 **Speaker** at startup. Set `false` to skip |
| `DRA_ALSA_SPEAKER_LEVEL` | `100%` | ALSA **Speaker** level passed to `amixer sset` when unmuting |
| `DRA_PREFER_ALSA_HW` | `1` | Prefer `(hw:…)` ALSA device names over Pulse/PipeWire sink names (PipeWire sink playback can hang PortAudio). Set `0` to use the Pulse sink |
| `DRA_LINUX_PLAYBACK` | `aplay` | Linux playback path: `aplay -D hw:N,0` (then `plughw`) by default; set `portaudio` to force PortAudio |
| `BUSY_RETRY_SECONDS` | `5` | Retry interval while the channel is busy; also the value pre-filled for a **new announcement** in the UI |
| `BUSY_GIVE_UP_SECONDS` | `45` | Drop this fire if still busy after this long; also pre-filled for a new announcement |

## DRA backend behavior on the Linux host

- **Startup pairing:** each radio has its own DRA-36M and therefore its own
  **CM119A** USB audio + HID. With two DRAs, startup should log **2 HID +
  2 PortAudio** pairings. Plug each DRA into a **fixed** motherboard USB
  port; do **not** set `DRA_HID_PATH` (that pins one CM119 only). Use
  `DRA_AUDIO_DEVICES` if PortAudio order is ambiguous. If HID count ≠ audio
  count, run `probe-all` and check udev/`plugdev`
  (see [Hardware and radio setup](hardware-setup.md#identifying-two-identical-adapters)).
- **Confirm the mode:** when startup succeeds, the server logs
  **`Startup complete in …s (radio mode: dra)`** or **`… stub`**
  (stderr or `data/logs/announcements.log`). If no DRA is attached while
  `.env` asks for `dra`, the app **falls back to stub**, sends **one** admin
  alert, and stays up — use **Admin → Environment → Restart application**
  after plugging the adapter in. If you still see **`stub`** with adapters
  attached, check `.env` / HID / udev.
- **Busy and PTT:** defer/drop on busy — `channel_busy()` is true if
  **either** COS is active; re-check after synthesize; final busy check at
  keying; **both** PTT lines together, released in `finally`; mono Piper on
  the **left** USB channel; PTT lead streamed as USB silence.
- **Clear hold:** optional `DRA_CLEAR_SECONDS` (continuous idle before
  PTT). While the scheduler runs, **background COS polling**
  (`DRA_COS_TRACK`, default on) accrues idle time so Trigger now or a slot
  fire can **key immediately** if the channel was already quiet long
  enough. A single short kerchunk resets the clear hold.
- **ALSA unmute:** the app **unmutes Speaker at startup** on each CM119
  ALSA card it uses (`DRA_ALSA_UNMUTE`, `DRA_ALSA_SPEAKER_LEVEL`), because
  the CM119 often comes up muted with no modulation. Unmute uses **all
  playback ALSA controls** on the card (not only `Speaker`). Startup fails
  if `amixer` cannot unmute — fix permissions or install `alsa-utils`.
- **USB replug recovery:** after a USB replug while the app is running, the
  card often mutes again; the app watches `/proc/asound/cards` on the COS
  poll (~0.25 s) and before transmit, re-runs `amixer` when CM119 card
  numbers change, and refreshes PortAudio output indices
  (`AudioReplugRadio`). No app restart is needed.
- **Pulse vs ALSA names:** with PipeWire, the same CM119 may appear as both
  `(hw:…)` and `alsa_output.usb-…` in PortAudio. The app defaults to
  **`(hw:…)`**; after reboot, if startup paired only Pulse sinks, the next
  fire re-resolves to `(hw:…)` when those appear (and can map Pulse→ALSA via
  `/proc/asound/cards` for `aplay`; see GitHub
  [#88](https://github.com/rfreedman/StationVoice/issues/88)).
- **In-flight USB loss:** if a DRA USB cable is unplugged mid-transmit, the
  in-flight transmit aborts (`TransmitAbortError`) rather than leaving PTT
  stuck; the fire returns `FireOutcome.DROPPED_USB` for manual triggers.
- **Other fatal startup errors** (permissions, unmute, bad config) log,
  notify once, and exit; the systemd unit uses **`Restart=no`**, so it stays
  inactive until you `systemctl start` / deploy / Admin restart. There is no
  auto-restart loop.

## Stub backend on headless Linux

`RADIO_BACKEND=stub` replaces only the radio (PTT/COS). A **trigger** or
scheduled fire still plays PCM on the **host** through PortAudio
(`sounddevice`). Browser **Play** is separate: it streams to the web client
and does not use host PortAudio.

On Debian/Ubuntu, PortAudio talks to **PulseAudio** (or PipeWire's
`pipewire-pulse`). `libportaudio2` alone is not enough — the app user needs
a running Pulse/PipeWire session (`XDG_RUNTIME_DIR`, usually
`/run/user/<uid>/pulse/native`). Without that, triggers fail with:

`PulseAudio_Initialize: Can't connect to server` (`PaErrorCode -9999`)

An ALSA loopback device does not fix that by itself; init fails before
device selection.

**Setup (as the same non-root user that runs the app):**

1. Install a Pulse **server**, not only `pulseaudio-utils`. On a minimal
   host: `sudo apt install pulseaudio` (or PipeWire + `pipewire-pulse` +
   WirePlumber). `pactl` alone is not enough.
2. Start it for that user: `systemctl --user start pulseaudio` (or the
   PipeWire units). For a systemd service, use a user session or set
   `XDG_RUNTIME_DIR=/run/user/<uid>` so `/run/user/<uid>/pulse/native`
   exists.
3. Enable on login so reboot keeps it: `systemctl --user enable pulseaudio`.
4. With no real speakers, Pulse often already uses **`auto_null`** as the
   default sink (`pactl info`). If not, add one:

   ```bash
   pactl load-module module-null-sink sink_name=stub_null \
     sink_properties=device.description=Stub_Null_Output
   pactl set-default-sink stub_null
   ```

5. Confirm PortAudio initializes (app venv):

   ```bash
   python -c "import sounddevice as sd; print(sd.query_devices())"
   ```

6. Restart the app if it was started before Pulse was up, then trigger an
   announcement. Audio goes to the null sink (the web UI still will not hear
   triggered audio). A manual `pactl load-module` null sink does not survive
   a Pulse/PipeWire restart unless you persist it; `auto_null` comes back
   when Pulse starts with no hardware.

When you switch to `RADIO_BACKEND=dra`, CM119 USB devices replace this
null-sink path for on-air transmit.

## Implementing a new backend

1. Implement at least the Protocol methods.
2. For on-air use with clear hold and Trigger now UX, implement the
   optional Protocols that **DraRadio** provides (or document deliberate
   gaps).
3. Register via [`create_radio_from_config()`](../app/radio.py) / startup in
   [`app/startup.py`](../app/startup.py).
4. Run the full test suite with `RADIO_BACKEND=stub`; add targeted tests with
   fakes where hardware is required.

## See also

- [Hardware and radio setup](hardware-setup.md) — wiring, jumpers, udev, bench tests
- [Configuration reference](configuration.md) — all settings with defaults
- [Troubleshooting](troubleshooting.md) — transmit and COS symptom runbook
- [Manual operation](manual-operations.md) — Trigger now and busy behavior
