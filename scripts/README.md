# Scripts

## Station deploy helpers (`scripts-local/`)

Gitignored copies for this station: `deploy`, `start-remote`, `stop-remote`, `status`, `tail-remote`, and (optional) R2 helpers `backup-to-r2.py` / `list-r2-backups.py`. See [Deploying](../docs/deploy.md). Those R2 scripts are independent of the app (no `app.*` imports); install deps per each module docstring (`uv pip install boto3 botocore`).

```bash
scripts-local/start-remote
scripts-local/stop-remote
scripts-local/status
scripts-local/deploy
scripts-local/tail-remote
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
