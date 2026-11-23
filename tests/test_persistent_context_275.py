"""PCC: hardware reset marker and SAVE/LOAD CONTEXT semantics."""
import json
from pathlib import Path
import pytest
from basic_cde.core.machine import BasicMachine
from basic_cde.core.expressions import BasicError
from basic_cde.app.session import BasicSession
from basic_cde.devices.drives import VirtualDrives


def run_session(session, maximum=2000):
    collected = []
    for _ in range(maximum):
        result = session.step()
        collected.append(result.output)
        if result.state == 'finished':
            return ''.join(collected)
        assert result.state == 'running', result.state
    raise AssertionError('No termino')


def test_save_persistent_survives_new_session_and_reset(tmp_path):
    state = tmp_path / 'state' / 'persistent.json'
    first = BasicSession('SAVE PERSISTENT 1\nPRINT MM.PERSISTENT\nEND', persistent_path=state)
    assert run_session(first) == '1\n'
    assert json.loads(state.read_text())['value'] == 1
    second = BasicSession('PRINT MM.PERSISTENT\nSAVE PERSISTENT 0\nPRINT MM.INFO(PERSISTENT)\nEND',
                          persistent_path=state)
    assert run_session(second) == '1\n0\n'
    third = BasicSession('PRINT MM.PERSISTENT\nEND',persistent_path=state)
    assert run_session(third) == '0\n'


def test_persistent_rejects_fractional_and_invalid_integer(tmp_path):
    state=tmp_path/'persistent.json'
    for raw in ['1.25','"hello"','1E30']:
        session=BasicSession(f'SAVE PERSISTENT {raw}',persistent_path=state)
        with pytest.raises(BasicError,match='SAVE PERSISTENT'):
            session.step()
        assert not state.exists()


def test_context_save_load_arrays_and_scalar_on_chain(tmp_path):
    a=tmp_path/'flash';a.mkdir()
    (a/'next.bas').write_text('''PRINT MM.PERSISTENT
LOAD CONTEXT
PRINT NUM,WORDS$(1),INDEX%(0)
SAVE PERSISTENT 0
END''')
    src='''DIM WORDS$(2)
DIM INTEGER INDEX%(2)
WORDS$(1)="PCC"
INDEX%(0)=37
NUM=5.5
SAVE PERSISTENT 1
SAVE CONTEXT
RUN "A:/next.bas"'''
    session=BasicSession(src,drives=VirtualDrives(a=a),persistent_path=tmp_path/'persistent.json')
    assert run_session(session)=='1\n5.5 PCC 37\n'
    assert not (a/'.basic-cde-context.json').exists()  # LOAD CONTEXT consume; KEEP preserva
    assert session.machine.variables.globals['MM.PERSISTENT'] == 0


def test_context_clear_and_restore_preserve_mm_internal(tmp_path):
    root=tmp_path/'flash';root.mkdir()
    s=BasicSession('''A=12
SAVE CONTEXT CLEAR
PRINT A
LOAD CONTEXT
PRINT A
END''',drives=VirtualDrives(a=root),persistent_path=tmp_path/'p.json')
    assert run_session(s) == '0\n12\n'
    assert s.machine.variables.globals['MM.ERRNO'] == 0


def test_missing_context_and_no_drive_are_errors(tmp_path):
    for cmd in ('LOAD CONTEXT','SAVE CONTEXT'):
        s=BasicSession(cmd, persistent_path=tmp_path/'p.json')
        with pytest.raises(BasicError,match='requiere A:'):
            s.step()
    root=tmp_path/'flash';root.mkdir()
    s=BasicSession('LOAD CONTEXT',drives=VirtualDrives(a=root),persistent_path=tmp_path/'p.json')
    with pytest.raises(BasicError, match='no hay contexto'):
        s.step()


def test_corrupt_context_does_not_change_globals(tmp_path):
    root=tmp_path/'flash';root.mkdir()
    (root/'.basic-cde-context.json').write_text(json.dumps({'version':1,'variables':{
       'A':{'type':'scalar','value':99},'B':{'type':'garbage'}}}))
    s=BasicSession('A=1\nLOAD CONTEXT',drives=VirtualDrives(a=root),persistent_path=tmp_path/'p.json')
    s.step()
    with pytest.raises(BasicError,match='datos invalidos'):
        s.step()
    assert s.machine.variables.globals['A'] == 1


def test_legacy_basic_machine_no_persistent_file():
    machine=BasicMachine('SAVE PERSISTENT 3\nPRINT MM.PERSISTENT\nEND')
    assert machine.run() == '3\n'


def test_pcc_real_quit_saves_retained_marker_and_context(tmp_path):
    from basic_cde.core.machine import KeyboardBuffer
    root_a, root_b=tmp_path/'flash',tmp_path/'sd'
    root_a.mkdir();root_b.mkdir();(root_b/'bas').mkdir()
    source=(Path(__file__).parent.parent/'examples'/'pcc-273-ajustado.bas').read_text()
    keyboard=KeyboardBuffer()
    session=BasicSession(source,keyboard=keyboard,drives=VirtualDrives(a=root_a,b=root_b),
                         persistent_path=tmp_path/'persist.json')
    for _ in range(2200):
        assert session.step().state=='running'
    keyboard.push('Q')
    for _ in range(2000):
        result=session.step()
        if result.state=='finished':break
        assert result.state=='running'
    else: raise AssertionError('PCC no termino tras Q')
    assert json.loads((tmp_path/'persist.json').read_text())['value']==1
    saved=json.loads((root_a/'.basic-cde-context.json').read_text())
    assert 'CURDRIVE$' not in saved['variables'] or saved['variables']['CURDRIVE$']['type']=='array'
    assert 'FILE$' in saved['variables']
