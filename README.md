# StationVoice

<p align="center">
  <a href="https://w2zq.com">
    <img src="static/docs/dvra-logo.png" width="200">  
  </a>
</p>

![Test](https://github.com/rfreedman/StationVoice/actions/workflows/test.yml/badge.svg)

<big>Software for Scheduled Amateur Radio Repeater Text-to-Speech Announcements,
developed at the <a href="https://w2zq.com" style="white-space: nowrap;">Delware Valley Radio Association</a> </big>
<br/><br/>

## About

<b>StationVoice</b> is a multi-port, text-to-speech "announcement machine" for Amateur Radio repeaters.

Repeater hardware-based announcements are typically cumbersome, requiring hard-coded words and phrases from a fixed dictionary to be strung together.

There are several sofware-based announcement software systems that but most either 
require the recording of audio files, or have very basic and robotic-sounding text-to-speech (TTS).

At the DVRA (station callsign W2ZQ), we have two
repeaters - one for VHF, and one for UHF, and they are in different locations.

Our existing system announces on both repeaters at the same time from a single location by transmitting on two radios: one on each frequency. The repeaters receive these transmissions and repeat them the same way that they do for any normal transmission.

We wanted to continue to make the same announcements on both repeaters, at the same time,
but we wanted a system that provided better TTS voices, without needing to generate audio files, and more flexible and accessible 
scheduling than our existing announcement system.

This is the result, and what will be put on the air soon.

- Rich, N2EHL 2026-11-18


## License

[![License: GPL v3](https://img.shields.io)](https://gnu.org)

This project is licensed under the **GNU General Public License v3.0 or later (GPL-3.0-or-later)** — see the [LICENSE](LICENSE) file for details.

### Third-Party Licenses
This project incorporates third-party libraries, including [`piper-tts`](https://github.com) (licensed under `GPL-3.0-or-later`), along with various permissively licensed dependencies (MIT, BSD, Apache 2.0).


## Features
 * **MultiPort** - **StationVoice** runs on a Linux computer, and uses 
 <a href="https://www.masterscommunications.com/products/radio-adapter/dra/dra36m.html">Masters Communications DRA-36M interfaces to control the radios</a>. The DRA-36M
 connects via a standard USB-A port. You can add more radios by attaching more DRA-36Ms 
 (though the software has only been tested with two, you should be able to use more).
 
 * **TTS** - better-sounding text-to-speech by using the Piper TTS library<br/>
   The text-to-speech conversion is done directly - no need to generate an audio file.

 * **Accessibility** - the admin interface is web-based, so that it can be used
   anywhere and on any computer that can reach the server.<br/>
   (We can use the admin interface on our shack's LAN, or from home via a VPN - it is NOT
   exposed to the open internet).

 * **Flexible Scheduling** - instead of requiring announcements to be scheduled at
   specific times, StationVoice divides each 24-hour period into 48 time slots, one for 
   each hour and half-hour. An announcement can then be scheduled for multiple slots
   with a single 'schedule'. 
   <br/>Repeating schedules are modeled after common calendar repeating event 
   schedules, with options like certain times on certain days of the week, or on 
   a particular day of the week on a specific week of the year, for example, 7:00pm
   on the third Wednesday of the month. <br/><br/> 
   See [scheduling](static/docs/scheduling.md) for more info

 * **Amateur Radio Newsline**
   Many repeater controllers have the ability to transmit the Amateur Radio Newsline via EchoLink, or by the operator manually downloading and copying the ARNewsline mp3 file each week. To enable transmitting the Newsline on non-EchoLink repeaters, and without manual intervention, StationVoice can be configured to automatically download the Newsline mp3 file each week.  <br/><br/> To accommodate repeater controllers that cannot be programmed to automatically disable the repeater timeout while the Newsline is being transmitted, StationVoice automatically breaks up the NewsLine into multiple pieces (at story boundaries) that fit within the repeater timeout window, and un-keys the radios between the pieces. 
  
 ## Documentation
 - Installation - coming soon
 - Configuration - coming soon
 - Scheduling - coming soon
 - Advanced Text-to-Speech - coming soon
 - Amateur Radio Newsline - coming soon
