"""Pruebas de las traducciones de Ayuda y Acerca de."""

import pytest

from basic_cde.gui.i18n import translate


@pytest.mark.parametrize("language", ["es", "en"])
def test_user_guide_is_available(language):
    title = translate("help.guide_title", language)
    body = translate("help.guide_body", language)

    assert title.strip()
    assert len(body) > 500


@pytest.mark.parametrize("language", ["es", "en"])
def test_user_guide_covers_main_features(language):
    body = translate("help.guide_body", language)

    for term in ("BASIC", "Ctrl+Enter", "SAVE", "STOP", "A:", "B:"):
        assert term in body


@pytest.mark.parametrize("language", ["es", "en"])
def test_about_contains_version_and_credits(language):
    body = translate("about.body", language, version="0.3.10.dev0")

    assert "0.3.10.dev0" in body
    assert "Ariel Palazzesi" in body
    assert "ChatGPT (OpenAI)" in body
    assert "320" in body


@pytest.mark.parametrize("language", ["es", "en"])
def test_help_menu_entries_are_translated(language):
    for key in (
        "help.user_guide",
        "help.environment",
        "help.about",
    ):
        assert translate(key, language).strip()


def test_english_and_spanish_help_are_distinct():
    assert translate("help.guide_body", "es") != (
        translate("help.guide_body", "en")
    )
    assert translate("about.body", "es", version="1.0") != (
        translate("about.body", "en", version="1.0")
    )
