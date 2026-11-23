"""Regresiones de mensajes bilingües de BASIC PicoCalc Linux."""

import string

import pytest

from basic_cde.gui.i18n import TRANSLATIONS, translate


STATUS_KEYS = (
    "status.mounts_unavailable",
    "status.sd_auto_fixed",
    "status.last_program_missing",
    "status.flash_mounted",
    "status.sd_adjusted",
    "status.sd_mounted",
    "status.library_attached",
    "status.remember_failed",
    "status.running",
    "status.volume_saved",
    "status.volume_applied",
    "status.volume_failed",
    "status.volume_no_pactl",
    "status.volume_applying",
    "status.active_drive",
    "status.current_directory",
    "status.saved",
    "status.loaded",
    "status.editor_applied",
)

DIALOG_KEYS = (
    "dialog.preferences",
    "dialog.load_failed",
    "error.save_mounts",
    "error.save_library",
)


def placeholders(template):
    return {
        name
        for _, name, _, _ in string.Formatter().parse(template)
        if name is not None
    }


@pytest.mark.parametrize("key", STATUS_KEYS + DIALOG_KEYS)
def test_translation_exists_in_both_languages(key):
    for language in ("es", "en"):
        assert translate(key, language).strip()


@pytest.mark.parametrize("key", STATUS_KEYS + DIALOG_KEYS)
def test_placeholders_match(key):
    assert placeholders(TRANSLATIONS["es"][key]) == (
        placeholders(TRANSLATIONS["en"][key])
    )


@pytest.mark.parametrize("language", ["es", "en"])
def test_volume_messages(language):
    for key in (
        "status.volume_saved",
        "status.volume_applied",
        "status.volume_failed",
        "status.volume_no_pactl",
        "status.volume_applying",
    ):
        result = translate(key, language, volume=65)
        assert "65%" in result


@pytest.mark.parametrize("language", ["es", "en"])
def test_file_messages(language):
    for key in ("status.saved", "status.loaded"):
        result = translate(
            key, language, path="A:/TEST.BAS"
        )
        assert "A:/TEST.BAS" in result


def test_language_changes_status_text():
    assert translate(
        "status.volume_saved", "es", volume=70
    ) != translate(
        "status.volume_saved", "en", volume=70
    )


def test_basic_keywords_are_preserved():
    for language in ("es", "en"):
        message = translate("status.running", language)
        assert "RUN" in message
        assert "INKEY$" in message
        assert "Ctrl+C" in message
        assert "STOP" in message
