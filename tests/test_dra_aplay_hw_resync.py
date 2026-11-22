"""Before transmit, re-resolve Pulse-paired indices to ALSA hw for aplay (#88)."""

from __future__ import annotations

from app.cm119 import Cm119HidAdapter
import app.dra_playback as dra_playback
from app.dra_portaudio import DraOutputDevice, PortAudioDeviceInfo
from app.dra_radio import DraRadio

import pytest


def test_prepare_for_transmit_rescans_when_aplay_lacks_hw(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    radio = DraRadio(
        hid_adapters=[
            Cm119HidAdapter(b"hid-1", "dra-hid-1"),
            Cm119HidAdapter(b"hid-2", "dra-hid-2"),
        ],
        audio_indices=[6, 7],
        usb_channel="left",
        cos_line="vol_dn",
        cos_active_high=False,
    )
    sync_calls: list[bool] = []

    def tracking_on() -> bool:
        return True

    def aplay() -> str:
        return "aplay"

    def no_hw() -> bool:
        return False

    def look_valid() -> bool:
        return True

    def note_present() -> bool:
        return True

    def sync_audio(*, after_usb_event: bool = False) -> bool:
        sync_calls.append(after_usb_event)
        if after_usb_event:
            radio.__dict__["_audio_indices"] = [0, 1]
        return after_usb_event

    def unmute(_radio: object) -> None:
        return None

    def recovery(_radio: object) -> bool:
        return False

    def query_devices(index: int) -> dict[str, str]:
        return {"name": f"USB PnP Sound Device: Audio (hw:{index},0)"}

    monkeypatch.setattr(radio, "runtime_usb_hid_tracking_enabled", tracking_on)
    monkeypatch.setattr("app.config.dra_linux_playback_backend", aplay)
    monkeypatch.setattr(radio, "audio_indices_have_alsa_hw", no_hw)
    monkeypatch.setattr(radio, "audio_output_indices_look_valid", look_valid)
    monkeypatch.setattr(radio, "note_usb_hid_presence", note_present)
    monkeypatch.setattr(radio, "sync_audio_output_indices_if_changed", sync_audio)
    monkeypatch.setattr("app.dra_alsa_mixer.apply_cm119_replug_recovery", recovery)
    monkeypatch.setattr("app.dra_alsa_mixer.sync_cm119_speaker_unmute", unmute)
    monkeypatch.setattr("sounddevice.query_devices", query_devices)

    radio.prepare_for_transmit()

    assert True in sync_calls
    assert radio.audio_device_indices == [0, 1]


def test_audio_indices_have_alsa_hw(monkeypatch: pytest.MonkeyPatch) -> None:
    radio = DraRadio(
        hid_adapters=[Cm119HidAdapter(b"hid-1", "dra-hid-1")],
        audio_indices=[0],
        usb_channel="left",
        cos_line="vol_dn",
        cos_active_high=False,
    )

    def device_name(index: int) -> str:
        if index == 0:
            return "USB PnP Sound Device: Audio (hw:0,0)"
        return (
            "alsa_output.usb-C-Media_Electronics_Inc."
            "_USB_PnP_Sound_Device-00.analog-stereo"
        )

    monkeypatch.setattr("app.dra_portaudio.portaudio_output_device_name", device_name)
    assert radio.audio_indices_have_alsa_hw() is True
    radio.__dict__["_audio_indices"] = [6]
    assert radio.audio_indices_have_alsa_hw() is False


def test_alsa_card_for_aplay_falls_back_pulse_ordinal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pulse sinks have no (hw:N,0); map by DRA ordinal to /proc CM119 cards (#88)."""

    def no_hw(_index: int) -> None:
        return None

    def fake_signature(*, limit: int) -> tuple[int, ...]:
        return tuple([0, 1][:limit])

    def fake_dra() -> list[DraOutputDevice]:
        pulse_a: PortAudioDeviceInfo = {
            "name": (
                "alsa_output.usb-C-Media_Electronics_Inc."
                "_USB_PnP_Sound_Device-00.analog-stereo"
            ),
            "max_output_channels": 2,
        }
        pulse_b: PortAudioDeviceInfo = {
            "name": (
                "alsa_output.usb-C-Media_Electronics_Inc."
                "_USB_PnP_Sound_Device-00.analog-stereo.2"
            ),
            "max_output_channels": 2,
        }
        return [(6, pulse_a), (7, pulse_b)]

    monkeypatch.setattr("app.dra_alsa_unmute.alsa_card_from_portaudio_device", no_hw)
    monkeypatch.setattr("app.dra_alsa_unmute.cm119_alsa_card_signature", fake_signature)
    monkeypatch.setattr("app.dra_portaudio.list_dra_output_devices", fake_dra)
    assert dra_playback._alsa_card_for_aplay(6) == 0  # pyright: ignore[reportPrivateUsage]
    assert dra_playback._alsa_card_for_aplay(7) == 1  # pyright: ignore[reportPrivateUsage]


def test_alsa_playback_devices_use_proc_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DRA_ALSA_PLAYBACK_DEVICE", raising=False)

    def card_for(_index: int) -> int:
        return 1

    monkeypatch.setattr("app.dra_playback._alsa_card_for_aplay", card_for)
    devices = dra_playback._alsa_playback_devices_for_portaudio_index(  # pyright: ignore[reportPrivateUsage]
        6
    )
    assert devices == ["hw:1,0", "plughw:1,0"]
