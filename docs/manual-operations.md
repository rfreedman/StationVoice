# Manual operation

How to transmit on demand: **Trigger now**, what its status shows while the
channel is busy, how it interacts with the schedule and with Newsline, and
what to do after a restart.

## Trigger now

**Trigger now** (when enabled) transmits a schedule's announcement immediately, 
regardless of the scheduled time.

- The button is controlled by the `TRIGGER_NOW` setting (default **off**;
  toggle in Admin → Environment or set in `.env`). Only Admin and Editor
  roles see it.

- On the API it is
  `POST /api/schedules/{schedule_id}/trigger` (Admin or Editor).
- **Manual triggers never change slot jobs.** Triggering does not reschedule
  anything, does not advance the baseline rotation, and does not change what
  the next slot plays. A slot that fires later still plays normally.
- The trigger uses the announcement's own busy retry and give-up values,
  the same as a scheduled fire.

### Status while a trigger runs

The home card follows the actual radio phase rather than a generic
"in progress" label:

- **Busy** — the channel is busy; the trigger is retrying at the
  announcement's busy-retry interval until its give-up deadline.
- **Clear-hold countdown** — on the DRA backend with
  `DRA_CLEAR_SECONDS` > 0, the trigger waits for that much continuous
  clear channel before keying. The countdown is shown even while a busy
  retry is still in flight, because retries spend most of their time
  blocked in the clear wait. Background COS polling (`DRA_COS_TRACK`)
  means time the channel was already quiet before the trigger counts toward
  the hold, so the transmit can key immediately.
- When the trigger finishes (transmitted, dropped, or given up), the home
  status is pushed live to all open tabs. You do not have to wait for
  the periodic refresh. A dropped trigger leaves a dismissible drop notice.

On the stub backend the trigger transmits instantly (the channel never
appears busy), which makes it a good way to verify the UI flow without
radios.

### Failure modes

- **Another announcement is playing** — the trigger does not queue behind
  the running transmission immediately; it retries at the announcement's
  busy-retry interval. If the playback lock is still held past the give-up
  window, the fire is dropped with "Another announcement was still playing
  when the give-up timer expired", and the drop notice appears on the home
  screen.
- **Still busy at the give-up deadline** — the fire is dropped (`409`, with
  the drop detail such as "Channel still busy" or "Another announcement was
  still playing when the give-up timer expired"), and the drop notice appears
  on the home screen. The trigger is not retried later. A disabled schedule
  returns `400`; an unknown schedule returns `404`.
- **DRA USB unplugged mid-transmit** — the in-flight transmit aborts and
  the fire is reported as dropped (`TransmitAbortError` /
  `FireOutcome.DROPPED_USB`); PTT is always released, never left keyed.
- **Channel keys up in the last moment before transmit** — the final COS
  check (and, on DRA, `DRA_FINAL_CHECK_SECONDS` of continued reading after
  the clear hold) cancels the key-up and the trigger retries.

## Trigger now and Newsline

- Point Trigger now at the **Newsline schedule** to air the bulletin outside
  its slot. The same availability rules apply: if the report failed to
  download or split, the trigger plays the baseline substitution instead
  (see [Amateur Radio Newsline](arnewsline.md)).
- A manual trigger **during** a bulletin keeps its usual lock retry — it
  does not interrupt the bulletin; it retries behind the running
  transmission and is dropped if the lock is still held at give-up.

## After an outage or restart

Deploy and any restart start a **new process** (see
[Operations — process restart and in-memory state](operations.md#process-restart-and-in-memory-state)).
In-flight manual-trigger retries and busy-retry jobs are dropped, and a slot
whose fire time already passed is **not** played late. If something did not
air:

- Use **Trigger now** on the schedule to transmit it now, or
- Wait for the next slot, and
- Check the logs (`data/logs/announcements.log`) for deferred fires that
  will not run until triggered again.

Admin → Environment → **Restart application** 
causes the application to exit, and if it was running as a systemd service, 
it will be restarted. See [Operations](operations.md).

## Other manual actions

- **Check for Newsline now** — one download/split outside the scheduled
  window, with its own stop/continue choice after download (see
  [Amateur Radio Newsline](arnewsline.md#download-window)).
- **Speak preview / Play** — browser-side previews that never key the radio
  (see [Creating announcements](announcements.md)).
- **Silence overlays** — for planned off-air time (nets, meetings, overnight), a
  Silence overlay is the scheduled equivalent of standing down; see
  [How to schedule](how-to-schedule.md).
