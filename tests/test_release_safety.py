"""Check that public release automation is non-destructive."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_published_release_is_never_replaced_automatically():
    workflow = (ROOT / ".github/workflows/publish-appimage.yml").read_text(encoding="utf-8")
    assert "if: github.event_name == 'workflow_dispatch'" in workflow
    assert "gh release view" in workflow
    assert "already exists" in workflow
    assert "--clobber" not in workflow


def test_font_import_uses_audited_upstream_revision():
    installer = (ROOT / "scripts/instalar_fuentes.py").read_text(encoding="utf-8")
    assert "8adc11f3ba5e2a0a496363e732995ca1b009f697" in installer
    assert "PicoMite/main/" not in installer
