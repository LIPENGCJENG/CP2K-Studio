import json
from pathlib import Path
import pytest
from core.models import Project
from core.project_io import save_project, load_project, export_bundle
from core.generator import GenerationError
from core.structure import load_structure


def test_complete_and_draft_roundtrip(water, tmp_path):
    for i, p in enumerate([water, Project()]):
        path = tmp_path/f'{i}.json'
        save_project(p, path)
        assert load_project(path) == p
    assert not list(tmp_path.glob('.*.json.*'))


def test_bad_project_does_not_load(tmp_path):
    path = tmp_path/'bad.json'
    path.write_text('{broken')
    with pytest.raises(ValueError):
        load_project(path)
    path.write_text(json.dumps({'format_version': 99}))
    with pytest.raises(ValueError):
        load_project(path)


def test_export_validates_and_preserves_coordinates(water, tmp_path, validator):
    dest = tmp_path/'job'
    path = export_bundle(water, dest)
    text = path.read_text()
    assert 'COORD_FILE_NAME structure.xyz' in text
    assert 'COORD_FILE_NAME "structure.xyz"' not in text
    assert validator.parse(text, dest).ok
    st = load_structure(dest/'structure.xyz')
    assert st.positions == water.structure.positions
    reopened = load_project(dest/'project.cp2kstudio.json')
    assert reopened.structure == water.structure
    assert reopened.kinds == water.kinds
    from core.validator import validate_project
    assert validate_project(reopened).ok
    assert all(Path(p).is_file() for p in reopened.dft.basis_files)
    with pytest.raises(FileExistsError):
        export_bundle(water, dest)
    assert path.read_text() == text


def test_export_copies_colliding_resource_names(water, tmp_path, validator):
    sources = []
    from core.database_manager import BUNDLED_DATA
    for name, original in [('a', BUNDLED_DATA/'BASIS_MOLOPT'), ('b', BUNDLED_DATA/'GTH_POTENTIALS')]:
        folder = tmp_path/name
        folder.mkdir()
        source = folder/'same library'
        # Official provenance uses file bytes; text IO would turn LF into
        # CRLF on Windows and invalidate an otherwise identical database.
        source.write_bytes(original.read_bytes())
        assert source.read_bytes() == original.read_bytes()
        sources.append(str(source))
    water.dft.basis_files = [sources[0], sources[0]]
    water.dft.potential_file = sources[1]
    dest = tmp_path/'export'
    path = export_bundle(water, dest)
    assert len(list((dest/'data').iterdir())) == 2
    assert validator.parse(path.read_text(), dest).ok
    reopened = load_project(dest/'project.cp2kstudio.json')
    assert all(Path(p).is_file() for p in reopened.dft.basis_files)
    assert len(reopened.dft.basis_files)==1  # references are de-duplicated
    assert Path(reopened.dft.basis_files[0]).read_bytes() == (BUNDLED_DATA/'BASIS_MOLOPT').read_bytes()
    assert Path(reopened.dft.potential_file).read_bytes() == (BUNDLED_DATA/'GTH_POTENTIALS').read_bytes()
    from core.validator import validate_project
    from core.file_references import check_generated_dependencies
    assert validate_project(reopened).ok
    assert not check_generated_dependencies(path.read_text(encoding='utf-8'), dest, require_relative=True)


def test_invalid_export_leaves_no_files(tmp_path):
    dest = tmp_path/'invalid'
    with pytest.raises(GenerationError):
        export_bundle(Project(), dest)
    assert not dest.exists() and not list(tmp_path.iterdir())


def test_bad_xml_cleans_staging(water, tmp_path):
    xml = tmp_path/'bad.xml'
    xml.write_text('<CP2K_INPUT><CP2K_VERSION>CP2K version 2025.2</CP2K_VERSION></CP2K_INPUT>')
    water.xml_spec = str(xml)
    dest = tmp_path/'invalid'
    with pytest.raises(ValueError, match='2026.1'):
        export_bundle(water, dest)
    assert not dest.exists() and not list(tmp_path.glob('.cp2k-studio-*'))


def test_relative_resource_resolution_uses_project_folder(water, tmp_path):
    (tmp_path/'local_basis').write_text('basis')
    data = water.model_dump()
    data['dft']['basis_files'] = ['./local_basis']
    path = tmp_path/'project.json'
    path.write_text(json.dumps(data))
    assert load_project(path).dft.basis_files == [str(tmp_path/'local_basis')]
