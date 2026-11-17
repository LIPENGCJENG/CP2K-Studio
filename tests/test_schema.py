import hashlib
import json
import pytest
from core.schema import BUNDLED_XML, CP2KSchema


def test_xml_provenance_and_interface():
    metadata = json.loads((BUNDLED_XML.parent/'provenance.json').read_text())
    assert hashlib.sha256(BUNDLED_XML.read_bytes()).hexdigest() == metadata['sha256']
    schema = CP2KSchema()
    assert '2026.1' in schema.version
    assert 'RUN_TYPE' in schema.keywords('GLOBAL')
    assert schema.section('FORCE_EVAL/DFT/SCF/OT') is not None
    assert schema.keyword('FORCE_EVAL/DFT/SCF', 'MAX_SCF')['name'] == 'MAX_SCF'
    with pytest.raises(KeyError):
        schema.section('GLOBAL/NO_SUCH_SECTION')


def test_wrong_version_is_never_silently_used(tmp_path):
    xml = tmp_path/'2025.xml'
    xml.write_text('<CP2K_INPUT><CP2K_VERSION>CP2K version 2025.2</CP2K_VERSION></CP2K_INPUT>')
    with pytest.raises(ValueError, match='2026.1'):
        CP2KSchema(xml)
