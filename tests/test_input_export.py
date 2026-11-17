from pathlib import Path
import pytest
from core.models import Project, DatabaseReference
from core.input_export import export_input
from core.generator import generate_input, GenerationError
from core.database_manager import scan_databases
from core.potential_database import parse_potential_file


def test_standalone_input_uses_generator_and_inline_coords(water, tmp_path, validator):
    expected = generate_input(water)
    result = export_input(water, tmp_path / 'single.inp')
    assert result.path.read_text() == expected
    assert '&COORD' in expected and 'COORD_FILE_NAME' not in expected
    assert validator.parse(result.path.read_text(), tmp_path).ok
    assert all(Path(p).is_file() for p in result.dependencies)
    assert result.generated_files == []
    with pytest.raises(FileExistsError):
        export_input(water, result.path)


def test_invalid_config_or_xml_never_writes_input(water, tmp_path):
    with pytest.raises(GenerationError):
        export_input(Project(), tmp_path / 'invalid.inp')
    xml = tmp_path / 'old.xml'
    xml.write_text('<CP2K_INPUT><CP2K_VERSION>CP2K version 2025.2</CP2K_VERSION></CP2K_INPUT>')
    water.xml_spec = str(xml)
    with pytest.raises(ValueError):
        export_input(water, tmp_path / 'wrong_schema.inp')
    assert not list(tmp_path.glob('*.inp'))


def test_standalone_merged_potential_dependency_and_conflict(water, tmp_path):
    catalog = scan_databases()
    for label, filename in [('O', 'POTENTIAL'), ('H', 'GTH_POTENTIALS')]:
        entry = next(e for e in catalog.find('potential', label, water.kinds[label].potential) if Path(e.path).name == filename)
        water.kinds[label].potential_ref = DatabaseReference(**entry.reference())
    water.dft.potential_files = list(dict.fromkeys(k.potential_ref.path for k in water.kinds.values()))
    path = tmp_path / 'multi.inp'
    result = export_input(water, path)
    assert path.read_text() == generate_input(water)
    merged = tmp_path / 'studio_potentials.dat'
    assert merged in result.generated_files
    assert len(parse_potential_file(merged)) == 2
    assert str(merged) in result.dependencies
    merged.write_text('existing unrelated data')
    old = path.read_text()
    with pytest.raises(FileExistsError):
        export_input(water, path, overwrite=True)
    assert merged.read_text() == 'existing unrelated data'
    assert path.read_text() == old
