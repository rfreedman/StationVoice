# Amateur Radio Newsline

A **Newsline** library item plays the current week's [Amateur Radio Newsline](https://www.arnewsline.org/)
report as a sequence of short pieces. A normal weekly (or any other) schedule
points at that item. The app downloads and splits the report on its own during
a Thursday–Friday window.

This document covers both the operator behavior (download window, spoken
parts, schedule and airtime) and how the splitter works. Related settings are
collected at the end.

## Download window

[Amateur Radio Newsline](https://www.arnewsline.org/) makes their weekly release available late on Thursdays,
or early on Fridays, so checks for a new download run once an hour, in the station timezone, from the **Thursday check
start** (default 12:00) through the **Friday check stop** (default 18:00).
Both times are on the home screen.

The checks stop when a newly published report is downloaded and split
successfully during that window, or when Friday's stop time passes. If the app
starts while the window is open and this week's report is not ready yet, it
checks immediately, then continues at the hourly times after that moment.

If the feed is still the previous report, the app logs that the new episode is
not out yet and keeps checking. A failed split does not erase a report that
already split successfully.

If a new report downloads but processing fails, hourly checks keep looking at
the feed but do not retry that report. **Check for Newsline now** deletes that
report's audio, script, stories, and splitter cache, then downloads again. A
later report on the feed is still downloaded and split.

**Check for Newsline now** runs the same download and split once, including
outside the Thursday–Friday window. It does not change the hourly schedule.
The button is disabled while a check or split is already running, and while a
Newsline bulletin is on the air. The request returns immediately. The home
status line shows 'checking', then 'downloading' and 'processing' while a new report
is fetched and split, with the current processing step and elapsed time, then
the report number when that finishes. When the feed has no newer report, the
line says so and keeps the current report number. A failure is shown on that
line. The action is written to the log.

## Files

Reports live under `data/arnewsline/`:

- `state.json` — the report number, recorded only after a successful split
- `{report number}/Report{number}.mp3` and `nsln{number}.txt` — the downloaded episode
- `{report number}/stories/` — the split story files, including a zero-byte
  `station-id.mp3` marker file where the script has an identification break
- `cache/` — alignment cache used only while splitting; that report's entries
  are removed when the split finishes (success or failure)

Stories are packed so that each file stays under the repeater timeout minus 2
seconds (e.g. 178 seconds when the timeout is 180 seconds). This allows at least a 2-second
buffer between the end of a segment and the repeater's timeout, allowing for 
PTT to be released and settle before the repeater IDs.

## The spoken (Text-To-Speech) parts

A Newsline item has no script of its own. It points at ordinary spoken
announcements:

- **Opening** — optional, played once before the news stories
- **Station ID** — required, played in place of each (usually one) `station-id.mp3` marker
- **Closing** — optional, played once after the last news story.
- **Resume after busy** — optional, played in the same keyed transmission as
  the next story after the channel was busy during a gap (not used between
  the opening and the first story). Be sure to keep this one short to minimize
  the likelihood of hitting the repeater timeout!

Create those as normal announcements first (see
[Creating announcements](announcements.md)), then choose them on the Newsline
item. A Newsline item cannot be chosen as an opening, station ID, closing, or
resume. A spoken announcement that a Newsline item still uses cannot be
deleted.

On the Newsline editor, **Play** streams the latest split report in the
browser, using the opening, station ID, and closing chosen on that screen.
While a piece plays, the status shows **Streaming…**, the piece name, and
elapsed minutes and seconds for that piece. The editor fields are locked
until it finishes, you press **Stop**, or you leave that screen (Back,
another page, or closing the tab). A short tone marks simulated PTT key-up; a
slightly lower tone marks unkey. Between pieces it pauses for the usual PTT
lead and then the unkey gap from this screen, with the speakers idle rather
than playing silence. **Stop** ends the preview, including a pause. **Reset**
undoes unsaved edits on the announcement (including those choices and the
unkey gap) and stays disabled until something has changed. If no report is
ready, Play shows a warning and does not start.

## Schedule and airtime

Point a weekly schedule (Friday is typical) at the Newsline item. Playback
order is the opening, then the story files in name order with the station ID
substituted, then the closing. Each piece is its own transmission: the radio
keys, waits the usual PTT lead (`PTT_LEAD_SECONDS`, default 0.4 seconds),
plays that piece, then unkeys. While the bulletin airs, the home card shows
the current piece name; for report stories it also shows `news item x of y`
(opening, station ID, and closing are named but not counted).

Between pieces the radio stays unkeyed for at least the item's **PTT gap**
(default 2 seconds). A full bulletin is about 17 minutes plus the short
spoken parts and those gaps, so if played at the center of the slot or earlier, 
it finishes before the next half-hour slot when the channel stays clear.

If the latest report failed to download or process, or the story files are
missing, that slot does not play Newsline. The baseline that would have
played if the Newsline schedule were not there is used instead, or the slot
stays silent if none fits. Last week's files are not used after a failed
check. A bulletin airs only from the Thursday before the Friday named in its
script through the following Thursday; after that, last week's files are not
used even when they are still on disk. The home screen says Newsline is not
available and names what plays instead. A manual trigger of that schedule
does the same.

If the channel is busy before the first piece, that wait is limited by the
slot window and the busy give-up, the same as any other announcement. Once
the first piece has started, the bulletin finishes every remaining piece even
if that runs past the slot, the original give-up, or another schedule.

If the channel is busy during a gap, the radio stays unkeyed and waits for
the same clear hold as a normal key-up, including a fresh carrier check. The
home card shows **Paused · channel busy** or **Paused · clear hold** instead
of Running while that wait is in progress. If a resume announcement is set
and at least one story has already aired, that resume plays and then the next
story without dropping PTT between them. Busy between the opening and the
first story does not play the resume — the first story keys alone when the
channel clears. The bulletin does not start over. That wait is not a
scheduler retry.

A non-emergency that comes due while the bulletin is on the air is dropped.
It is not played later, and the baseline rotation does not advance for that
missed slot. A manual trigger during the bulletin keeps its usual lock retry.

An emergency has priority over the bulletin, but a story already on the air
is not cut off. If the emergency comes due in the middle of a piece, that
piece finishes, the emergency plays (with its own clear wait and busy
give-up, starting when its turn begins), and the bulletin continues with the
next piece. If the emergency comes due while the bulletin is unkeyed and
waiting for a clear channel, that wait stops and the emergency plays before
the next piece is keyed. If the emergency is dropped because the channel
stays busy, the bulletin still continues. A later non-emergency during the
emergency or the resumed bulletin is dropped.

## Spoken length

Opening, station ID, and closing use the same length limit as every other
spoken announcement: the repeater timeout minus 2 seconds. See
[How to schedule — spoken length](how-to-schedule.md#spoken-length). A
too-long opening or closing is left out and the stories still play. A
too-long station ID means the bulletin does not play; the slot's baseline
plays instead.

## ffmpeg and the first split

`ffmpeg` and `ffprobe` must be on `PATH`. If they are missing, the app logs a
warning and keeps running; download, split, and Newsline playback cannot run
until they are installed.

The first successful split downloads the speech models it needs (`base.en`
for alignment and `small.en` for a check of the exported audio). Later splits
reuse those models. A split usually finishes in several minutes and does not
block a slot that is ready to fire.

## How splitting works

The weekly Amateur Radio Newsline mp3 and matching text script is downloaded, 
and then the mp3 is cut into story files before it airs. 
[Whisper](https://openai.com/index/whisper/) compares the spoken words in the mp3 file 
to the written words in the script, and locates the times of the spoken words in the mp3. 
The splice point itself is a quiet stretch in the audio, chosen from those word times.

`split_report` in `app/newsline/split_job.py` always runs the forced-align
pipeline with `align_model="base.en"` and `qa_model="small.en"`.

### Restart after processing

If memory pressure _after_ a split is a concern, set
`NEWSLINE_RESTART_AFTER_PROCESS=true` (Admin → Environment → Newsline
checkbox). When a **scheduled** check downloads a new report and enters
`split_report`, the process schedules a systemd restart after that check
ends — whether the split succeeds or fails. If a transmission is in progress
(COS busy / PTT keyed), restart is skipped and admins get an alert.

**Note that** this is only supported for systemd services.
If systemd (systemctl) is not available, the situation will be logged, and the 
restart will be skipped. No error will be raised.

**Check for Newsline now** always pauses after a successful download and
before split. The admin chooses Stop (no split), continue with restart
after, or continue without restart. If there is no answers within 10 minutes, the
check stops without splitting. That choice overrides the env toggle for
that run.

### Libraries

| Package | Import | Role | Model |
| --- | --- | --- | --- |
| **stable-ts** (`stable-ts>=2.19.0`) | `stable_whisper` | Forced alignment of the official script onto the MP3 | `base.en` |
| **PyTorch** (`torch`, `torchaudio`) | — | Runs that stable-ts Whisper model (CPU wheels) | — |
| **faster-whisper** (`faster-whisper>=1.1.0`) | `faster_whisper` | Open transcription of short windows and exported slices | `base.en` for handoffs, `small.en` for QA |

`faster-whisper` is the CTranslate2 build of Whisper. A process-wide cache in
`app/newsline/engine/whisper_model.py` keeps one model instance per worker
while a split runs. One CTranslate2 model is not safe to transcribe on from
several threads at once. When the pipeline finishes (success or failure),
`clear_whisper_models()` drops those instances so the announcer process does
not keep multi-GB Whisper weights loaded for the rest of the week.

**rapidfuzz** is also on this path. It is fuzzy string matching: it compares
Whisper's words to phrases taken from the script (openers and sign-offs).

### Cooler / slower splits (Linux host)

By default a split uses up to four parallel QA workers and four ffmpeg
exports, and each Whisper/torch run may use every CPU core — fine on a
desktop, hard on a small fanless mini-pc (high CPU % and temperature). To trade
wall-clock time for heat, set in `.env` (or the service environment) and
restart:

```bash
ARNEWSLINE_QA_WORKERS=1
ARNEWSLINE_EXPORT_WORKERS=1
ARNEWSLINE_CPU_THREADS=2
```

`ARNEWSLINE_QA_WORKERS=1` alone is not enough on a hot box: a single
Whisper worker can still saturate all cores via CTranslate2. Cap threads
with `ARNEWSLINE_CPU_THREADS` as well.

### Steps

1. **Script.** The downloaded transcript is parsed into speakable blocks
   (intro, stories, station-ID breaks, close).

2. **Forced alignment (stable-ts).** `align_script_words` in
   `app/newsline/engine/forced_align.py` joins those blocks into one text
   and calls `stable_whisper.load_model("base.en").align(...)` with
   `language="en"`, `original_split=True`, and silence suppression.
   Alignment is constrained to the known script and returns a start and end
   time for each word. The result is cached under `data/arnewsline/cache/`
   and removed when the split finishes. If the number of aligned blocks does
   not match the script, the run fails.

3. **Quiet cuts.** Those word times mark a search window between blocks.
   `build_forced_boundaries` picks the cut as the midpoint of the longest
   low-RMS quiet stretch in the audio. A long cart or ID gap gets two cuts:
   one after the previous speech, and one before the next.

4. **Handoff rewrite (faster-whisper).** Intro, break, and close boundaries
   are checked again. `transcribe_handoff_window` in
   `app/newsline/engine/handoff_window.py` decodes a few seconds around the
   provisional cut to 16 kHz mono PCM and runs faster-whisper `base.en` with
   word timestamps and `vad_filter=False`, so a short opener is kept.
   Sign-off and opener phrases from that segment's script are matched with
   rapidfuzz, and the cut moves into the silence between those landmarks.

5. **Export and QA (faster-whisper).** Stories are sliced to MP3. Each file
   stays under the repeater timeout minus 2 seconds. Then up to three QA
   passes transcribe each file with faster-whisper `small.en`: the whole
   file when it is about 45 seconds or shorter, otherwise the first 18
   seconds and the last 25. Slice QA turns voice-activity detection on
   (`vad_filter=True`). Fuzzy matching checks that the previous story's
   sign-off did not bleed into the head, and that this story's opener was
   not clipped. Bad cuts are nudged and the files are re-exported. Remaining
   critical issues fail the split.

## Related settings

| Variable | Default | Meaning |
| --- | --- | --- |
| `NEWS_CHECK_START` | `12:00` | Thursday start of the check window (`HH:MM`, station timezone) |
| `NEWS_CHECK_STOP` | `18:00` | Friday end of that window (`HH:MM`) |
| `NEWS_CHECK_INTERVAL_HOURS` | `1` | Hours between checks inside the window (`0.5` is every 30 minutes; `0.5`–`24`) |
| `ARNEWSLINE_QA_WORKERS` | `min(4, CPUs)` | Parallel Whisper workers for slice QA. Set `1` for sequential ASR (cooler, slower) |
| `ARNEWSLINE_EXPORT_WORKERS` | `4` | Parallel ffmpeg story exports. Set `1` to encode one file at a time |
| `ARNEWSLINE_CPU_THREADS` | *(all cores)* | Cap PyTorch / CTranslate2 / OpenMP threads used by a split. Example: `2` on a small NUC that runs hot |
| `NEWSLINE_RESTART_AFTER_PROCESS` | `false` | Restart the systemd unit after a **scheduled** check splits a new report (skipped with an admin alert if a transmission is in progress). Manual check asks after download; unanswered choices time out after 10 minutes as Stop |
| `REPEATER_TIMEOUT_SECONDS` | `180` | Story files must stay under the timeout minus 2 seconds |

The Newsline check can also be started from the UI/API:
`POST /api/newsline/check` (Admin or Editor), with
`POST /api/newsline/check/choice` for the Stop / split-restart decision, and
`POST /api/newsline/preview` to stream the latest split report — see the
[API overview](api-overview.md).
