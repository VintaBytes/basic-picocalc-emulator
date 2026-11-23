"""Persistencia del idioma de la interfaz."""

import json

import pytest

from basic_cde.app.settings import MountSettings


def test_default_language(tmp_path):
    settings = MountSettings(tmp_path / "settings.json")
    assert settings.load_language() == "es"


@pytest.mark.parametrize("language", ["es", "en"])
def test_save_and_reload_language(tmp_path, language):
    path = tmp_path / "settings.json"
    settings = MountSettings(path)

    settings.save_language(language)

    assert MountSettings(path).load_language() == language
    assert json.loads(path.read_text())["version"] == 1


def test_language_survives_other_settings(tmp_path):
    path = tmp_path / "settings.json"
    settings = MountSettings(path)

    settings.save_language("en")

    operations = [
        lambda: settings.save_volume(45),
        lambda: settings.save({"A": "/tmp/flash"}),
        lambda: settings.save_libraries(["/tmp/library.bas"]),
        lambda: settings.save_last_program("/tmp/test.bas"),
        lambda: settings.save_function_keys({}),
    ]

    for operation in operations:
        operation()
        assert MountSettings(path).load_language() == "en"

    reloaded = MountSettings(path)

    assert reloaded.load_volume() == 45
    assert reloaded.load() == {"A": "/tmp/flash"}
    assert reloaded.load_libraries() == ["/tmp/library.bas"]
    assert reloaded.load_last_program() == "/tmp/test.bas"


@pytest.mark.parametrize("invalid", ["fr", "", None, 123])
def test_unknown_language_falls_back_to_spanish(tmp_path, invalid):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({
        "version": 1,
        "mounts": {},
        "language": invalid,
    }))

    assert MountSettings(path).load_language() == "es"


def test_reject_invalid_language_without_modifying_file(tmp_path):
    path = tmp_path / "settings.json"
    settings = MountSettings(path)
    settings.save_language("en")

    before = path.read_bytes()

    with pytest.raises(ValueError):
        settings.save_language("fr")

    assert path.read_bytes() == before


def test_existing_configuration_without_language(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({
        "version": 1,
        "mounts": {"B": "/tmp/sdcard"},
        "volume": 60,
    }))

    settings = MountSettings(path)

    assert settings.load_language() == "es"
    assert settings.load_volume() == 60
    assert settings.load() == {"B": "/tmp/sdcard"}

    settings.save_language("en")

    assert settings.load_language() == "en"
    assert settings.load_volume() == 60
    assert settings.load() == {"B": "/tmp/sdcard"}
