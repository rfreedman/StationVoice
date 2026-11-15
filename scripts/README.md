# Scripts

## `start-remote`

Run from the **dev machine**: SSH to the Linux host and `systemctl start` the app unit. Does not pull git. Waits for `Startup complete` in the unit journal. Defaults: host `dvra-announcements`, unit `dvra-announcements`. Needs passwordless sudo for that unit (see [Deploying](../docs/deploy.md)).

```bash
scripts/start-remote                 # default host dvra-announcements
scripts/start-remote other-host      # or DEPLOY_HOST=… SERVICE_NAME=…
```

## `stop-remote`

Run from the **dev machine**: SSH and `systemctl stop` the app unit (SIGTERM via systemd; never SIGKILL). Waits up to `DEPLOY_STOP_TIMEOUT` seconds (default 30). Exits 0 if the unit was already inactive.

```bash
scripts/stop-remote
scripts/stop-remote other-host
```

## `deploy`

Run from the dev machine: stops the systemd unit, fast-forwards git on the host, starts the unit again (`./serve.sh` as `ExecStart`). Defaults: host `dvra-announcements`, path `/home/announce/dvra-repeater-announcements`, unit `dvra-announcements`. `DEPLOY_STOP_TIMEOUT` (default 30) and `DEPLOY_START_TIMEOUT` (default 180) are the stop and startup waits. Needs uv and NOPASSWD systemctl on the host. Details: [Deploying](../docs/deploy.md).

```bash
scripts/deploy
scripts/deploy other-host
```

## `tail-nuc`

Tail `data/logs/announcements.log` on the Linux host (name is historical).

```bash
scripts/tail-nuc
scripts/tail-nuc dvra-announcements
```

## `dra36m_check.py`

Bench verification before wiring the announcements app to the radios. A **DRA** (Digital Radio Adapter) is the USB box between the computer and one radio. This project uses the [Masters Communications **DRA-36M**](https://www.masterscommunications.com/products/radio-adapter/dra/dra36m.html). It plays the announcement into the radio and keys the transmitter. The setting `TTS_RADIO_BACKEND=dra` means the app is using those adapters.

**Full procedures, pass criteria, and flags:** [`docs/final-hardware/dra36m-check-tests.md`](../docs/final-hardware/dra36m-check-tests.md)

**Record your rig:** [`docs/final-hardware/bench-record.md`](../docs/final-hardware/bench-record.md)

Quick start (JU1 on, JU5=A, **JU3=L** on both DRA; `-c left` is the script default):

```bash
source .venv/bin/activate
python scripts/dra36m_check.py retest -c left --with-voice --lead 0.6
```

Run this on the Linux host. Radios have not been tried on macOS. **Linux:** udev rules + `plugdev` for CM119 HID/USB — [`dra36m-check-tests.md`](../docs/final-hardware/dra36m-check-tests.md#linux-udev-and-plugdev).

Subcommands: `probe`, **`probe-all`**, `monitor`, `snap`, `ptt`, `tone`, `smoke`, `voice`, `voice-gate`, `retest`, **`dual-smoke`**, **`dual-voice`**, **`dual-retest`** (dual = both DRAs on the Linux host).

## `work_time.py`

Estimate active work time from commit timestamps. Gaps of 2 hours or less count as one sitting; longer gaps start a new one. The quoted figure adds a 45-minute lead-in per sitting, for work before that sitting's first commit.

```bash
python scripts/work_time.py
python scripts/work_time.py --threshold 3
```
