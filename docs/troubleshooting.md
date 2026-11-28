# Troubleshooting

Symptom-first runbook. Each entry names the usual cause and the fix; the
linked subject doc has the full procedure.

## Startup

| Symptom | Likely cause | Fix |
|---|---|---|
| Startup log says `(radio mode: stub)` although `.env` sets `dra` | No DRA was found; the app **falls back to stub** with one admin alert and stays up | Plug the adapter in, then **Admin → Environment → Restart application**. If it still says `stub` with adapters attached, check `.env`, udev/HID (see below) |
| App exits at startup (permissions, unmute, bad config) | Fatal startup errors log, notify once, and exit; the systemd unit is `Restart=no` | Read `data/logs/announcements.log` or the unit journal; fix the cause; start the unit again. There is no auto-restart loop |
| Startup fails immediately on a fresh install | `STATION_CALL` / `STATION_NAME` missing or blank | Set them in `.env` (see [`.env.example`](../.env.example)) |
| Startup fails with a plugin error (admin email) | Notifier plugin in `plugins/` but its packages or send credentials are missing | Install the plugin's packages into the venv; put its secrets in `.env.secrets` — see [Configuration — admin email](configuration.md#admin-email-optional-plugin) |
| Not sure the deploy/restart worked | Startup success is the `Startup complete` line | Check the unit journal (not `data/logs/serve.out`) and confirm `(radio mode: …)` — see [Operations](operations.md) |

## Transmit (DRA backend)

| Symptom | Likely cause | Fix |
|---|---|---|
| PTT keys (red LED, RF carrier) but **no modulation** | CM119 USB card came up with **Speaker muted / 0%** | `amixer -c N sset Speaker 100% unmute`; the app unmutes at startup and after replug. Adjust **R16** for deviation — see [Hardware setup](hardware-setup.md#alsa-mixer-usb-speaker-can-come-up-muted) |
| Bench `ptt` subcommand keys **no RF** | COMM OK watchdog: no USB audio stream, so the DRA blocks keying | Use `smoke` or `voice` for real PTT tests |
| First word of the announcement clipped | PTT lead too short | Raise `PTT_LEAD_SECONDS` (bench: `--lead 0.6`) |
| Speech sounds fuzzy / over-deviated | TX level too hot | Back off **R16** on the DRA (JU3=L) |
| Announcement audio heard from the computer's speakers | Playback aimed at the wrong PortAudio device (motherboard analog out) | Re-check `DRA_AUDIO_DEVICES` / device pairing; the analog headphone jack is unused in this design |
| Your voice mixed onto announcements at 1200 bps | Microphone still plugged in | Unplug mics whenever the scheduler might TX |
| A fire was dropped with `DROPPED_USB` | DRA USB unplugged mid-transmit | In-flight transmits abort and PTT is released; replug the DRA (the app recovers without restart), re-run `probe`/`retest` if unsure |

## Busy / COS

| Symptom | Likely cause | Fix |
|---|---|---|
| Pin 6 never shows busy | **JU5 not = A (1200)**, radio volume at/near zero, or JU1 not installed | Check JU5 = A, turn the radio volume up, leave carrier squelch usable, confirm JU1 is installed — see [Hardware setup](hardware-setup.md#jumper-settings-same-on-both-dra-36m) |
| `probe` shows PortAudio OK then `OSError: open failed` on HID | udev rules missing — `hidapi` needs **both** the `hidraw` node and the `/dev/bus/usb` node | Install the udev rules, add the user to `plugdev`, replug — see [Hardware setup](hardware-setup.md#linux-udev-and-plugdev) |
| Idle/busy labels swapped | COS polarity inverted for this rig | Set `DRA_COS_ACTIVE_HIGH=true` (bench: `--active-high`) after measuring with `monitor --cos vol_dn` |
| With two DRAs, only one radio's PTT/COS works | `DRA_HID_PATH` is set — it pins **one** CM119 and hides the second | Unset `DRA_HID_PATH`; use fixed USB ports; optionally `DRA_AUDIO_DEVICES` — see [Radio backend](radio-backend.md#dra-backend-behavior-on-the-linux-host) |
| DRA shows green blinking + blue solid while the app is idle | Desktop audio (KDE / PipeWire) streaming UI sounds to the DRA | Disable volume feedback sounds; full runbook in [Hardware setup](hardware-setup.md#host-troubleshooting-desktop-audio-stealing-the-dra) |

## Host / stub backend

| Symptom | Likely cause | Fix |
|---|---|---|
| Trigger fails with `PulseAudio_Initialize: Can't connect to server` (`PaErrorCode -9999`) | Headless Linux: app user has no Pulse/PipeWire session | Install a Pulse **server**, start/enable it for the app user, add a null sink — see [Radio backend](radio-backend.md#stub-backend-on-headless-linux) |
| Same error when running the app or bench scripts under `sudo` | Root has no PulseAudio session | Run as the configured non-root user (in `plugdev`) |
| Log line `22050 Hz → 44100 Hz USB` | Normal: Piper output resampled to the device default | Nothing — informational |

## Scheduler and announcements

| Symptom | Likely cause | Fix |
|---|---|---|
| A slot did not air after a restart or app downtime | Past-due slots are **not** played late (no double-transmission risk) | Use **Trigger now** or wait for the next slot — see [Manual operation](manual-operations.md#after-an-outage-or-restart) |
| At a slot, the baseline played instead of the scheduled announcement | The announcement is marked **too long** (over repeater timeout − 2 s) | Shorten it and save again; the UI names the substitution — see [Creating announcements](announcements.md#spoken-length-the-repeater-timeout-minus-2-seconds) |
| The home grid for earlier today shows a different announcement than what aired | The grid is a **simulation** from the current rotation, not a log | Check `data/logs/announcements.log` for what really aired |
| Announcement never plays and nothing replaces it | All candidate baselines too long, or a **Silence** overlay owns the slot | Check the slot clock's warnings and overlay list — see [How to schedule](how-to-schedule.md) |
| An announcement was dropped while the channel was busy | Busy give-up expired (per-announcement value) | Normal behavior; use **Trigger now** to try again — see [Manual operation](manual-operations.md) |

## Newsline

| Symptom | Likely cause | Fix |
|---|---|---|
| Log warning about `ffmpeg` / `ffprobe`; no download or split | They are not on `PATH` | Install them; download, split, and Newsline playback cannot run until they exist |
| Latest report failed to split; hourly checks won't retry it | A failed split is not retried automatically | **Check for Newsline now** clears that report and re-downloads — see [Newsline](arnewsline.md#download-window) |
| Newsline slot played the baseline instead | Report failed/missing, story files gone, outside the bulletin validity window, or a spoken part is too long | The home screen names what plays instead and why — see [Newsline](arnewsline.md#schedule-and-airtime) |
| Host runs hot (high CPU %/temperature) during a split | Parallel Whisper/ffmpeg workers saturating a small NUC | Set `ARNEWSLINE_QA_WORKERS=1`, `ARNEWSLINE_EXPORT_WORKERS=1`, `ARNEWSLINE_CPU_THREADS=2` — see [Newsline](arnewsline.md#cooler--slower-splits-linux-host) |

## Deploy and remote access

| Symptom | Likely cause | Fix |
|---|---|---|
| `sudo -n systemctl stop` asks for a password | Sudoers NOPASSWD line missing or path/argv mismatch (bare unit name, exact binary path) | Fix `/etc/sudoers.d/dvra-announcements` with `visudo`; re-test after `sudo -k` — see [Operations](operations.md#systemd-start--stop) |
| Deploy stops with a version complaint | `origin/main` has new commits but no version bump | `uv version --bump patch`, commit, push, deploy — see [Operations](operations.md#deploy-behavior) |
| Deploy reports **Linux host working tree has local changes** | An older `./serve.sh` rewrote `uv.lock` on the host | `git restore uv.lock` on the host, then redeploy — see [Operations](operations.md#deploy-behavior) |
| Deploy aborts without updating | App did not stop within `DEPLOY_STOP_TIMEOUT` (default 30 s) | Check for a stuck process/transmission. Deploy never SIGKILLs (that can leave PTT keyed) |
| After reboot, `https://announcements.w2zq.com` fails but `http://…:8000` works | Caddy boot race: Wi-Fi IP not up when Caddy starts | The `Restart=on-failure` drop-in retries; manual: `sudo systemctl restart caddy` — see [Operations](operations.md#boot-race-wi-fi-ip) |

## Web UI / accounts

| Symptom | Likely cause | Fix |
|---|---|---|
| Sign-in returns `429` | Login rate limit: `LOGIN_MAX_FAILURES` (default 5) failures within `LOGIN_WINDOW_SECONDS` (default 300 s) | Wait for the window to pass; the counter is in-memory and clears on restart |
| Locked out: last Admin demoted or deleted | The store refuses this — cannot happen | If locked out another way, accounts live in `data/users.json` — see [Backup and recovery](backup-recovery.md) |
| Stale "pending" manual-trigger state in another tab | Missed SSE push (older tab state) | The next periodic refresh (~15 s) corrects it; terminal transitions are force-pushed |
