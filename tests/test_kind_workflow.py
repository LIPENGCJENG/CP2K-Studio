from pathlib import Path
import json
import pytest
from core.database_manager import scan_databases
from core.models import Kind,Structure,DatabaseReference
from core.kind_validator import project_catalog,validate_kinds
from core.project_io import save_project,load_project,export_bundle
from core.generator import generate_input,GenerationError
from core.potential_database import parse_potential_file
from core.validator import validate_project
from ui.main_window import MainWindow
from ui.kind_panel import SearchCombo


def choose(combo,name):
    index=next(i for i in range(1,combo.count()) if combo.itemData(i) and name in combo.itemData(i).names)
    combo.setCurrentIndex(index);combo.activated.emit(index)


def test_ui_selection_immediately_syncs_model_files_and_preview(app,water):
    window=MainWindow();window.load_into_ui(water)
    row=next(i for i in range(window.kind_panel.table.rowCount()) if window.kind_panel.table.item(i,0).text()=='O')
    combo=window.kind_panel.table.cellWidget(row,1)
    assert isinstance(combo,SearchCombo)
    assert all(combo.itemData(i).element=='O' for i in range(1,combo.count()) if combo.itemData(i))
    choose(combo,'TZV2P-MOLOPT-GTH')
    assert window.project.kinds['O'].basis_set=='TZV2P-MOLOPT-GTH'
    assert window.project.kinds['O'].basis_ref.sha256
    assert Path(window.project.kinds['O'].basis_ref.path).is_file()
    assert 'BASIS_SET TZV2P-MOLOPT-GTH' in window.preview.toPlainText()
    before=window.project.kinds['O'].model_dump()
    window.kind_panel.q_filter.setText('999')
    window.refresh()
    assert window.project.kinds['O'].model_dump()==before
    window.kind_panel.q_filter.clear()
    window.kind_panel.quality.setCurrentText('TZV2P')
    assert all(e.quality=='TZV2P' for e in window.kind_panel.candidates('basis','O'))
    window.dirty=False;window.close()


def test_recommendation_is_explicit_and_persistent(app,water,tmp_path):
    from core.kind_recommender import recommend
    window=MainWindow();window.load_into_ui(water)
    before=window.project.model_copy(deep=True)
    options=recommend(window.kind_panel.catalog,'O','PBE')
    assert window.project==before
    window.kind_panel.apply_recommendation('O',options[0])
    assert window.project.kinds['O'].recommendation.used
    path=tmp_path/'project.json';save_project(window.project,path)
    reopened=load_project(path)
    assert reopened==window.project
    window.load_into_ui(reopened)
    assert window.project.kinds['O'].basis_ref.sha256==reopened.kinds['O'].basis_ref.sha256
    assert window.project.kinds['O'].recommendation.used
    window.dirty=False;window.close()


def test_saved_missing_record_retained_and_export_blocked(app,water,tmp_path):
    window=MainWindow();window.load_into_ui(water)
    original=window.project.kinds['O'].basis_set
    data=window.project.model_dump()
    data['kinds']['O']['basis_ref']['path']=str(tmp_path/'removed_database')
    path=tmp_path/'missing.json';path.write_text(json.dumps(data))
    p=load_project(path)
    window.load_into_ui(p)
    assert window.project.kinds['O'].basis_set==original
    assert str(tmp_path/'removed_database')==window.project.kinds['O'].basis_ref.path
    assert not window.export_action.isEnabled()
    with pytest.raises(GenerationError):export_bundle(window.project,tmp_path/'bad_export')
    window.dirty=False;window.close()


def test_multi_basis_and_multi_potential_bundle(water,tmp_path,validator):
    catalog=scan_databases()
    def bind(label,basis_name,source,potential_source):
        kind=water.kinds[label]
        kind.element=label
        basis=next(e for e in catalog.find('basis',label,basis_name) if Path(e.path).name==source)
        potential=next(e for e in catalog.find('potential',label,kind.potential) if Path(e.path).name==potential_source)
        kind.basis_set=basis.name;kind.basis_ref=DatabaseReference(**basis.reference())
        kind.potential_ref=DatabaseReference(**potential.reference())
    bind('O','DZVP-GTH','GTH_BASIS_SETS','POTENTIAL')
    bind('H','DZVP-MOLOPT-GTH','BASIS_MOLOPT','GTH_POTENTIALS')
    water.dft.basis_files=list(dict.fromkeys(k.basis_ref.path for k in water.kinds.values()))
    water.dft.potential_files=list(dict.fromkeys(k.potential_ref.path for k in water.kinds.values()))
    water.dft.potential_file=water.dft.potential_files[0]
    original_scf=water.dft.scf.model_dump();original_motion=water.motion.model_dump()
    dest=tmp_path/'multi';path=export_bundle(water,dest)
    tree=validator.parse(path.read_text(),dest).tree
    dft=tree['+force_eval'][0]['+dft']
    assert len(dft['basis_set_file_name'])==2
    assert dft['potential_file_name']=='studio_potentials.dat'
    potentials=parse_potential_file(dest/'studio_potentials.dat')
    assert len(potentials)==2
    assert {(e.element,e.name) for e in potentials}=={('O','GTH-PBE-q6'),('H','GTH-PBE-q1')}
    assert all(Path(dest/p).is_file() for p in dft['basis_set_file_name'])
    reopened=load_project(dest/'project.cp2kstudio.json')
    assert validate_project(reopened).ok
    assert reopened.dft.scf.model_dump()==original_scf and reopened.motion.model_dump()==original_motion
    assert all(Path(k.potential_ref.path).is_file() for k in reopened.kinds.values())
    # Portable copied source libraries remain usable on a second export.
    second=export_bundle(reopened,tmp_path/'second')
    assert validator.parse(second.read_text(),second.parent).ok


def test_two_kind_labels_same_element_and_atom_labels(app,water,tmp_path,validator):
    window=MainWindow();window.load_into_ui(water)
    p=window.project.model_copy(deep=True)
    p.structure=Structure(symbols=['O','O'],positions=[(0,0,0),(1,0,0)],cell=((6,0,0),(0,6,0),(0,0,6)),periodic='XYZ',kind_labels=['O1','O2'])
    p.kinds={label:p.kinds['O'].model_copy(deep=True) for label in ['O1','O2']}
    window.load_into_ui(p)
    assert window.kind_panel.table.rowCount()==2
    text=generate_input(window.project)
    assert '&KIND O1' in text and '&KIND O2' in text
    assert text.count('ELEMENT O')==2
    assert 'O1 0 0 0' in text
    table=window.structure_panel.coords
    assert [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())
            if not table.isColumnHidden(i)]==['元素','x','y','z','固定']
    assert table.isColumnHidden(4)
    original_kinds=window.project.model_dump()['kinds']
    table.item(1,1).setText('1.2345678912345')
    window.refresh()
    assert window.project.structure.kind_labels==['O1','O2']
    assert window.project.structure.positions==[(0.,0.,0.),(1.2345678912345,0.,0.)]
    assert window.project.model_dump()['kinds']==original_kinds
    assert '&KIND O1' in window.preview.toPlainText() and '&KIND O2' in window.preview.toPlainText()
    saved=tmp_path/'edited.cp2kstudio.json'
    save_project(window.project,saved)
    window.load_into_ui(load_project(saved))
    assert window.project.structure.kind_labels==['O1','O2']
    assert window.structure_panel.coords.item(1,4).text()=='O2'
    assert window.structure_panel.coords.isColumnHidden(4)
    path=export_bundle(window.project,tmp_path/'labels')
    assert 'O2 1.2345678912345 0 0' in (path.parent/'structure.xyz').read_text()
    assert validator.parse(path.read_text(),path.parent).ok
    window.dirty=False;window.close()


def test_changing_atomic_kind_label_syncs_rows(app,water):
    window=MainWindow();window.load_into_ui(water)
    window.structure_panel.coords.item(0,4).setText('O1')
    window.refresh()
    assert window.project.structure.labels[0]=='O1'
    assert window.project.kinds['O1'].element=='O'
    assert not window.project.kinds['O1'].basis_set
    assert not window.export_action.isEnabled()
    assert set(window.kind_panel._elements)=={'O1','H'}
    window.dirty=False;window.close()


def test_input_import_recovers_kind_metadata_and_labels(water,tmp_path,validator):
    from core.input_import import import_input
    p=water.model_copy(deep=True)
    p.structure.kind_labels=['O1','H1','H1']
    oxygen=p.kinds['O'].model_copy(deep=True);oxygen.element='O'
    hydrogen=p.kinds['H'].model_copy(deep=True);hydrogen.element='H'
    p.kinds={'O1':oxygen,'H1':hydrogen}
    path=tmp_path/'input.inp';path.write_text(generate_input(p))
    imported,warnings=import_input(path)
    assert warnings and imported.structure.labels==p.structure.labels
    assert imported.kinds['O1'].element=='O'
    assert imported.kinds['O1'].basis_ref.sha256
    assert imported.dft.charge==0 and imported.dft.multiplicity==1
    assert validate_project(imported).ok
    assert validator.parse(generate_input(imported)).ok
