"""Persistencia de montajes, sin PySide6 y sin acceder al HOME real."""
import json

from basic_cde.app.settings import MountSettings
from basic_cde.devices.drives import VirtualDrives
from basic_cde.core.expressions import BasicError


def test_save_and_reload_both_drives(tmp_path):
    a, b = tmp_path / 'flash', tmp_path / 'sd'
    a.mkdir(); b.mkdir()
    settings = MountSettings(tmp_path / 'config' / 'settings.json')
    drives = VirtualDrives(a=a, b=b)
    settings.save(drives.roots)
    loaded = settings.load()
    restored = VirtualDrives(a=loaded['A'], b=loaded['B'])
    assert restored.roots == drives.roots
    assert json.loads(settings.path.read_text())['version'] == 1


def test_invalid_and_missing_configuration(tmp_path):
    settings = MountSettings(tmp_path / 'settings.json')
    assert settings.load() == {}
    settings.path.write_text('{no json', encoding='utf-8')
    assert settings.load() == {}
    settings.path.write_text('{"version": 500, "mounts": {"A": "/tmp"}}')
    assert settings.load() == {}


def test_only_mount_paths_persist(tmp_path):
    a = tmp_path / 'flash'; a.mkdir()
    settings = MountSettings(tmp_path / 'settings.json')
    settings.save({'A': a, 'B': None})
    assert settings.load() == {'A': str(a)}
    assert 'B' not in json.loads(settings.path.read_text())['mounts']


def test_xdg_config_home(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path))
    assert MountSettings().path == tmp_path / 'basic-cde-linux' / 'settings.json'


def test_permissions(tmp_path):
    settings = MountSettings(tmp_path / 'settings.json')
    settings.save({'A': '/cualquiera'})
    assert settings.path.stat().st_mode & 0o777 == 0o600


def test_unavailable_root_can_be_skipped_without_deleting_preferences(tmp_path):
    settings = MountSettings(tmp_path / 'settings.json')
    settings.save({'A': str(tmp_path / 'unmounted'), 'B': None})
    drives = VirtualDrives()
    for unit, path in settings.load().items():
        try:
            drives.mount(unit, path)
        except (BasicError, OSError):
            pass
    assert drives.roots['A'] is None
    assert settings.load()['A'].endswith('unmounted')
