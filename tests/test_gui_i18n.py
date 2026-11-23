"""Contrato de traducciones de la interfaz, independiente de Qt."""

import string

import pytest

from basic_cde.gui.i18n import (
    DEFAULT_LANGUAGE,
    LANGUAGES,
    TRANSLATIONS,
    translate,
)


def fields(template):
    formatter = string.Formatter()
    return {
        name for _, name, _, _ in formatter.parse(template)
        if name is not None
    }


def test_supported_languages():
    assert LANGUAGES == ("es", "en")
    assert DEFAULT_LANGUAGE == "es"


def test_all_translations_have_matching_keys():
    assert set(TRANSLATIONS["es"]) == set(TRANSLATIONS["en"])


def test_all_translations_are_nonempty():
    for catalog in TRANSLATIONS.values():
        assert all(isinstance(value, str) and value.strip()
                   for value in catalog.values())


def test_placeholders_match_between_languages():
    spanish = TRANSLATIONS["es"]
    english = TRANSLATIONS["en"]

    for key in spanish:
        assert fields(spanish[key]) == fields(english[key]), key


def test_menu_translation():
    assert translate("menu.file", "es") == "Archivo"
    assert translate("menu.file", "en") == "File"
    assert translate("menu.view", "en") == "View"


def test_interpolation():
    assert translate("editor.position", "es", line=3, column=8) == (
        "Línea 3 · Columna 8"
    )
    assert translate("editor.position", "en", line=3, column=8) == (
        "Line 3 · Column 8"
    )


def test_unknown_language_uses_spanish():
    assert translate("menu.file", "fr") == "Archivo"


def test_unknown_key_raises_error():
    with pytest.raises(KeyError):
        translate("nonexistent.key", "es")


def test_basic_commands_are_not_translation_keys():
    for command in ("PRINT", "RUN", "LIST", "READY", "GOTO"):
        assert command not in TRANSLATIONS["es"]
        assert command not in TRANSLATIONS["en"]
