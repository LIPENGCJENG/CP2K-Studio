"""Integration tests use audited, unmodified official CP2K v2026.1 files."""
from pathlib import Path
import hashlib
import json
import os
import pytest
from core.basis_database import parse_basis_file
from core.potential_database import parse_potential_file
from core.database_format import DatabaseFormatError
from core.database_manager import BUNDLED_DATA,scan_databases
from core.models import DatabaseSettings,CustomDatabase,DatabaseReference,Kind,Structure
from core.kind_validator import validate_kinds,project_catalog
from core.kind_recommender import recommend


@pytest.fixture(scope='module')
def catalog():
    return scan_databases()


def bind(project,label,basis,potential):
    project.kinds[label]=Kind(element=basis.element,basis_set=basis.name,potential=potential.name,
        basis_ref=DatabaseReference(**basis.reference()),potential_ref=DatabaseReference(**potential.reference()))


def test_official_file_fingerprints_and_all_databases_parse():
    manifest=json.loads((BUNDLED_DATA/'manifest.json').read_text())
    assert manifest['cp2k_version']=='2026.1' and len(manifest['commit'])==40
    for name,metadata in manifest['files'].items():
        path=BUNDLED_DATA/name
        assert hashlib.sha256(path.read_bytes()).hexdigest()==metadata['sha256']
        result=(parse_basis_file if metadata['kind']=='basis' else parse_potential_file)(path)
        assert len(result)>100


def test_basis_main_names_aliases_shells_and_q(catalog):
    entries=parse_basis_file(BUNDLED_DATA/'BASIS_MOLOPT')
    entry=next(e for e in entries if e.element=='O' and e.name=='DZVP-MOLOPT-GTH')
    assert 'DZVP-MOLOPT-GTH-q6' in entry.aliases
    assert entry.q==6 and entry.quality=='DZVP' and 'MOLOPT' in entry.tags
    assert catalog.find('basis','O','DZVP-MOLOPT-GTH-q6',str(BUNDLED_DATA/'BASIS_MOLOPT'))[0].key==entry.key
    # Identical installed copies can take precedence over the bundled path;
    # candidate deduplication is by record contents, not filesystem identity.
    assert sum((e.element,e.name,e.content_sha256)==(entry.element,entry.name,entry.content_sha256)
               for e in catalog.query('basis','O'))==1


def test_potential_names_aliases_matrices_nlcc_and_all_electron():
    entries=parse_potential_file(BUNDLED_DATA/'POTENTIAL')
    entry=next(e for e in entries if e.element=='O' and e.name=='GTH-PBE-q6')
    assert entry.q==6 and entry.xc=='PBE' and 'GTH-PBE' in entry.aliases
    assert next(e for e in entries if e.element=='O' and e.name=='ALLELECTRON').q==8
    uzh=parse_potential_file(BUNDLED_DATA/'POTENTIAL_UZH')
    assert any('NA' in issue for issue in uzh.issues)
    assert not any(e.element=='Bi' and e.name=='GTH-PBE0-q15' for e in uzh)
    assert any('Bi GTH-PBE0-q15' in issue for issue in uzh.issues)


@pytest.mark.parametrize('element',['Ba','Ti','O'])
def test_element_filters_and_recommendations(catalog,element):
    for category in ['basis','potential']:
        candidates=catalog.query(category,element)
        assert candidates and all(e.element==element for e in candidates)
    for xc in ['PBE','BLYP']:
        options=recommend(catalog,element,xc)
        assert options
        assert all(o.potential.xc==xc and o.basis.q==o.potential.q and o.basis.element==element for o in options)
        assert all(o.basis.family!='UZH' and o.potential.family!='UZH' for o in options)


def test_search_filters_and_no_invented_recommendations(catalog):
    results=catalog.query('basis','O',search='q6',quality='DZVP',source='BASIS_MOLOPT',q=6)
    assert results and all(e.quality=='DZVP' and e.q==6 and Path(e.path).name=='BASIS_MOLOPT' for e in results)
    assert not recommend(catalog,'Og','PBE')
    assert not recommend(catalog,'O',None)
    assert not recommend(catalog,'O','UNSUPPORTED_XC')
    assert not catalog.query('basis','O',q=999)


def test_q_xc_element_and_method_checks(water,catalog):
    basis=catalog.find('basis','O','DZVP-MOLOPT-GTH')[0]
    potential=catalog.find('potential','O','GTH-BLYP-q6')[0]
    bind(water,'O',basis,potential)
    result=validate_kinds(water,catalog)
    assert not result.errors
    assert any(i.severity=='Warning' and 'XC' in i.message for i in result.issues)
    infos = [issue.message for issue in result.issues if issue.severity == 'Info' and issue.label == 'O']
    assert not infos  # Normal q matches and basis-quality labels are not issues.
    ti_basis=catalog.query('basis','Ti',source='BASIS_MOLOPT')[0]
    ti_potential=catalog.find('potential','Ti','GTH-PADE-q4')[0]
    water.structure=Structure(symbols=['Ti'],positions=[(0,0,0)],cell=((6,0,0),(0,6,0),(0,0,6)),periodic='XYZ')
    water.kinds={};bind(water,'Ti',ti_basis,ti_potential)
    assert any('q12' in e and 'q4' in e for e in validate_kinds(water,catalog).errors)
    water.structure.symbols=['O']
    assert validate_kinds(water,catalog).errors


def test_unknown_q_does_not_claim_compatibility(water,catalog,tmp_path):
    basis=catalog.find('basis','O','DZVP-MOLOPT-GTH')[0]
    # This is an actual official data block with q-bearing aliases removed to
    # exercise missing metadata; coefficients and primary name stay unchanged.
    path=tmp_path/'no_q';path.write_text(basis.render((basis.name,)))
    water.databases.custom_files=[CustomDatabase(path=str(path),category='basis',version='2026.1')]
    water.dft.basis_files=[str(path)]
    checked=project_catalog(water)
    actual=checked.find('basis','O',basis.name,str(path))[0]
    potential=catalog.find('potential','O','GTH-PBE-q6')[0]
    bind(water,'O',actual,potential)
    result=validate_kinds(water,project_catalog(water))
    assert any(i.severity=='Warning' and '无法自动确认' in i.message for i in result.issues)


def test_uzh_not_mixed_and_all_electron_not_gpw(water,catalog):
    basis=catalog.query('basis','O',source='BASIS_MOLOPT_UZH')[0]
    potential=catalog.find('potential','O','GTH-PBE-q6')[0]
    bind(water,'O',basis,potential)
    assert any('UZH' in e for e in validate_kinds(water,catalog).errors)
    basis=catalog.find('basis','O','DZVP-MOLOPT-GTH')[0]
    potential=catalog.find('potential','O','ALLELECTRON')[0]
    bind(water,'O',basis,potential)
    assert any('全电子' in e for e in validate_kinds(water,catalog).errors)


def test_bad_empty_and_truncated_files_rejected(tmp_path):
    path=tmp_path/'bad'
    for text in ['', 'O A_NAME\n1\n2 0 1 5 1 1\n1.0 0.5\n']:
        path.write_text(text)
        with pytest.raises(DatabaseFormatError):parse_basis_file(path)
    path.write_text('O GTH-PBE-q6\n2 4\n0.2 2 1\n0\n')
    with pytest.raises(DatabaseFormatError):parse_potential_file(path)
    with pytest.raises(FileNotFoundError):parse_basis_file(tmp_path/'missing')


def test_explicit_version_and_official_manifest_mismatch(tmp_path,catalog):
    entry=catalog.find('basis','O','DZVP-MOLOPT-GTH')[0]
    path=tmp_path/'BASIS_MOLOPT';path.write_text(entry.render())
    settings=DatabaseSettings(data_directory=str(tmp_path))
    c=scan_databases(settings)
    assert not c.find('basis','O',entry.name,str(path))
    settings.declared_version='2026.1'
    assert scan_databases(settings).find('basis','O',entry.name,str(path))
    settings.declared_version='2025.2'
    assert not scan_databases(settings).find('basis','O',entry.name,str(path))


def test_duplicate_name_conflict_and_fingerprint_change(water,catalog,tmp_path):
    entry=catalog.find('basis','O','DZVP-MOLOPT-GTH')[0]
    path=tmp_path/'custom_basis';path.write_text(entry.render())
    settings=DatabaseSettings(custom_files=[CustomDatabase(path=str(path),category='basis',version='2026.1')])
    water.databases=settings;water.dft.basis_files=[str(path)]
    actual=project_catalog(water).find('basis','O',entry.name,str(path))[0]
    potential=catalog.find('potential','O','GTH-PBE-q6')[0]
    bind(water,'O',actual,potential)
    stamp=path.stat()
    content=path.read_text().replace('0.1040796000','0.2040796000')
    if content==path.read_text():
        row=actual.payload[2].split();row[1]='0.1234567890'
        content=actual.render().replace(actual.payload[2],' '.join(row))
    path.write_text(content)
    os.utime(path,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
    changed=project_catalog(water)
    assert any('DZVP-MOLOPT-GTH' in m for m in changed.conflicts)
    assert any('指纹已变化' in e for e in validate_kinds(water,changed).errors)


def test_startup_never_fetches(monkeypatch):
    import urllib.request
    monkeypatch.setattr(urllib.request,'urlopen',lambda *a,**k:pytest.fail('startup attempted network'))
    assert scan_databases().entries


def test_explicit_official_download_is_verified_and_transactional(tmp_path,monkeypatch):
    from io import BytesIO
    import urllib.request
    from core.database_manager import download_official_data
    calls=[]
    def fetch(url,**kwargs):
        calls.append(url)
        return BytesIO((BUNDLED_DATA/url.rsplit('/',1)[-1]).read_bytes())
    monkeypatch.setattr(urllib.request,'urlopen',fetch)
    target=tmp_path/'cache'
    download_official_data(target)
    manifest=json.loads((target/'manifest.json').read_text())
    assert len(calls)==len(manifest['files'])
    assert all(manifest['commit'] in url and 'raw.githubusercontent.com/cp2k/cp2k/' in url for url in calls)
    before=(target/'BASIS_MOLOPT').read_bytes()
    monkeypatch.setattr(urllib.request,'urlopen',lambda *a,**k:BytesIO(b'corrupt'))
    with pytest.raises(ValueError,match='指纹'):download_official_data(target)
    assert (target/'BASIS_MOLOPT').read_bytes()==before
    assert not list(tmp_path.glob('.cp2k-download-*'))


def test_reference_element_mismatch_and_priority_shadowing(water,catalog,tmp_path):
    wrong=catalog.query('basis','Ti',source='BASIS_MOLOPT')[0]
    potential=catalog.find('potential','O','GTH-PBE-q6')[0]
    water.kinds['O'].basis_ref=DatabaseReference(**wrong.reference())
    water.kinds['O'].basis_set=wrong.name
    assert any('不存在' in e or '条目内容' in e for e in validate_kinds(water,catalog).errors)
    original=catalog.find('basis','O','DZVP-MOLOPT-GTH')[0]
    row=original.payload[2].split();row[1]='0.1234567890'
    path=tmp_path/'modified';path.write_text(original.render().replace(original.payload[2],' '.join(row)))
    water.databases.custom_files=[CustomDatabase(path=str(path),category='basis',version='2026.1')]
    water.dft.basis_files=[str(BUNDLED_DATA/'BASIS_MOLOPT'),str(path)]
    updated=project_catalog(water);actual=updated.find('basis','O',original.name,str(path))[0]
    bind(water,'O',actual,potential)
    assert any('覆盖' in e for e in validate_kinds(water,project_catalog(water)).errors)


def test_renamed_official_uzh_file_keeps_protocol_identity(tmp_path):
    path=tmp_path/'renamed_library'
    path.write_bytes((BUNDLED_DATA/'BASIS_MOLOPT_UZH').read_bytes())
    settings=DatabaseSettings(custom_files=[CustomDatabase(path=str(path),category='basis',version='2026.1')])
    catalog=scan_databases(settings)
    actual=catalog.find('basis','O','DZVP-MOLOPT-PBE-GTH-q6',str(path))
    assert actual and actual[0].family=='UZH'
    assert not any(r.basis.path==str(path.resolve()) for r in recommend(catalog,'O','PBE'))
