# Creating announcements

Announcements are **library items**. You write the words once, then one or
more schedules point at that item — the text is never duplicated into
schedule entries. Depending on the item, the content is:

- **Spoken (TTS)** — text synthesized by Piper when you save it. Most
  announcements are this kind.
- **Audio file** — an uploaded MP3, played as-is.
- **Amateur Radio Newsline** — a special item that plays the current week's
  split report. See [Amateur Radio Newsline](arnewsline.md).

## Creating a spoken announcement

Open **New announcement** and save the spoken text. The same text can be used
by a baseline schedule, an overlay, or both — timing does not live on the
text; it lives on the schedules that point at the item.

When you save, the app synthesizes the text and stores:

- The text, plus the voice, speed, and sentence pause used.
- **Busy retry** and **busy give-up** values, pre-filled from the server
  defaults (`BUSY_RETRY_SECONDS` / `BUSY_GIVE_UP_SECONDS`). Each announcement
  carries its own values, so a bulletin and a station ID can behave
  differently on a busy channel.
- The measured audio length (see below).

The rendered audio is cached as PCM so scheduled transmissions play without
synthesizing again. **Speak preview** streams the synthesized speech to your
browser so you can hear it before saving or scheduling. Changing the
environment's repeater timeout updates the too-long mark on already-saved
items from the stored length, without synthesizing again.

### Text features

- `[pause]` tags (for example `[pause:1]`, `[pause:1s]`) insert silence; the
  pause time counts toward the measured length.
- The sentence pause (`TTS_SENTENCE_PAUSE`, and per-announcement) inserts
  silence between sentences.
- `{{phrase}}` is always spoken as written and skips the pronunciation
  dictionary. `[[ipa]]` is manual inline phoneme input (see below).
- Dictionary substitutions apply while **Use the phoneme dictionary** is on
  (the default, including announcements saved before it existed). The stored
  announcement text is unchanged.

## Spoken length: the repeater timeout minus 2 seconds

An **audio file** (MP3) announcement is measured the same way from the
uploaded file. The limit is the **repeater timeout**
(`REPEATER_TIMEOUT_SECONDS`, default 180) **minus 2 seconds** — 178 seconds
by default. The PTT lead after key-up sits inside that 2-second margin.

- **Over the limit, spoken:** the text is still saved. The editor tells you
  the length, the limit, and to shorten it and save again. The announcement
  is marked **too long**. Shorten it under the limit and save again to clear
  the mark.
- **Over the limit, MP3:** the upload is **rejected** (not saved) with that
  same length message — use a shorter file.

A too-long announcement cannot be chosen for a new or updated schedule. A
schedule that already points at one is kept, but when that slot comes due,
the announcement is not played: the baseline that would have played is used
instead, the next baseline in the rotation that fits if that one is also too
long, or the slot stays silent if none fit. The home screen, schedule list,
schedule editor, slot clock, and upcoming line all name the schedule, the
announcement, its length, the limit, and what will play instead.

The same rule applies to an emergency, and to the Newsline opening, station
ID, closing, and resume parts — a too-long station ID means the bulletin
does not play at all.

## Audio file (MP3) announcements

- Upload via the editor (`POST /api/announcements/audio`; replace with
  `PUT /api/announcements/{id}/audio`, fetch with
  `GET /api/announcements/{id}/audio` — see the
  [API overview](api-overview.md)).
- Maximum upload size is `AUDIO_ANNOUNCEMENT_MAX_BYTES` (default 5 MiB,
  range 64 KiB–20 MiB).
- The file is measured on upload; over-limit files are rejected.

## Pronunciation

Piper sometimes mis-pronounces words, and pronunciation varies among voices.
Piper does not have a way to set up a dictionary of word pronunciations or
specific phonemes, so StationVoice provides workarounds at several levels.

### General workarounds in the text

- If the speech is a bit stilted or has unnatural pauses between words, try
  concatenating words with dashes, e.g. `P-L-tone`.
- For more fluid speech, it sometimes helps to concatenate words with
  commas, e.g. `four,four,two,point,six,five,zero,mega-hertz`.

### Plain-text substitutions

| Word | Substitution |
| --- | --- |
| Delaware | Del-aware |
| Association | Asso-see-ation |

### Inline IPA phonemes

The Piper TTS engine supports IPA phoneme notation inline in the input text,
with the phoneme string surrounded by `[[` and `]]`. For instance:

```text
"This is the [[dˈɛlɐwˌɛ‍ɹ]] Valley Radio [[ɐsˌo‍ʊsɪˈe‍ɪʃən]]"
```

For a starting point, generate phonemes with espeak-ng:

```bash
espeak-ng -v en-us --ipa=3 Delaware
```

produces `dˈɛlɐwˌɛ‍ɹ`. This frequently produces better pronunciation for
words mispronounced by Piper's default internal phoneme conversion
("Delaware" and "Association" are both cases where this is true).

### The phoneme dictionary (Pronunciations screen)

The Pronunciations screen stores a word or phrase spelling with either an
IPA string or alternate plain text, not both. While a spoken announcement
has **Use the phoneme dictionary** on, those spellings are replaced when the
announcement is synthesized: IPA is spoken as phonemes, alternate text as
ordinary words. The stored announcement text is unchanged. The dictionary
file is `phonemes.json` in the data directory; it is not part of the git
repository.

Matching rules:

- Matching ignores case and only replaces **whole words and phrases**. A
  longer phrase wins over a shorter one. "our" does not change "hour".
  "Delaware's" does not use an entry for "Delaware"; add "Delaware's" if
  that possessive needs an entry.
- A spelling wrapped in asterisks, such as `*440-frequency*`, is a
  **shortcut**. The punctuation rule does not apply inside the asterisks, so
  a hyphenated keyword can stand for a different pronunciation. The
  announcement must contain the same asterisks; `440-frequency` does not use
  that entry. `*440*` does not replace the start of `*440-frequency*` when
  the longer shortcut is saved.
- `{{phrase}}` in the announcement is spoken as written and skips the
  dictionary. The braces are not spoken. `[[ipa]]` is still manual phoneme
  input and is not rewritten. `[pause:1s]` is still a pause.

**IPA for this spelling** on the Pronunciations screen uses the espeak-ng
library shipped with Piper, with the same phoneme mode as
`espeak-ng -v en-us --ipa=3` (including tie marks and stress). A word looked
up by itself is stressed the way that command stresses it, so `our` alone is
`ˈaʊɚ` rather than the unstressed form used inside a sentence. Pick a voice
on that screen and speak the spelling, the IPA, or the alternate text before
saving the row. Tie marks are easy to miss because the joiner has no width.
The saved IPA keeps them; they are removed from `[[ ]]` blocks when text is
prepared for Piper, which has no phoneme id for U+200D and would only skip
the character.

## Voices

Voice choices and the server defaults for new announcements (speed,
sentence pause, busy retry / give-up) come from the server (`GET /api/voices`)
— defaults are not hard-coded in the UI.

- Any voice usable by Piper TTS works. Browse samples at
  [piper-samples](https://rhasspy.github.io/piper-samples/) and models on
  Hugging Face [`rhasspy/piper-voices`](https://huggingface.co/rhasspy/piper-voices).
- **Featured voices** are listed in the UI with friendly names and are
  preloaded at startup; they are re-downloaded automatically if their model
  file is missing. **Extra voices on disk** (copied into `voices/piper/`)
  appear in the UI but are not re-downloaded.
- On a low-RAM host, set `TTS_PIPER_QUALITIES=medium` so only medium models
  are listed and preloaded.

Full voice management (featured voice catalog, custom download URLs,
aliases) is in [Configuration reference](configuration.md#piper-voices).
Voices can be downloaded from the CLI: `python -m app download`, or
`python -m app download amy ryan` for specific voices. `python -m app --help`
lists the speak and voice-listing commands.

## Deleting announcements

A spoken announcement that a Newsline item still uses (as opening, station
ID, closing, or resume) **cannot be deleted** — remove it from the Newsline
item first.
