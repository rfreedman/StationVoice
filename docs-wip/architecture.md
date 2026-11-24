# Architecture

StationVoice combines a web-based management application, text-to-speech, announcement and schedule data, and a radio backend.

This document is a high-level orientation. For implementation details, consult the source code and the linked technical references.

## Components

### Web application

The application provides the administrative interface for managing announcements, schedules, configuration, and users. The application is built around Python and FastAPI, with browser-based UI components.

### Announcement library

Announcements are managed as library items. Depending on the item, the content can be synthesized speech, an audio file, or a special item such as Amateur Radio Newsline. Scheduling refers to library items rather than duplicating announcement text in schedule entries.

### Text-to-speech

StationVoice uses Piper for speech synthesis. Speech is generated for playback rather than requiring operators to maintain a collection of recordings for ordinary text announcements.

Pronunciation customization and speech-related options are documented in the UI and API documentation as they evolve.

### Scheduler

The scheduler uses a slot-based daily schedule. Baseline schedules provide announcements for slots not otherwise claimed, while overlays can override baseline behavior for recurring or date-related events.

See [How to schedule](how-to-schedule.md).

### Radio backend

Radio control and audio transmission are separated behind a radio backend interface.

- **stub:** Software backend used for development and testing without radio hardware.
- **dra:** Production interface using Masters Communications DRA-36M hardware.

The backend abstraction provides channel-busy detection and PTT control, along with optional capabilities supported by the implementation.

See [Radio backend protocol](radio-backend.md).

### Newsline processing

StationVoice can retrieve Amateur Radio Newsline audio and prepare it for playback in story-sized pieces, allowing transmission to be interrupted by unkeying between segments where required.

See [Amateur Radio Newsline](arnewsline.md).

## Data and configuration

StationVoice uses environment variables for configuration. Data files are stored under the configured data directory, with paths and defaults described in [Environment reference](env-reference.md).

Review the backup and operational implications of the data directory before deploying the application on a production station.

## Further reading

- [API overview](api-overview.md)
- [Environment reference](env-reference.md)
- [Deployment](deploy.md)
- [Hardware](final-hardware/README.md)
