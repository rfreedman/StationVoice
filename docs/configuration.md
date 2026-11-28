# Configuration reference

Every StationVoice setting, its default, and its meaning. StationVoice is
configured with environment variables; an optional `.env` file in the
project root (see [`.env.example`](../.env.example)) is loaded at startup —
variables already set in the shell override that file. Subject docs
([Scheduling](how-to-schedule.md), [Radio backend](radio-backend.md),
[Newsline](arnewsline.md)) describe the behavior that these settings control.

## Core
<table>
    <tr>
      <th>Variable</th>
      <th>Default</th>  
      <th>Meaning</th>
    </tr>
    <tr>
      <td><code>TTS_DEFAULT_VOICE</code></td>
      <td><code>en_US-ryan-medium</code></td>
      <td>Default Piper voice</td>
    </tr>
    <tr>
      <td><code>TTS_VOICES_DIR</code></td>
      <td><code>./voices</code></td>
      <td>Model cache (<code>voices/piper/</code> holds <code>.onnx</code> files)</td>
    </tr>
    <tr>
      <td><code>TTS_PIPER_VOICES_FILE</code></td>
      <td><code>config/piper-voices.json</code></td>
      <td>Featured voice catalog (UI list, aliases, startup preload)</td>
    </tr>
    <tr>
      <td><code>TTS_PIPER_QUALITIES</code></td>
      <td><code>all</code></td>
      <td><code>all</code> = list/preload every <code>voices/piper/*.onnx</code>; <code>medium</code> = only <code>*-medium</code></td>
    </tr>
    <tr>
      <td><code>TTS_SPEED</code></td>
      <td><code>1.0</code></td>
      <td>Speaking rate (<code>&lt; 1</code> is slower)</td>
    </tr>
    <tr>
      <td><code>TTS_SENTENCE_PAUSE</code></td>
      <td><code>0.25</code></td>
      <td>Silence between sentences, in seconds</td>
    </tr>
    <tr>
      <td><code>HOST</code> / <code>PORT</code></td>
      <td><code>0.0.0.0</code> / <code>8000</code></td>
      <td>Bind address</td>
    </tr>
    <tr>
      <td><code>TIMEZONE</code></td>
      <td><code>America/New_York</code></td>
      <td>Clock for schedules</td>
    </tr>
    <tr>
      <td><code>DATA_DIR</code></td>
      <td><code>./data</code></td>
      <td>Saved announcements JSON</td>
    </tr>
    <tr>
      <td><code>USERS_PATH</code></td>
      <td><code>$DATA_DIR/users.json</code></td>
      <td>Web UI users</td>
    </tr>
    <tr>
      <td><code>SESSION_SECRET</code></td>
      <td>auto (<code>data/.session_secret</code>)</td>
      <td>Signs login session cookies</td>
    </tr>
    <tr>
      <td><code>SESSION_IDLE_SECONDS</code></td>
      <td><code>1800</code> (30 min)</td>
      <td>Log out after this much idle time (the UI's automatic 15 s refreshes do not count as activity)</td>
    </tr>
    <tr>
      <td><code>LOGIN_MAX_FAILURES</code></td>
      <td><code>5</code></td>
      <td>Failed sign-ins for the same username from the same client before <code>429</code></td>
    </tr>
    <tr>
      <td><code>LOGIN_WINDOW_SECONDS</code></td>
      <td><code>300</code></td>
      <td>How long those failures stay counted, in seconds</td>
    </tr>
    <tr>
      <td><code>TTS_PCM_CACHE_DIR</code></td>
      <td><code>./data/pcm</code></td>
      <td>Pre-rendered announcement PCM (written on save and at startup; scheduled fires play this)</td>
    </tr>
    <tr>
      <td><code>LOG_DIR</code></td>
      <td><code>./data/logs</code></td>
      <td>Daily rotating <code>announcements.log</code> (app + uvicorn server) and filtered <code>access.log</code> (page/asset/major API hits; home polls/health/SSE omitted). Access is file-only (not stdout/stderr). Kept 30 days (<code>LOG_KEEP_DAYS</code>)</td>
    </tr>
    <tr>
      <td><code>PTT_LEAD_SECONDS</code></td>
      <td><code>0.4</code></td>
      <td>Delay after PTT before audio (on <strong>dra</strong>, silence is streamed on USB; on <strong>stub</strong>, host sleep)</td>
    </tr>
    <tr>
      <td><code>RADIO_BACKEND</code></td>
      <td><code>stub</code></td>
      <td><code>stub</code> = in-memory PTT/COS. A <strong>DRA</strong> (Digital Radio Adapter) is the USB box between the computer and one radio. This project uses the <a href="https://www.masterscommunications.com/products/radio-adapter/dra/dra36m.html">Masters Communications <strong>DRA-36M</strong></a>. It plays the announcement into the radio and keys the transmitter. <code>dra</code> means the app is using those adapters (requires <code>hidapi</code>). If <code>dra</code> is set but no DRA is attached, startup falls back to stub with one admin alert. Confirm the active mode in the startup log: <code>(radio mode: stub)</code> or <code>(radio mode: dra)</code>. On <strong>stub</strong>, triggers still use host PortAudio — headless Linux needs a Pulse/PipeWire session (see <a href="radio-backend.md#stub-backend-on-headless-linux">Stub backend on headless Linux</a>)</td>
    </tr>
    <tr>
      <td><code>SYSTEMD_UNIT</code></td>
      <td><code>dvra-announcements</code></td>
      <td>Bare systemd unit name (no <code>.service</code> suffix) used by Admin → Restart on the Linux host</td>
    </tr>
    <tr>
      <td><code>SLOT_HALF_WINDOW_MINUTES</code></td>
      <td><code>10</code></td>
      <td>How far an overlay may shift from its slot center</td>
    </tr>
    <tr>
      <td><code>TRIGGER_NOW</code></td>
      <td><code>false</code></td>
      <td>Dev only: show <strong>Trigger now</strong> on schedule rows (does not change Last or the next slot)</td>
    </tr>
    <tr>
      <td><code>BUSY_RETRY_SECONDS</code></td>
      <td><code>5</code></td>
      <td>Retry interval while the channel is busy; also the value pre-filled for a <strong>new announcement</strong> in the UI</td>
    </tr>
    <tr>
      <td><code>BUSY_GIVE_UP_SECONDS</code></td>
      <td><code>45</code></td>
      <td>Drop this fire if still busy after this long; also pre-filled for a new announcement</td>
    </tr>
    <tr>
      <td><code>SCHEDULER_MAX_WAIT_SECONDS</code></td>
      <td><code>5</code></td>
      <td>How long the scheduler may sleep before checking the clock again</td>
    </tr>
    <tr>
      <td><code>REPEATER_TIMEOUT_SECONDS</code></td>
      <td><code>180</code></td>
      <td>Repeater time limit for one transmission (<code>30</code>–<code>600</code>). Spoken audio, uploaded MP3 announcements, and Newsline story files must finish 2 seconds sooner</td>
    </tr>
    <tr>
      <td><code>AUDIO_ANNOUNCEMENT_MAX_BYTES</code></td>
      <td><code>5242880</code> (5 MiB)</td>
      <td>Max size for an uploaded MP3 library announcement (<code>65536</code>–<code>20971520</code>)</td>
    </tr>
</table>

## DRA radio backend (`RADIO_BACKEND=dra`)

Details and app behavior: [Radio backend](radio-backend.md).

<table>
  <colgroup>
    <col style="width: 22%" />
    <col style="width: 18%" />
    <col style="width: 60%" />
  </colgroup>
  <thead>
    <tr><th>Variable</th><th>Default</th><th>Meaning</th></tr>
  </thead>
  <tbody>
    <tr>
      <td><code>DRA_USB_CHANNEL</code></td>
      <td><code>left</code></td>
      <td>USB channel for DATA IN (<strong>JU3=L</strong> → <code>left</code>)</td>
    </tr>
    <tr>
      <td><code>DRA_COS_LINE</code></td>
      <td><code>vol_dn</code></td>
      <td>HID COS decode (<code>vol_dn</code> or <code>allstar3</code>)</td>
    </tr>
    <tr>
      <td><code>DRA_COS_ACTIVE_HIGH</code></td>
      <td><code>false</code></td>
      <td>Set <code>true</code> if idle/busy labels swap on <code>monitor</code></td>
    </tr>
    <tr>
      <td><code>DRA_AUDIO_DEVICES</code></td>
      <td><em>(auto)</em></td>
      <td>Optional comma list of PortAudio substrings or indices (<strong>one per DRA</strong>). On the Linux host with <strong>two radios</strong>, use fixed USB ports; set this only if auto-detection order is wrong</td>
    </tr>
    <tr>
      <td><code>DRA_CLEAR_SECONDS</code></td>
      <td><code>0</code></td>
      <td>Continuous COS idle required after synthesize, before PTT (<code>10</code> matches bench voice-gate)</td>
    </tr>
    <tr>
      <td><code>DRA_CLEAR_POLL_SECONDS</code></td>
      <td><code>0.25</code></td>
      <td>COS poll interval during clear wait and background idle tracking</td>
    </tr>
    <tr>
      <td><code>DRA_FINAL_CHECK_SECONDS</code></td>
      <td><code>1.0</code></td>
      <td>After the clear hold, keep reading COS this long before PTT; any busy read cancels (catches a key-up as the UI countdown ends). Only applies when <code>DRA_CLEAR_SECONDS</code> &gt; 0</td>
    </tr>
    <tr>
      <td><code>DRA_COS_TRACK</code></td>
      <td><code>true</code></td>
      <td>Background COS polls while the scheduler runs (idle before Trigger now counts toward clear)</td>
    </tr>
    <tr>
      <td><code>DRA_HID_PATH</code></td>
      <td><em>(auto)</em></td>
      <td>Hex HID path to pin <strong>one</strong> CM119 (a <strong>single</strong> DRA on the Linux host). <strong>Omit when two DRAs are connected</strong> — each radio needs its own CM119 HID</td>
    </tr>
    <tr>
      <td><code>DRA_ALSA_UNMUTE</code></td>
      <td><code>true</code></td>
      <td>Linux <strong>dra</strong> only: run <code>amixer</code> to unmute CM119 <strong>Speaker</strong> at startup. Set <code>false</code> to skip</td>
    </tr>
    <tr>
      <td><code>DRA_ALSA_SPEAKER_LEVEL</code></td>
      <td><code>100%</code></td>
      <td>ALSA <strong>Speaker</strong> level passed to <code>amixer sset</code> when unmuting</td>
    </tr>
    <tr>
      <td><code>DRA_PREFER_ALSA_HW</code></td>
      <td><code>1</code></td>
      <td>Prefer <code>(hw:…)</code> ALSA device names over Pulse/PipeWire sink names (PipeWire sink playback can hang PortAudio). Set <code>0</code> to use the Pulse sink</td>
    </tr>
    <tr>
      <td><code>DRA_LINUX_PLAYBACK</code></td>
      <td><code>aplay</code></td>
      <td>Linux playback path: <code>aplay -D hw:N,0</code> (then <code>plughw</code>) by default; set <code>portaudio</code> to force PortAudio</td>
    </tr>
  </tbody>
</table>

## Amateur Radio Newsline

Behavior: [Amateur Radio Newsline](arnewsline.md).

<table>
  <colgroup>
    <col style="width: 22%" />
    <col style="width: 18%" />
    <col style="width: 60%" />
  </colgroup>
  <thead>
    <tr><th>Variable</th><th>Default</th><th>Meaning</th></tr>
  </thead>
  <tbody>
    <tr>
      <td><code>NEWS_CHECK_START</code></td>
      <td><code>12:00</code></td>
      <td>Thursday start of the Amateur Radio Newsline check window (<code>HH:MM</code>, station timezone)</td>
    </tr>
    <tr>
      <td><code>NEWS_CHECK_STOP</code></td>
      <td><code>18:00</code></td>
      <td>Friday end of that window (<code>HH:MM</code>)</td>
    </tr>
    <tr>
      <td><code>NEWS_CHECK_INTERVAL_HOURS</code></td>
      <td><code>1</code></td>
      <td>Hours between checks inside the window (<code>0.5</code> is every 30 minutes; <code>0.5</code>–<code>24</code>)</td>
    </tr>
    <tr>
      <td><code>ARNEWSLINE_QA_WORKERS</code></td>
      <td><code>min(4, CPUs)</code></td>
      <td>Parallel Whisper workers for slice QA during a Newsline split. Set <code>1</code> for sequential ASR (cooler, slower)</td>
    </tr>
    <tr>
      <td><code>ARNEWSLINE_EXPORT_WORKERS</code></td>
      <td><code>4</code></td>
      <td>Parallel ffmpeg story exports during a split. Set <code>1</code> to encode one file at a time</td>
    </tr>
    <tr>
      <td><code>ARNEWSLINE_CPU_THREADS</code></td>
      <td><em>(all cores)</em></td>
      <td>Cap PyTorch / CTranslate2 / OpenMP threads used by a split. Example: <code>2</code> on a small NUC that runs hot</td>
    </tr>
    <tr>
      <td><code>NEWSLINE_RESTART_AFTER_PROCESS</code></td>
      <td><code>false</code></td>
      <td>After a <strong>scheduled</strong> Newsline check starts splitting a new report, restart the systemd unit when the check finishes (success or failure). Skipped with an admin alert if a transmission is in progress. Manual <strong>Check for Newsline now</strong> asks after download (Stop / continue with restart / continue without); unanswered choices time out after 10 minutes as Stop</td>
    </tr>
  </tbody>
</table>

## Station identity

<table>
  <colgroup>
    <col style="width: 22%" />
    <col style="width: 18%" />
    <col style="width: 60%" />
  </colgroup>
  <thead>
    <tr><th>Variable</th><th>Default</th><th>Meaning</th></tr>
  </thead>
  <tbody>
    <tr>
      <td><code>STATION_CALL</code></td>
      <td><em>(required)</em></td>
      <td>Call sign shown in the UI / idle assertion name</td>
    </tr>
    <tr>
      <td><code>STATION_NAME</code></td>
      <td><em>(required)</em></td>
      <td>Club or station name (page heading and logo alt text)</td>
    </tr>
    <tr>
      <td><code>APP_TITLE</code></td>
      <td><code>{STATION_CALL} Announcements</code></td>
      <td>FastAPI / browser title; omit to use the derived default</td>
    </tr>
  </tbody>
</table>

Startup fails if `STATION_CALL` or `STATION_NAME` is missing or blank.

## Defer timing (fixed in code, not env vars)

These complement `BUSY_RETRY_SECONDS` on each announcement and
`DRA_CLEAR_SECONDS` / `DRA_CLEAR_POLL_SECONDS` for COS. They are **not**
configurable today; names live in `app/fire.py` and `app/scheduler.py` if you
need to tune behavior in a fork.

<table>
  <colgroup>
    <col style="width: 30%" />
    <col style="width: 10%" />
    <col style="width: 60%" />
  </colgroup>
  <thead>
    <tr><th>Constant</th><th>Default</th><th>Role</th></tr>
  </thead>
  <tbody>
    <tr>
      <td><code>DEFER_CLEAR_NONBLOCKING_MAX_SECONDS</code></td>
      <td><code>0.5</code></td>
      <td>After <strong>Trigger now</strong>, first clear-hold retry is scheduled within this cap so the HTTP request returns while the COS poll thread keeps waiting.</td>
    </tr>
    <tr>
      <td><code>DEFER_RETRY_WHEN_CLEAR_MET_CAP_SECONDS</code></td>
      <td><code>1.0</code></td>
      <td>When the clear hold is already satisfied, defer retries run at most this often instead of the full per-announcement busy retry interval.</td>
    </tr>
    <tr>
      <td><code>SCHEDULER_MIN_WAKE_SECONDS</code></td>
      <td><code>0.5</code></td>
      <td>Shortest sleep between APScheduler wakeups (avoids missing fires under macOS App Nap).</td>
    </tr>
    <tr>
      <td><code>MANUAL_NUDGE_SKIP_IF_RUN_WITHIN_SECONDS</code></td>
      <td><code>0.2</code></td>
      <td>Background COS nudge does not reschedule a manual defer that is already about to run.</td>
    </tr>
    <tr>
      <td><code>MANUAL_NUDGE_PTT_TIMER_PROTECT_SECONDS</code></td>
      <td><code>2.0</code></td>
      <td>Short PTT defer retries keep their scheduled time instead of being pulled forward when the channel clears.</td>
    </tr>
    <tr>
      <td><code>MANUAL_NUDGE_MIN_WAIT_FOR_UNKNOWN_KIND_SECONDS</code></td>
      <td><code>2.0</code></td>
      <td>Only <code>busy</code> / <code>clear</code> / <code>ptt</code> defers with a longer wait are nudged when idle credit meets the clear hold.</td>
    </tr>
    <tr>
      <td><code>MANUAL_NUDGE_RUN_DELAY_MS</code></td>
      <td><code>50</code></td>
      <td>How soon to run a nudged manual defer after the clear hold is met.</td>
    </tr>
  </tbody>
</table>

On a low-RAM host, set `TTS_PIPER_QUALITIES=medium` so only medium models
are listed and preloaded. High-quality voices use more CPU and RAM.

## Piper voices

Browse samples at [piper-samples](https://rhasspy.github.io/piper-samples/)
and downloadable models on Hugging Face
[`rhasspy/piper-voices`](https://huggingface.co/rhasspy/piper-voices).

**Featured voices** live in
[`config/piper-voices.json`](../config/piper-voices.json) (override with
`TTS_PIPER_VOICES_FILE`). They appear in the UI with friendly names/aliases,
are **preloaded at startup**, and are **re-downloaded automatically** if the
matching `.onnx` under `voices/piper/` is missing. Deleting a featured model
file without removing it from the JSON means it comes back on the next start
(Hugging Face or custom URLs).

**Download source:** omit `onnx_url` / `config_url` to use Piper's Hugging
Face download for standard voice ids (`en_US-…-medium`, etc.). Set optional
`onnx_url` (and usually `config_url`) to HTTP(S) URLs for custom or mirrored
models; files are still stored as `{id}.onnx` and `{id}.onnx.json` under
`voices/piper/`.

**Extra voices on disk:** copy `{id}.onnx` and `{id}.onnx.json` into
`voices/piper/`. They show up in the UI (subject to `TTS_PIPER_QUALITIES`)
and are loaded from disk when present. They are **not** re-downloaded if you
delete them, unless something later asks for that exact voice id (for example
Speak / prepare for an announcement that still references it).

**Add a featured voice**

1. Edit [`config/piper-voices.json`](../config/piper-voices.json) and copy an
   existing object in the `voices` array.
2. Set `id` to the Piper voice id (for example `en_US-libritts_r-medium`),
   or any filename stem you want on disk for a custom download.
3. Choose a unique `alias` (used by the CLI, e.g. `--voice libritts`).
4. Fill `name`, `gender`, `locale`, `quality`, and `description`.
5. Optionally set `onnx_url` and `config_url` to HTTPS (or HTTP) download
   locations; leave them out to use Hugging Face for standard Piper ids.
6. Restart the app. The first startup downloads the model into `voices/piper/`
   if it is not already there.

Example with custom URLs (commented — do not paste live secrets into the
default JSON):

```json
{
  "id": "custom",
  "alias": "custom",
  "name": "Custom",
  "gender": "male",
  "locale": "en_US",
  "quality": "medium",
  "description": "Custom voice.",
  "onnx_url": "https://example.com/voices/custom.onnx",
  "config_url": "https://example.com/voices/custom.onnx.json"
}
```

## Admin email (optional plugin)

Admin email delivery is optional. Core always logs operational failures via
`alert_admins`; email is only sent when a notifier plugin is present under
`plugins/` (that directory is empty by default) **and**
`ADMIN_EMAIL_NOTIFICATIONS` is enabled (default on when unset). Use
Admin → Environment → **Send email notifications** to mute start/stop and
alert emails without removing the plugin.

An example Bird (MessageBird) plugin ships in
[`plugin-examples/bird_email.py`](../plugin-examples/bird_email.py). Enable
it by copying that file into `plugins/` (any filename works).
`plugin-examples/` is never loaded. Other notifier plugins should follow the
same pattern: document their Python packages in the module docstring;
install those packages into the venv separately (they are not project
dependencies).

For the Bird example:

```bash
cp plugin-examples/bird_email.py plugins/
uv pip install 'messagebird-sdk>=0.137.0'
```

If the plugin is in `plugins/` but its Python packages or send credentials
are missing, startup **fails** after a clear error from the plugin's
`validate_requirements_installed()` (install / `.env.secrets` hint
included). Put Bird settings in `.env.secrets` (see
[`.env.secrets.example`](../.env.secrets.example)), not in the main `.env`.
The app loads `.env.secrets` at startup (shell env still wins).
Admin → Environment shows **Admin alerts** / `ADMIN_EMAILS` only when an
email plugin is loaded; other secrets stay file-only. The station-local R2
backup script uses the same plugin when available, otherwise logs only.

<table>
  <colgroup>
    <col style="width: 22%" />
    <col style="width: 18%" />
    <col style="width: 60%" />
  </colgroup>
  <thead>
    <tr><th>Variable</th><th>Default</th><th>Meaning</th></tr>
  </thead>
  <tbody>
    <tr>
      <td><code>BIRD_API_KEY</code></td>
      <td><em>(required to send)</em></td>
      <td>Bird API key (Bird example plugin)</td>
    </tr>
    <tr>
      <td><code>EMAIL_FROM</code></td>
      <td><em>(required to send)</em></td>
      <td>From address</td>
    </tr>
    <tr>
      <td><code>EMAIL_FROM_NAME</code></td>
      <td><code>Repeater Announcements</code></td>
      <td>From display name</td>
    </tr>
    <tr>
      <td><code>ADMIN_EMAILS</code></td>
      <td><em>(required to send)</em></td>
      <td>Comma-separated admin recipients (editable in Admin UI when a plugin is present)</td>
    </tr>
    <tr>
      <td><code>ADMIN_EMAIL_NOTIFICATIONS</code></td>
      <td><code>1</code></td>
      <td><code>1</code>/<code>0</code> (or true/false): send admin emails when a plugin is present. Missing means on. Not part of config history / revert.</td>
    </tr>
    <tr>
      <td><code>PLUGINS_DIR</code></td>
      <td><code>&lt;repo&gt;/plugins</code></td>
      <td>Override plugins directory (tests)</td>
    </tr>
  </tbody>
</table>

Duplicate alerts with the same debounce key are suppressed for 15 minutes.
