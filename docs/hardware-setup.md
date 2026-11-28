# Hardware and radio setup

A **DRA** (Digital Radio Adapter) is the USB box between the computer and one
radio. This project uses the [Masters Communications
**DRA-36M**](https://www.masterscommunications.com/products/radio-adapter/dra/dra36m.html).
It plays the announcement into the radio and keys the transmitter. The
setting `RADIO_BACKEND=dra` means the app is using those adapters. **Piper**
is the text-to-speech (TTS) library that turns announcement text into the
speech the radio transmits.

This document consolidates the production hardware decision, wiring, radio
settings, Linux host setup, bench checkout procedure, and the bench record.
The backend software that talks to this hardware is covered in
[Radio backend](radio-backend.md).

- Development and testing **without radios** is done on macOS or 64-bit Linux s(radios have
  not been tried on macOS). Development and production **with radios** run
  on a 64-bit Linux computer — tested on **Ubuntu 26.04.1 LTS**.
- **Decision:** two assembled Masters DRA-36M units, each with its own USB
  cable to the host and its own Mini-DIN-6 cable to one radio. Both radios
  hear the same announcement, key together, and report busy independently.
- **Host:** a 64-bit Linux computer with an **internal SSD**. A Raspberry Pi
  4 was considered; a used mini PC was used instead (faster CPU, internal
  SSD, similar cost in 2026).
- **Bench status (October 2026):** single-DRA `retest` passed with **IC-2720**
  and **IC-207H**; dual-DRA `dual-retest` passed with **IC-2720** +
  **FT-8900R**. The announcements app (`RADIO_BACKEND=dra`) has been run
  there with two DRAs and transmitted on both radios.

## Station

| Role | Choice |
|---|---|
| Host | 64-bit Linux (tested on Ubuntu 26.04.1 LTS) |
| Production radios | **IC-207H** |
| Test radio | **IC-2720** (same DATA jack; development only) |
| Radio interface | 2 × DRA-36M, assembled, metal case |
| Audio path | USB only. The computer's analog headphone jack is unused. |
| PTT / busy | Each DRA's CM119A HID (GPIO3 PTT, COS from SQL) |
| Storage | Internal SSD |
| Host power | AC adapter supplied with the computer |
| DRA power | USB from the Linux host; use **direct** motherboard ports, not an unpowered hub |

**Not required:** custom interface board, Y-cable, DRA-Switch, DRA-3M mixer,
extra PTT transistor, or analog audio from the computer's headphone jack.


## How audio actually moves

The DRA-36M **is** the sound card. Piper / PortAudio play into that USB
device. The CM119A DAC creates analog TX audio. The DRA sends it out
Mini-DIN **pin 1**, which is the radio's **DATA IN**.

```
Announcements app  --USB-->  DRA-36M  --Mini-DIN pin 1-->  radio DATA IN
                              CM119A  --Mini-DIN pin 3-->  radio PTT (ground to key)
                                      --Mini-DIN pin 6-->  radio SQL (COS)
                                      --Mini-DIN pin 2-->  ground
```

There is no analog lead from the computer into a "DRA DATA IN." DATA IN is
on the radio. The stock Mini-DIN cable already makes that connection.

This app does not use receive audio from the radio (pins 4 / 5). Busy is
taken from SQL on pin 6. Leave pins 4 and 5 unwired in software. Do not use
the radio's 9600 bps DATA setting; that path bypasses the limiter.

## Mini-DIN-6 pinout (radio DATA jack and DRA)

Stock Masters DIN6 cables are 1:1. Both ends use this pinout.

| Pin | Radio (IC-207H / IC-2720) | DRA-36M |
|---|---|---|
| 1 | Data In (1200 bps path) | TX audio (JU3 left or right) |
| 2 | Ground | Ground |
| 3 | PTT (pull to ground to key) | PTT (transistor or relay) |
| 4 | Data Out | 9600 RX audio (unused here) |
| 5 | AF Out ~270 mV p-p | 1200 RX audio (unused here) |
| 6 | SQL — **high when squelch is open** (labeled **SQ** on the 207H, **P SQL** on the 2720) | COS (AllStar HID input when **JU1** is installed) |

## Jumper settings (same on both DRA-36M)

Masters ships the DRA-36M for digital-mode (VARA / Direwolf): **JU1 off**,
JU3 = R, **JU5 = B (9600)**. **This app is not that.** On a new unit,
change three jumpers from factory default:

| Jumper | What it controls | Factory | For this app |
|---|---|---|---|
| **JU1** | **COS (channel busy):** when installed, connects the radio's **Mini-DIN pin 6** (SQL — high when squelch is open) to the CM119A logic input that the host reads as COS over USB HID. With JU1 off, pin 6 is ignored and **`channel_busy()` / `monitor --cos vol_dn` cannot work.** | **Off** (open) | **Install** the shunt (closed) |
| **JU3** | **TX audio path:** **L** = Mini-DIN pin 1 fed from USB **left** channel; **R** = pin 1 from USB **right** channel. Software must play program audio on the same channel. | **R** (right) | **L** (left) on **both** DRA |
| **JU5** | **Receive audio source** on the DATA jack: **A** = pin **5** (1200 baud AF out), **B** = pin **4** (9600 baud data out). The DRA routes the selected pin into the CM119 receive path (unused for playback in this app, but must match how the radio is configured). Wrong JU5 has caused missing or inverted COS on the bench. | **B** (9600) | **A** (1200) |

Set the radio to **1200 bps DATA**, same as **JU5 = A**. The 36M has **no
JU2** (CTCSS input was omitted); all other jumper numbers match the DRA-36.

| Jumper | Setting for this app | Why |
|---|---|---|
| **JU1** | **Installed** | Enables COS from Mini-DIN pin 6 (radio SQL) as the CM119A HID bit |
| JU2 | Not present on 36M | — |
| **JU3** | **L** on both units | Pin 1 = USB **left** channel. Keep both DRA identical so software can play the same stream on **left** |
| JU4 | Leave off unless the PTT LED glows with the radio off | Anti-false PTT LED; Icom base radios usually leave this off |
| **JU5** | **A (1200)** | Masters factory default is **B (9600)**. Match the radio's **1200 bps DATA** setting even though this app does not record RX audio — wrong JU5 has caused bogus or inverted COS on the bench |
| **PTT pair** | Start on **T** (transistor). Both shunts required, parallel to the silkscreen arrows | Icom packet PTT is ground-to-key. If a radio will not key, rotate both shunts 90° to **R** (reed relay). The 36M relay option exists for Icom radios that dislike open-collector keying |

**TX level:** With **JU3 = L**, adjust **R16** (left-channel pot) on each DRA
until DATA-IN deviation is clean for Piper speech. **R14** is for the right
channel only (unused with this jumper choice). R12 is receive level and is
irrelevant until something reads RX audio.

**Software:** Bench TX commands use **`-c left`** (or omit `-c` —
[`dra36m_check.py`](../scripts/dra36m_check.py) defaults to left). The app
routes mono Piper onto the **left** channel of **both** USB devices and
feeds the two streams in alternating 50 ms blocks so both radios play at the
same time ([`app/dra_playback.py`](../app/dra_playback.py)). The bench
script imports its HID/audio helpers from `app/cm119.py` and
`app/dra_playback.py`, so run it from the repo with the project virtualenv.

Official jumper text: [dra36-jumpers.txt](https://masterscommunications.com/products/radio-adapter/dra/txt/dra36-jumpers.txt).
Pinout: [dra36-DIN-pinout.txt](https://masterscommunications.com/products/radio-adapter/dra/txt/dra36-DIN-pinout.txt).
36 vs 36M: [dra36-vs-dra36m](https://www.masterscommunications.com/products/radio-adapter/dra/dra36-vs-dra36m.html).

## Radio settings (both IC-207H and IC-2720)

1. DATA speed **1200 bps**, not 9600. 9600 bypasses the limiter and is the
   wrong audio injection point.
2. At 1200 bps, **unplug the microphone** while the app is transmitting.
   Otherwise mic audio is mixed onto the announcement. (9600 mutes the mic
   automatically; do not switch to 9600 to get that mute.)
3. Keep the radio's speaker volume at a **normal** level. Pin 6 SQL may not
   assert if the volume is at zero.
4. SQL must actually open for pin 6 to go high. If a tone squelch is on,
   also leave carrier squelch at a usable setting so SQL follows the channel.
5. Confirm PTT: Mini-DIN pin 3 to ground keys the transmitter.

Ignore IC-2720 packet-band lock for this project. Production is the IC-207H.

## PTT and busy (what the app must do)

Announcements go out on **both** radios at once. Never talk on one machine
while the other has a QSO.

| Function | Hardware | Software |
|---|---|---|
| Busy | Each DRA COS (HID), from that radio's pin 6 SQL | `channel_busy()` is true if **either** COS is active. Defer with existing `BUSY_RETRY_SECONDS` / `BUSY_GIVE_UP_SECONDS` until **both** are clear |
| PTT | Each DRA CM119A **GPIO3** | `set_ptt(True)` asserts **both** HID PTT bits. Keep `PTT_LEAD_SECONDS` (default 0.4 s) before audio. Release both in `finally` |
| Audio | Two PortAudio (CM119A) devices | Play the **same** PCM on **both** devices, or a PulseAudio / PipeWire combine sink that feeds both. Piper is mono; place it on the **left** channel (silence on right) on **each** DRA to match **JU3 = L** |

SQL polarity: radio pin 6 is **high when the squelch is open**. CM119A COS
for AllStar is normally **active-low**. Invert in software after measuring,
or use any NPN inverter Masters documents for that COS input. Confirm with a
DMM on pin 6 (squelched vs open) and on the HID bit before relying on busy
detect.

**Application:** Set `RADIO_BACKEND=dra` on the **one Linux computer** that
runs this app with radios (keep `stub` on macOS, where radios have not been
tried). Confirm the active mode in the startup log — see
[Radio backend](radio-backend.md) for backend settings, dual-device
pairing, and app behavior on the Linux host.

## Identifying two identical adapters

Both DRA-36M units enumerate as the same C-Media CM119A (USB sound + HID).
Enumeration order is not stable across reboots.

1. Plug Radio 1's DRA into a chosen USB port on the Linux host and leave it
   there.
2. Same for Radio 2 on a different port.
3. udev rules keyed on **USB path** (`KERNELS=="1-1.x"`) or the device
   serial, not "first CM119A vs second."
4. Grant the service user access to both CM119 **USB** and **`hidraw`**
   nodes (see [Linux udev and plugdev](#linux-udev-and-plugdev)) and both
   ALSA / PortAudio devices. Put the app user in group **`plugdev`**.

`lsusb` and `arecord -l` / `aplay -l` should show two C-Media devices.
`ls /dev/hidraw*` should show two HID interfaces after the DRA are plugged in.

## Linux host setup

- **64-bit Linux**, tested on Ubuntu 26.04.1 LTS. The Piper stack requires
  64-bit; do not use 32-bit OS builds.
- `sudo apt install libportaudio2` (or equivalent) for PortAudio playback.
- Keep `data/` (announcements JSON, PCM cache, logs) on the **internal SSD**.
- Two DRA-36M units are USB-powered; plug both into **direct** motherboard
  USB ports with adequate current.
- Run the app and bench scripts as the configured non-root user — **not**
  `sudo` (root has no PulseAudio session; PortAudio can fail with
  `PaErrorCode -9999`).

### Linux: udev and plugdev

The DRA-36M CM119A needs **HID** (`open_path`) and **USB audio**
(PortAudio). On Linux, `hidapi` needs both:

- read/write on the matching **`/dev/hidraw*`** node, and
- read/write on the matching **`/dev/bus/usb/…/…`** node (not only `hidraw`).

Without udev, `probe` can show **OK** for PortAudio then fail with
**`OSError: open failed`** on HID even when your user can open
`/dev/hidraw*` manually.

**1. Install udev rules** (CM119A on the DRA: vendor `0d8c`, product `013a`):

```bash
sudo tee /etc/udev/rules.d/99-dra-cm119-hidraw.rules <<'EOF'
SUBSYSTEM=="hidraw", KERNEL=="hidraw*", ATTRS{idVendor}=="0d8c", ATTRS{idProduct}=="013a", MODE="0660", GROUP="plugdev"
EOF

sudo tee /etc/udev/rules.d/99-dra-cm119-usb.rules <<'EOF'
SUBSYSTEM=="usb", ATTR{idVendor}=="0d8c", ATTR{idProduct}=="013a", MODE="0660", GROUP="plugdev"
EOF

sudo udevadm control --reload-rules && sudo udevadm trigger
```

Unplug and replug each DRA (or reboot) so permissions apply. Two identical
DRAs share the same rules; udev sets **`plugdev`** on **each** matching
hidraw and USB device.

**2. Add the bench / app user to `plugdev`:**

```bash
sudo usermod -aG plugdev "$USER"
```

Log out and back in (or start a new login session) so **`plugdev`** is in
**`id -nG`**. The account that runs `python -m app serve` (systemd or
interactive) needs this group.

**3. Quick check** (DRA plugged in, normal user — **not** `sudo`):

```bash
id -nG | tr ' ' '\n' | grep -x plugdev
ls -l /dev/hidraw* /dev/bus/usb/*/*
```

Matching CM119 nodes should look like **`crw-rw---- root plugdev`**.

### ALSA mixer: USB Speaker can come up muted

After plug-in or reboot, the CM119 USB card often comes up with **Speaker
muted and 0%**. Symptom: **PTT keys** (HID OK) but **no modulation** on the
air (smoke tone and Piper both silent).

Check (adjust card number if `aplay -l` differs):

```bash
amixer -c 1 scontents
amixer -c 1 sset Speaker 100% unmute
```

Re-run `python scripts/dra36m_check.py smoke -c left --seconds 2 --lead 0.6`
to confirm tone on DATA IN. Adjust **R16** on the DRA (JU3=L) for deviation,
not only software volume. With `RADIO_BACKEND=dra`, the app **unmutes
Speaker at startup** on each CM119 ALSA card it uses and re-runs `amixer`
after USB replug — see [Radio backend](radio-backend.md).

### Piper sample rate vs CM119

Piper outputs **22050 Hz**; the DRA USB interface accepts **44100 / 48000
Hz**. The app and bench scripts **resample to the device's PortAudio
default** (usually 44100). Log line example: `22050 Hz → 44100 Hz USB`.

## DRA-36M status LEDs

Three front-panel indicators ([DRA detailed description](https://www.masterscommunications.com/products/radio-adapter/dra/dra-description.html)).
**Busy / COS does not drive the blue LED.**

| LED | Color | Meaning |
|---|---|---|
| Heartbeat | Green | Solid = USB power. **Flashes** when a host app is **streaming USB audio** to the DRA. |
| COMM OK | Blue | **Solid** only while heartbeat is healthy (green flashing). Host watchdog — not squelch. **Off** with USB plugged in but no audio stream (e.g. HID-only `monitor`) is normal. |
| PTT | Red | On while GPIO3 keys the transmitter. |

Blue COMM OK also gates PTT in hardware: if blue is out, the red PTT LED and
radio keying from the DRA are disabled until audio streaming restores
heartbeat. Validate busy with **HID COS** (`vol_dn`), pin 6, or Linux
`monitor` — not by watching blue during RX.

**Bare `ptt` subcommand does not key RF** without USB streaming; use
`smoke` or `voice` for real PTT tests.

## Bench checkout

Use these **before** wiring the announcements app to CM119A HID/PortAudio.
Run them on the **Linux host**, from the repo root with the venv active.
Radios have not been tried on macOS. Record results in the
[bench record](#bench-record) below.

**Prerequisites**

| Item | Requirement |
|------|-------------|
| Python venv | `uv sync` (installs `hidapi`, `sounddevice`, `numpy`) |
| Linux | `sudo apt install libportaudio2`; [udev + `plugdev`](#linux-udev-and-plugdev) |
| DRA jumpers | **JU1 on**, **JU5 = A (1200)**, **JU3 = L** on both production DRA (must match `-c`; default **`left`**) |
| Radio | **1200 bps DATA**, speaker volume up, **mic unplugged** for on-air TX tests |
| RF safety | Low power, dummy load, or quiet simplex |

### Recommended order (single radio)

Work one radio at a time. (Full radio checkout: jumpers as in the table,
Mini-DIN cable to the radio DATA jack, radio on 1200 bps DATA, mic
unplugged, volume up; in `alsamixer` for that USB card, unmute the playback
path and raise the PCM slider; confirm the computer's analog headphone
output is silent during tests — if you hear the announcement there,
playback is aimed at the wrong PortAudio device.)

| Step | Command | Pass criteria |
|------|---------|----------------|
| 1 USB | `probe` | Audio + HID OK; idle **`vol_dn busy: False`** when squelched |
| 2 COS live | `monitor --interval 0.5 --changes-only --cos vol_dn` | **busy** while other station TX; **idle** when quiet |
| 3 RF PTT + tone | `smoke --seconds 2 --lead 0.6` (or `-c left`) | TX after ~lead silence; tone clean (adjust **R16** with JU3=L) |
| 4 Piper on air | `voice -c left --lead 0.6 "…"` | Normal speed/intelligibility; first word not clipped |
| 5 Busy gate | `voice-gate -c left --poll 0.25 --clear-seconds 10 --lead 0.6` | No TX while other key held; one TX after full clear window |
| 6 Regression | `retest -c left --with-voice --lead 0.6` | Exit 0; voice sounds normal |

Optional: **`snap --period 0.25`** during step 2 for a burst log of
`vol_dn` / `ir0..3`.

Busy/COS polarity: squelch closed → pin 6 low and COS HID **idle**; open
squelch → pin 6 high and COS HID **busy**. Measure on Linux:

```bash
python scripts/dra36m_check.py monitor --interval 1 --raw --cos vol_dn
```

Prefer `vol_dn`; `allstar3` is an equivalent cross-check. Use `--active-high`
only if idle/busy labels swap. Do not use USB audio capture for squelch on
the 36M.

### Dual DRA (two adapters on one host)

**Verified on the Linux host (Ubuntu 26.04.1 LTS, 2026-10-24):** two
**DRA-36M** units with **IC-2720** and **FT-8900R** — `probe-all`,
`dual-smoke`, `dual-voice`, and `dual-retest -c left --with-voice --lead 0.6`
all passed (both rigs keyed; Piper heard on both).

Use these when **two** DRA-36M units are on fixed USB ports on the Linux
host. Single-radio commands (`probe`, `smoke`, `retest`) still target the
**first** CM119 only; dual commands pair every HID with PortAudio the same
way as the app. Per-radio jumper/COS checkout (first time on a new unit):
unplug the other DRA and run the [single-radio order](#recommended-order-single-radio).

| Step | Command | Pass criteria |
|------|---------|----------------|
| 1 Pairing | `probe-all` | Lists **each** HID path + idle COS; **two** PortAudio DRA devices; pairing table `dra-1` / `dra-2` with no HID ≠ audio count error |
| 2 Dual tone | `dual-smoke -c left --seconds 2 --lead 0.6` | **Both** radios key after lead; tone on both; adjust **R16** per DRA |
| 3 Dual Piper | `dual-voice -c left --lead 0.6 "…"` | Same speech on both rigs; not clipped at start |
| 4 Regression | `dual-retest -c left --with-voice --lead 0.6` | Exit 0; manual confirm both keyed and heard voice |

| Flag | Used on | Purpose |
|------|---------|---------|
| **`--require N`** | `probe-all` | Minimum paired count (default **2**) |
| **`--active-high`** | `probe-all`, `dual-retest` | Flip vol_dn polarity in idle COS samples |

**Env:** Leave **`DRA_HID_PATH` unset** with two DRAs. If PortAudio order is
wrong, use fixed USB ports and optional **`DRA_AUDIO_DEVICES`**. If HID count
≠ audio count, run `probe-all`, confirm udev/`plugdev`, and see
[Identifying two identical adapters](#identifying-two-identical-adapters).

### Bench subcommands

| Command | What it does | Key flags |
|---|---|---|
| `probe` | Lists PortAudio DRA device and reads one idle HID sample. Pass: `OK` for audio and HID; squelched `vol_dn busy: False` | — |
| `monitor` | Polls COS on an interval (production-style `vol_dn` default) | `--interval SEC` (default 1), `--cos vol_dn`, `--raw`, `--changes-only`, `--active-high`, `--wait-device SEC` (startup HID enumerate retry, default 20; the script retries up to 20 s if the channel is already busy at startup) |
| `snap` | Rapid COS samples (good while someone else keys) | `--period SEC` (default 0.25), `--count N` (default 30), `--active-high` |
| `ptt` | HID GPIO3 only — **no USB audio**. On DRA-36M this often keys **no RF** (COMM OK watchdog). Do not treat as RF pass/fail | `--seconds 2` |
| `tone` | Test tone to DRA USB **without** PTT (level/deviation check) | `-c left\|right\|mono` (must match **JU3**), `--level` (default 0.25) |
| `smoke` | PTT + **lead silence on USB** + tone + unkey (COMM OK + radio settle) | `--lead SEC` (default 0.4), `--seconds`, `--frequency` (default 800), `--level` (default 0.3) |
| `voice` | PTT + lead silence + **Piper** on air (22050 Hz stream rate, not 48 kHz device default) | `--lead SEC` (0.6 typical on bench), `-v VOICE`, text as arguments |
| `voice-gate` | Simulates **defer while busy** + **clear window** before one announcement (app `channel_busy()` behavior) | `--poll` (0.25), `--clear-seconds` (10), `--wait-busy` (120), `--wait-idle` (300), `--min-busy` (0.5), `--lead` (0.6), `--cos`, `--active-high`, `--wait-device` |
| `retest` | Automated bundle: `probe` → COS idle sample → `ptt` 0.5 s → `smoke` → optional `voice` | `--with-voice`, `--voice-text`, `--smoke-seconds` (2), `--lead` |
| `hid-once` | Hidden helper: one HID read as JSON. Not part of normal manual checkout | — |

**`voice-gate` procedure**

1. Start script (monitored rig squelched).
2. Key **another** radio and **hold** → logs **`COS busy — not transmitting`**,
   no RF from script.
3. **Unkey** → logs **`need 10s continuous clear before TX`** (or your
   `--clear-seconds`).
4. If someone keys again during clear → **`reset clear wait`**.
5. After **full clear window** → **one** Piper TX and exit.

**Pass:** No TX during hold; no TX during clear window if channel busy again;
exactly one TX after stable clear.

### Verification status (October 2026)

| Mode | Host | Radios | Regression command | Result |
|------|------|--------|-------------------|--------|
| Single DRA | **Linux** (Ubuntu 26.04.1 LTS) | **IC-2720** (dev / test rig) | `retest -c left --with-voice --lead 0.6` | **Pass** (2026-10-24) |
| Single DRA | **Linux** (Ubuntu 26.04.1 LTS) | **IC-207H** (production) | same `retest` | **Pass** (2026-10-24) |
| Dual DRA | **Linux** (Ubuntu 26.04.1 LTS) | **IC-2720** + **FT-8900R** | `dual-retest -c left --with-voice --lead 0.6` | **Pass** (2026-10-24) |

On-air production will use **two IC-207H**; dual `dual-retest` with both
production rigs on the Linux host is not recorded yet.

## Bench record

Recorded on the Linux host used for radio development (**Ubuntu 26.04.1
LTS**). **Production (both radios): JU3 = L, USB left channel, R16.**
Linux host (2026-10-24): single-DRA `retest` **pass** with **IC-2720**
(dev/test rig) and with production **IC-207H**; dual-DRA `dual-retest`
**pass** with **IC-2720** + **FT-8900R** (2× DRA-36M).

### DRA-36M (unit under test)

| Item | Linux host value | Notes |
|------|------------------|--------|
| **JU1** | Installed | Factory = off |
| **JU5** | **A (1200)** | Factory = B (9600) |
| **JU3** | **L (left)** | Pin 1 ← USB left channel |
| **PTT pair** | **T** (transistor) | Switch to **R** if a radio will not key |
| **JU4** | Off (default) | — |
| **TX level pot** | **R16** (left / JU3=L) | Backed off from factory until Piper voice was clear (no fuzzy over-deviation). *Record your panel mark:* _________________ |
| **USB** | Direct motherboard ports (no unpowered hub) | |
| **Blue COMM OK** | Off during HID-only tests | Normal; streams during `smoke` / `voice` |

### Software / COS and transmit

| Item | Value |
|------|--------|
| **COS mode** | `monitor --cos vol_dn` |
| **Polarity** | Default active-low — **no** `--active-high` |
| **Idle HID (squelched)** | `ir0..3=02000000`, `vol_dn busy: False` |
| **Cross-check** | `allstar3` matched `vol_dn` in testing |
| **USB channel flag** | `-c left` (matches **JU3 = L**) |
| **PTT lead** | `--lead 0.6` (silence on air before speech; tune 0.5–0.8 if needed) |
| **Piper voice** | `en_US-ryan-medium` @ **22050 Hz** (stream at Piper rate, not 48 kHz device default) |
| **Regression** | `python scripts/dra36m_check.py retest -c left --with-voice --lead 0.6` |
| **Busy gate** | `voice-gate -c left --poll 0.25 --clear-seconds 10 --lead 0.6` |

### Radios

| Radio | Role | Notes |
|---|---|---|
| **IC-2720** | Dev/test rig (single-radio `retest` and one leg of dual) | 146.520 MHz simplex (2 m calling); **1200 bps DATA**; volume up; mic unplugged for on-air `voice` tests |
| **IC-207H** | Production repeater radio | **1200 bps DATA**; same Mini-DIN DATA jack as IC-2720; single-radio `retest` passed 2026-10-24 |
| **FT-8900R** | Second radio for dual-DRA checkout | `dual-retest -c left --with-voice --lead 0.6` **pass** 2026-10-24 |

### Linux host + two IC-207H (fill in at production install)

| Item | Radio 1 | Radio 2 |
|------|---------|---------|
| Linux host USB port (fixed) | | |
| udev rules + user in `plugdev` | | |
| ALSA / PortAudio name | | |
| hidraw + `DRA_HID_PATH` if pinned (leave unset with two DRAs) | | |
| DRA label (Radio 1 / 2) | | |
| JU1 / JU5 / JU3 / PTT | JU1 on, JU5 A, **JU3 L**, T | Same |
| TX pot (**R16**, JU3=L) | | |
| IC-207H frequency / DATA | | |
| COS idle / busy bytes (`vol_dn`) | | |
| `--active-high` needed? | no / yes | |

### Sign-off

| Milestone | Date | Initials |
|-----------|------|----------|
| Linux host + IC-2720: single-radio `retest --with-voice --lead 0.6` | 2026-10-24 | |
| Linux host + IC-207H: single-radio `retest --with-voice --lead 0.6` | 2026-10-24 | |
| Linux host + IC-2720 + FT-8900R: dual `dual-retest --with-voice --lead 0.6` | 2026-10-24 | |
| Linux host + 2× IC-207H: dual `dual-retest --with-voice` | | |

## Host troubleshooting: desktop audio stealing the DRA

The announcements app plays to the DRAs with **`aplay -D plughw:N,0`**, not
the desktop default sink. KDE / PipeWire can still stream **UI sounds** to a
C-Media USB sink and light the DRA front panel even when
**`python -m app serve` is idle** and not keying PTT. Normal LEDs when idle:
green solid / blue off / red off. If a DRA shows **green blinking + blue
solid** while the app is idle, desktop audio is streaming to it.

**Fix that worked on the Ubuntu host (2026-10)** — persistent KDE settings
(survived reboot; both DRAs green solid / blue off after restart):

```bash
kwriteconfig6 --file kdeglobals --group Sounds --key Enable false
kwriteconfig6 --file kcm_soundrc --group General --key EnableSoundFeedback false
killall kded6   # once, after writing config; Plasma respawns kded
```

Optionally in **System Settings → Sound**: default playback **not** "USB PnP
Sound Device"; turn off event / feedback sounds if the GUI exposes them.
(`kdeglobals [Sounds] Enable=false` alone did **not** stop the loop;
`kcm_soundrc` volume feedback did.)

**Runbook if it happens again** (on the Linux host console):

1. **Confirm the app is not transmitting** — no stuck `aplay` / serve log
   in a TX phase; red PTT LED off on the DRA.
2. **See who holds ALSA playback:** `fuser -v /dev/snd/pcmC0D0p /dev/snd/pcmC1D0p 2>&1`
   — if **`pipewire`**, treat as desktop audio, not scheduler TX.
3. **Find the stream:** `wpctl status` → **Audio → Streams**. If
   **libcanberra** / **kded6** links to **USB PnP Sound Device** playback
   ports, inspect it: `wpctl inspect <stream-id>` and look for
   **`audio-volume-change`** / **`target.object`**.
4. **Pulse view:** `pactl list sinks short` — a **RUNNING**
   `alsa_output.usb-C-Media_…` sink while idle is a smoking gun.
   `pactl get-default-sink` should not be a C-Media device for desktop use.
5. **Apply the fix** above (step `EnableSoundFeedback false` + `Sounds
   Enable=false`, then `killall kded6`), re-check `wpctl status` and DRA LEDs.
6. **If LEDs stay wrong but `fuser` is empty** — unplug/replug that DRA's
   USB cable to reset the adapter watchdog (hardware latch).
7. **After PipeWire restart / reboot** — confirm the settings from step 5
   are still present; re-apply if needed.

Less reliable on PipeWire-pulse: `pactl move-sink-input`, `pactl
kill-sink-input` (often missing), `wpctl kill` (not in WirePlumber 0.5.x).
Suspending the Pulse sink can idle the sink but may not drop a stuck
libcanberra loop — disable volume feedback instead.

## Operator reminders

- Unplug mics at 1200 bps whenever the scheduler might TX.
- If pin 6 never shows busy, check **JU5 = A (1200)** and turn the radio
  volume up before chasing software.
- Same announcement on both machines; busy if either is busy; PTT both or
  neither.
- Symptom-first fixes for the radio path are collected in
  [Troubleshooting](troubleshooting.md).


## References

- DRA-36M product: https://www.masterscommunications.com/products/radio-adapter/dra/dra36m.html
- Support docs: https://masterscommunications.com/products/radio-adapter/dra/dra36m_docs.html
- Jumpers: https://masterscommunications.com/products/radio-adapter/dra/txt/dra36-jumpers.txt
- Mini-DIN pinout: https://masterscommunications.com/products/radio-adapter/dra/txt/dra36-DIN-pinout.txt
- 36 vs 36M: https://www.masterscommunications.com/products/radio-adapter/dra/dra36-vs-dra36m.html
- Bench script: [`scripts/dra36m_check.py`](../scripts/dra36m_check.py) ([`scripts/README.md`](../scripts/README.md))
- Scheduling: [How to schedule](how-to-schedule.md)
- Backend software: [Radio backend](radio-backend.md)
