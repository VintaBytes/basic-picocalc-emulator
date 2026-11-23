"""El comando EDIT solo solicita el editor; no altera el programa."""
from pathlib import Path
import pytest
from basic_cde.app.direct import DirectConsole, DirectCommandError


def test_edit_does_not_change_memory_or_file():
    original = '10 PRINT "ANTES"\n20 END\n'
    console = DirectConsole(original)
    result = console.execute('EDIT')
    assert result.action == 'edit'
    assert result.modified is False
    assert console.source == original
    assert console.execute('LIST').message == original
    assert 'EDIT' in console.execute('HELP').message


def test_edit_rejects_arguments():
    with pytest.raises(DirectCommandError, match='EDIT no admite'):
        DirectConsole().execute('EDIT "programa.bas"')


def test_editor_integration_does_not_forward_key_events():
    base = Path(__file__).resolve().parents[1] / 'src/basic_cde/gui'
    window = (base / 'window.py').read_text()
    editor = (base / 'editor.py').read_text()
    assert 'def edit_source(self):' in window
    assert 'self.direct_ready = False' in window
    assert 'dialog.exec()' in window
    assert 'self.direct.source = updated' in window
    assert 'QApplication.sendEvent' not in window
    assert 'QPlainTextEdit' in editor
    assert 'QSyntaxHighlighter' in editor
