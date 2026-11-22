# How Newsline splitting works

The weekly Amateur Radio Newsline MP3 is cut into story files before it airs. Operator behavior (download window, playlist, resume after busy) is in [Amateur Radio Newsline](arnewsline.md). This note is how the splitter uses speech models.

Whisper locates words in time. The splice point itself is a quiet stretch in the audio, chosen from those word times.

`split_report` in `app/newsline/split_job.py` always runs the forced-align pipeline with `align_model="base.en"` and `qa_model="small.en"`.

## Restart after processing

If memory pressure after a split is a concern, set `NEWSLINE_RESTART_AFTER_PROCESS=true` (Admin → Environment → Newsline checkbox). When a **scheduled** check downloads a new report and enters `split_report`, the process schedules a systemd restart after that check ends — whether the split succeeds or fails. If a transmission is in progress (COS busy / PTT keyed), restart is skipped and admins get an alert.

**Check for Newsline now** always pauses after a successful download and before split. The admin chooses Stop (no split), continue with restart after, or continue without restart. If nobody answers within 10 minutes, the check stops without splitting. That choice overrides the env toggle for that run.

## Libraries

| Package | Import | Role | Model |
| --- | --- | --- | --- |
| **stable-ts** (`stable-ts>=2.19.0`) | `stable_whisper` | Forced alignment of the official script onto the MP3 | `base.en` |
| **PyTorch** (`torch`, `torchaudio`) | — | Runs that stable-ts Whisper model (CPU wheels) | — |
| **faster-whisper** (`faster-whisper>=1.1.0`) | `faster_whisper` | Open transcription of short windows and exported slices | `base.en` for handoffs, `small.en` for QA |

`faster-whisper` is the CTranslate2 build of Whisper. A process-wide cache in `app/newsline/engine/whisper_model.py` keeps one model instance per worker while a split runs. One CTranslate2 model is not safe to transcribe on from several threads at once. When the pipeline finishes (success or failure), `clear_whisper_models()` drops those instances so the announcer process does not keep multi-GB Whisper weights loaded for the rest of the week.

### Cooler / slower splits (Linux host)

By default a split uses up to four parallel QA workers and four ffmpeg exports, and each Whisper/torch run may use every CPU core — fine on a desktop, hard on a small fanless NUC (high CPU % and temperature). To trade wall-clock time for heat, set in `.env` (or the service environment) and restart:

```bash
ARNEWSLINE_QA_WORKERS=1
ARNEWSLINE_EXPORT_WORKERS=1
ARNEWSLINE_CPU_THREADS=2
```

`ARNEWSLINE_QA_WORKERS=1` alone is not enough on a hot box: a single Whisper worker can still saturate all cores via CTranslate2. Cap threads with `ARNEWSLINE_CPU_THREADS` as well.

**rapidfuzz** is also on this path. It is fuzzy string matching: it compares Whisper’s words to phrases taken from the script (openers and sign-offs).

The first successful split downloads `base.en` and `small.en`. Later splits reuse them. A split usually finishes in about a minute and a half.

## Steps

1. **Script.** The downloaded transcript is parsed into speakable blocks (intro, stories, station-ID breaks, close).

2. **Forced alignment (stable-ts).** `align_script_words` in `app/newsline/engine/forced_align.py` joins those blocks into one text and calls `stable_whisper.load_model("base.en").align(...)` with `language="en"`, `original_split=True`, and silence suppression. Alignment is constrained to the known script and returns a start and end time for each word. The result is cached under `data/arnewsline/cache/` and removed when the split finishes. If the number of aligned blocks does not match the script, the run fails.

3. **Quiet cuts.** Those word times mark a search window between blocks. `build_forced_boundaries` picks the cut as the midpoint of the longest low-RMS quiet stretch in the audio. A long cart or ID gap gets two cuts: one after the previous speech, and one before the next.

4. **Handoff rewrite (faster-whisper).** Intro, break, and close boundaries are checked again. `transcribe_handoff_window` in `app/newsline/engine/handoff_window.py` decodes a few seconds around the provisional cut to 16 kHz mono PCM and runs faster-whisper `base.en` with word timestamps and `vad_filter=False`, so a short opener is kept. Sign-off and opener phrases from that segment’s script are matched with rapidfuzz, and the cut moves into the silence between those landmarks.

5. **Export and QA (faster-whisper).** Stories are sliced to MP3. Each file stays under the repeater timeout minus 2 seconds. Then up to three QA passes transcribe each file with faster-whisper `small.en`: the whole file when it is about 45 seconds or shorter, otherwise the first 18 seconds and the last 25. Slice QA turns voice-activity detection on (`vad_filter=True`). Fuzzy matching checks that the previous story’s sign-off did not bleed into the head, and that this story’s opener was not clipped. Bad cuts are nudged and the files are re-exported. Remaining critical issues fail the split.
