# How to schedule

The overall repeater schedule is a series of **'slots'**: every hour and every half-hour
(00:00, 00:30, 01:00, … 23:30). Something is chosen for each slot. You write the
words once in the library, then point one or more schedules at that text.

## 1. Write the announcement

Open **New announcement** and save the text to be spoken by the Text-to-Speech
system (see [Creating announcements](announcements.md) for voices, pronunciation, and
the length limit). The same text can be used by
a baseline schedule, an overlay, or both. Timing does not live on the text.

## Spoken length

When you save a spoken (TTS) announcement, the app synthesizes it (including sentence
pauses and `[pause]` tags) and stores how long the audio is. An **audio file**
(MP3) announcement is measured the same way from the uploaded file. The limit is the
**repeater timeout** minus 2 seconds. The default timeout is 180 seconds, so the
limit is 178 seconds. The PTT lead after key-up sits inside that 2 second margin.

If a spoken announcement is over the limit, the text is still saved, and the editor tells
you the length, the limit, and to shorten it and save again. The announcement
is marked as 'too long'. Shorten it so that it is under the limit and save again to clear the mark.
An uploaded MP3 that is over the limit is **rejected** (not saved) with that same
length message—use a shorter file. Changing the repeater timeout on the Admin -> Environment
screen updates the too-long mark on already-saved spoken/audio items from the stored
length without synthesizing again.

A too-long announcement cannot be chosen for a new or updated schedule. 
The baseline that would have played is used instead.
If that baseline is also too long, the next baseline in the rotation that fits
is used. If none fit, the slot stays silent. The home screen, the schedule list,
the schedule editor, the slot clock, and the upcoming line name the schedule,
the announcement, its length, the limit, and what will play instead. A notice
on the home screen names the same substitution when the fire happens.

The same rule applies to an emergency. Amateur Radio Newsline uses this limit
for its opening, station ID, closing, and resume; see
[Amateur Radio Newsline](arnewsline.md).

## 2. Fill the clock with a baseline

Create a **Baseline** schedule and pick an announcement. That announcement will play in
every slot that no other schedule claims, exactly on the hour or half-hour.

You may add more than one baseline. They take turns: each is used once, then
the list starts over. Enable **Shuffle baseline order each cycle** if you want a
new order when the list restarts. Disable a baseline to take it out of the
rotation without deleting the text.

## 3. Override a slot when you need something else

Overlays replace the baseline for the slots they match. 
The overlay schedule can be shifted a few minutes earlier or later than the slot time,
by default ±10 minutes in either direction.

The overlay still belongs to that slot when it is shifted. 
Example: the 15:30 slot shifted −5 minutes transmits at **15:25** 
and still consumes the slot. 
Nothing plays at 15:30. The 15:00 slot is unchanged.

The shift must stay inside the slot window (default ±10 minutes around the slot
time).

### Schedule Types
- **Weekly** — a weekday and a slot. Example:
  Sundays, 21:00 slot (every Sunday).
- **Monthly** — the 1st, 2nd, 3rd, or 4th weekday of the month, plus designated months
  to skip.

- **Event countdown** — every slot from a start date up to an event slot, but
  not the event slot itself and not later slots that same day. After that day it
  stops. This is for a one-time event.

  This is useful for announcements about one-time upcoming events like 'Field Day'.

- **Monthly countdown** — the same until-event rule as Event countdown, 
  but repeating each month.
  Choose the event slot (for example the 1st Wednesday at 19:00) and how many days
  before that event the announcement should start. Skip months if needed.

  This is useful for monthly repeating events, like club meetings.

- **Silence** — occupis a slot and transmits nothing (for example while a net is
  already on the air, or during overnight hours).

- **Emergency** — wins every slot until you turn it off. It does not interrupt a
  transmission that has already started.

Template names such as “Weekly” are only starting points. Rename the
schedule to whatever the operators will recognize.

## 4. When two overlays want the same slot

The higher priority wins. Defaults: emergency 100, weekly/monthly 50, event
countdown 20. A Sunday 21:00 net therefore beats a two-day-long meeting announcement on
that one slot. Two overlays of the same priority on the same slot cannot both be
saved.

## Today's schedule grid vs what played

The home **schedule clock** shows what the app would fire **now** if each slot ran
today, using the current baseline rotation and shuffle setting. It is **not** a log
of what already went on-air.

Earlier today, baseline rows can show a **different announcement name** than what
actually transmitted if you edited schedules, changed baseline order, shuffled, or
restarted the server after those slots. Overlays and fires always **re-resolve** at
fire time; the grid for past slots is only a simulation for planning.

For what really aired, use station records or logs (`data/logs/announcements.log` on
the Linux host), not the UI clock alone.

## Busy channel behavior

Each announcement has its own **busy retry** and **busy give-up** values
(pre-filled from the settings defaults). If the repeater is busy when a
slot fires, the app retries at the busy-retry interval until the give-up
deadline, then drops that fire (it is not played later). On the DRA
backend, an optional clear hold
(`DRA_CLEAR_SECONDS`) requires continuous idle before PTT — see
[Radio backend](radio-backend.md).

## Related settings

| Setting | Default | Meaning |
| --- | --- | --- |
| `REPEATER_TIMEOUT_SECONDS` | `180` | Repeater time limit for one transmission (`30`–`600`). Spoken audio, uploaded MP3 announcements, and Newsline story files must finish 2 seconds sooner |
| `SLOT_HALF_WINDOW_MINUTES` | `10` | How far an overlay may shift from its slot center |
| `BUSY_RETRY_SECONDS` | `5` | Retry interval while the channel is busy (pre-filled for new announcements) |
| `BUSY_GIVE_UP_SECONDS` | `45` | Drop this fire if still busy after this long (pre-filled for new announcements) |
| `TIMEZONE` | `America/New_York` | Clock for schedules |
| `TRIGGER_NOW` | `false` | Dev only: show **Trigger now** on schedule rows (does not change Last or the next slot) |

These are environment settings — see the
[configuration reference](configuration.md). `PUT /api/settings`
(baseline shuffle and the slot window) is described in the
[API overview](api-overview.md). If something does not air, see
[Troubleshooting](troubleshooting.md) and
[Manual operation](manual-operations.md).

## Suggested first setup

1. Create a station-ID announcement and a baseline schedule that uses it.
On it's own, this announcement will play in every slot.

2. If you have a weekly net, add a Weekly overlay. For example, if your net is on 
Sunday nights at 21:00, create a meeting announcement, and  a schedule for it for 
Sundays at 21:00, −5 minutes. This will override the baseline schedule in this slot.

3. For an upcoming in-person club meeting, add a meeting announcement and an event 
countdown schedule from a few days before the meeting until the meeting slot.
This will also override the baseline schedule in it's slot.
