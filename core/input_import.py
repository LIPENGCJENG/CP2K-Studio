"""Conservative import of supported INP fields; unknown physics is reported."""
from i18n.messages import i18n_msg, i18n_str, i18n_join
from pathlib import Path
from fractions import Fraction
from ase.cell import Cell
from ase.units import Bohr
from core.models import Project,Structure,Kind,GlobalConfig
from core.validator import InputValidator
from core.kind_validator import project_catalog,resource_paths


def import_input(path):
    path=Path(path).resolve()
    result=InputValidator().parse(path.read_text(encoding='utf-8'),path.parent)
    if not result.ok:
        raise ValueError(i18n_join('\n', result.errors))
    tree=result.tree
    fes=tree.get('+force_eval',[])
    if len(fes)!=1:
        raise ValueError(i18n_msg('Only one FORCE_EVAL using Quickstep GPW can currently be imported', code='studio.b743214d0067c28b'))
    fe=fes[0];d=fe.get('+dft',{});sub=fe.get('+subsys',{});g=tree.get('+global',{})
    if fe.get('method','quickstep').lower() not in {'qs','quickstep'} or d.get('+qs',{}).get('method','gpw').lower()!='gpw':
        raise ValueError(i18n_msg('INP import currently supports Quickstep / GPW only', code='studio.bef3e8778bc52812'))
    run=g.get('run_type','').upper()
    if run == 'MOLECULAR_DYNAMICS':run='MD'
    if run not in {'ENERGY','GEO_OPT','VIBRATIONAL_ANALYSIS','CELL_OPT','MD'}:
        raise ValueError(i18n_msg('Explicitly specify a supported RUN_TYPE: ENERGY, GEO_OPT, VIBRATIONAL_ANALYSIS, CELL_OPT or MD', code='md.import_run_error'))
    project=Project(global_settings=GlobalConfig(project_name=g.get('project_name',path.stem),
        run_type=run,print_level=g.get('print_level','LOW').upper()))
    warnings=[i18n_msg('Only parameters supported by the current model are imported. Arbitrary INP cannot be round-tripped completely; retain the original input.', code='studio.21fd24a8b764f0db')]
    def local(value):
        p=Path(value).expanduser()
        return i18n_str((path.parent/p).resolve()) if not p.is_absolute() and (path.parent/p).is_file() else i18n_str(p)
    project.dft.basis_files=[local(p) for p in d.get('basis_set_file_name',[])]
    project.dft.potential_file=local(d.get('potential_file_name',''))
    project.dft.charge=d.get('charge')
    project.dft.multiplicity=d.get('multiplicity')
    project.dft.uks=d.get('uks',d.get('lsd',False))
    project.dft.surface_dipole_correction=d.get('surface_dipole_correction',False)
    project.dft.surf_dip_dir=d.get('surf_dip_dir','Z').upper()
    if project.dft.charge is None or project.dft.multiplicity is None:
        warnings.append(i18n_msg('The input does not explicitly specify CHARGE or MULTIPLICITY. These remain unset for user confirmation.', code='studio.a9f78c688b691c30'))
    for key in ['cutoff','rel_cutoff','ngrids']:
        if key in d.get('+mgrid',{}):setattr(project.dft,key,d['+mgrid'][key])
    if 'eps_default' in d.get('+qs',{}):project.dft.eps_default=d['+qs']['eps_default']
    functional=d.get('+xc',{}).get('+xc_functional',{}).get('_')
    if functional and functional.upper() in {'PBE','BLYP','PADE'}:project.dft.xc_functional=functional.upper()
    else:warnings.append(i18n_msg('The functional is unspecified or unsupported and remains unselected.', code='studio.494adeb521acb130'))
    s=d.get('+scf',{});sc=project.dft.scf
    for key in ['eps_scf','max_scf']:
        if key in s:setattr(sc,key,s[key])
    if s.get('scf_guess','').upper() in {'ATOMIC','CORE','RANDOM'}:sc.guess=s['scf_guess'].upper()
    if '+diagonalization' in s:
        sc.method='DIAGONALIZATION';sc.added_mos=s.get('added_mos',0)
        if 'algorithm' in s['+diagonalization']:sc.diagonalization=s['+diagonalization']['algorithm'].upper()
        mixing=s.get('+mixing',{})
        if 'method' in mixing:sc.mixing_method=mixing['method'].upper()
        if 'alpha' in mixing:sc.mixing_alpha=mixing['alpha']
        if '+smear' in s:
            if s['+smear'].get('method','fermi_dirac').lower()!='fermi_dirac':raise ValueError(i18n_msg('This smearing method is not supported', code='studio.d994994e975db661'))
            sc.smearing=True;sc.electronic_temperature=s['+smear'].get('electronic_temperature',300)
    else:
        for key in ['minimizer','preconditioner']:
            if key in s.get('+ot',{}):setattr(sc,key,s['+ot'][key].upper())
        if 'energy_gap' in s.get('+ot',{}):sc.energy_gap=s['+ot']['energy_gap']
    if '+outer_scf' in s:
        sc.outer_scf=True;sc.outer_max_scf=s['+outer_scf'].get('max_scf',10)
    kinds={}
    for k in sub.get('+kind',[]):
        label=k.get('_','');element=k.get('element',label)
        basis=k.get('basis_set',[])
        if len(basis)>1:raise ValueError(i18n_msg('The importer currently supports one orbital basis per KIND', code='studio.94b9f46f7476389a'))
        kinds[label]=Kind(element=element,basis_set=basis[0] if basis else '',potential=k.get('potential',''))
    cell=sub.get('+cell',{})
    if all(axis in cell for axis in ['a','b','c']):matrix=[cell[a] for a in ['a','b','c']]
    elif 'abc' in cell:matrix=Cell.fromcellpar([*cell['abc'],*cell.get('alpha_beta_gamma',(90,90,90))]).array.tolist()
    else:matrix=((0,0,0),)*3;warnings.append(i18n_msg('No supported cell parameters were provided; set the cell manually.', code='studio.00c6cdd3d906d9e1'))
    coord=sub.get('+coord',{})
    rows=coord.get('*',[])
    if not rows:
        topology=sub.get('+topology',{})
        filename=topology.get('coord_file_name')
        if not filename or topology.get('coord_file_format','').lower()!='xyz':raise ValueError(i18n_msg('Only embedded COORD or a single-frame XYZ reference is supported', code='studio.20ea6c884343dc6f'))
        raw=Path(local(filename)).read_text().splitlines();count=int(raw[0]);rows=raw[2:2+count]
        if len(rows)!=count or any(line.strip() for line in raw[2+count:]):raise ValueError(i18n_msg('A complete, single-frame XYZ is required', code='studio.6b97eaae2619df54'))
    labels=[];symbols=[];positions=[]
    for row in rows:
        tokens=row.split()
        if len(tokens)<4:raise ValueError(i18n_msg('Invalid coordinate row', code='studio.e827569b6e802ec3'))
        label=tokens[0];labels.append(label)
        if label not in kinds:raise ValueError(i18n_msg('Missing ELEMENT definition for KIND {p0}', code='studio.6c4e221b785ed522', p0=label))
        symbols.append(kinds[label].element)
        positions.append([float(Fraction(x)) for x in tokens[1:4]])
    import numpy as np
    if coord.get('scaled',False):positions=(np.array(positions)@np.array(matrix)).tolist()
    elif coord.get('unit','ANGSTROM').upper() in {'BOHR','AU'}:positions=(np.array(positions)*Bohr).tolist()
    elif coord.get('unit','ANGSTROM').upper() not in {'ANGSTROM','ANGSTROMS'}:raise ValueError(i18n_msg('This coordinate unit is not supported', code='studio.8b4f1dc706a99bcc'))
    project.structure=Structure(symbols=symbols,positions=positions,cell=matrix,
        periodic=cell.get('periodic','XYZ').upper(),kind_labels=labels if labels!=symbols else [],source=i18n_str(path))
    project.kinds=kinds
    poisson=d.get('+poisson',{})
    if 'poisson_solver' in poisson:project.dft.poisson_solver=poisson['poisson_solver'].upper()
    elif project.structure.periodic=='XYZ':
        warnings.append(i18n_msg('The Poisson solver is unspecified and remains unselected.', code='studio.182441fa5188c085'))
    if 'periodic' in poisson and poisson['periodic'].upper()!=project.structure.periodic:
        raise ValueError(i18n_msg('CELL and POISSON periodicity differ; lossless import is not possible', code='studio.523e3e64258fca21'))
    geo=tree.get('+motion',{}).get('+geo_opt',{})
    for key in ['optimizer','max_iter','max_force','rms_force','max_dr','rms_dr']:
        if key in geo:setattr(project.motion,key,geo[key].upper() if key=='optimizer' else geo[key])
    if run == 'MD':
        from core.models import MDConfig
        node = tree.get('+motion', {}).get('+md', {})
        thermo = node.get('+thermostat', {})
        if node.get('ensemble', 'nve').upper() == 'NVT' and (thermo.get('type', 'nose').upper() != 'CSVR' or thermo.get('region', 'global') != 'global'):
            raise ValueError(i18n_msg('MD: only GLOBAL CSVR thermostats can be imported for NVT.', code='md.import_thermostat'))
        if node.get('ensemble', 'nve').upper() == 'NVE' and thermo:
            raise ValueError(i18n_msg('MD: NVE input must not contain a thermostat.', code='md.import_nve'))
        prints = tree.get('+motion', {}).get('+print', {})
        if isinstance(prints, list):
            if len(prints) != 1:
                raise ValueError(i18n_msg('MD: only one MOTION/PRINT configuration can be imported.', code='md.import_prints'))
            prints = prints[0]
        trajectory, restart = prints.get('+trajectory', {}), prints.get('+restart', {})
        def print_enabled(section):
            return str(section.get('_', True)).lower() not in {'false', 'off', '0'}
        fmt = trajectory.get('format', 'xyz').upper()
        values = dict(ensemble=node.get('ensemble', 'nve').upper(), steps=node.get('steps', 3),
            timestep=node.get('timestep', .5), temperature=node.get('temperature', 300),
            initialization_method=node.get('initialization_method', 'default').upper(),
            timecon=thermo.get('+csvr', {}).get('timecon', 1000),
            write_trajectory=print_enabled(trajectory), trajectory_format='XYZ' if fmt == 'XMOL' else fmt,
            trajectory_interval=trajectory.get('+each', {}).get('md', 1),
            write_restart=print_enabled(restart), restart_interval=restart.get('+each', {}).get('md', 1),
            backup_copies=restart.get('backup_copies', 1))
        external = tree.get('+ext_restart', {})
        if external:
            default = external.get('restart_default', True)
            required = ['restart_pos', 'restart_vel', 'restart_cell', 'restart_counters']
            if values['ensemble'] == 'NVT':required.append('restart_thermostat')
            if any(not external.get(key, default) for key in required):
                raise ValueError(i18n_msg('MD: partial EXT_RESTART settings cannot be represented as full MD continuation. Keep the original input or configure a complete restart explicitly.', code='md.import_partial_restart'))
            values.update(continue_from_restart=True, restart_file=local(external.get('restart_file_name', '')))
        elif '+velocity' in sub:
            # A real MD restart is a dynamics state, not just another geometry.
            values.update(continue_from_restart=True, restart_file=str(path))
        project.md = MDConfig.model_validate(values)
        for name, section, keys in [
            ('MOTION/MD', node, {'ensemble','steps','timestep','temperature','initialization_method','+thermostat','+print','step_start_val','time_start_val','econs_start_val'}),
            ('MOTION/MD/THERMOSTAT', thermo, {'type','region','+csvr'}),
            ('MOTION/MD/THERMOSTAT/CSVR', thermo.get('+csvr',{}), {'timecon','+thermostat_energy','+rng_init'}),
            ('MOTION/PRINT', prints, {'+trajectory','+restart'}),
            ('MOTION/PRINT/TRAJECTORY', trajectory, {'_','format','+each'}),
            ('MOTION/PRINT/RESTART', restart, {'_','backup_copies','+each'})]:
            extra = set(section) - keys
            if extra:warnings.append(i18n_msg('Settings not imported from {p0}: ', code='studio.a9bc38f5f9aae344', p0=name)+i18n_join(', ',sorted(extra)))
    if run == 'CELL_OPT':
        from core.models import CellOptimizationConfig
        node = tree.get('+motion', {}).get('+cell_opt', {})
        if '+geo_opt' in tree.get('+motion', {}):
            raise ValueError(i18n_msg('CELL_OPT import supports joint cell/coordinate optimization only, without a separate GEO_OPT section.', code='cellopt.import_type_error'))
        values = {key: node[key] for key in CellOptimizationConfig.model_fields if key in node}
        values['stress_tensor'] = fe.get('stress_tensor', 'none')
        values['initial_symmetry'] = cell.get('symmetry', 'none')
        for key in ['optimizer', 'constraint', 'stress_tensor', 'initial_symmetry']:
            if key in values:
                values[key] = values[key].upper()
        # XML expresses scalar external pressure as a one-item list. Full pressure
        # tensors and alternative stress algorithms are deliberately rejected.
        if isinstance(values.get('external_pressure'), list):
            if len(values['external_pressure']) != 1:
                raise ValueError(i18n_msg('CELL_OPT import supports one scalar EXTERNAL_PRESSURE, not a pressure tensor.', code='cellopt.import_pressure_error'))
            values['external_pressure'] = values['external_pressure'][0]
        elif 'external_pressure' not in values:
            # CP2K 2026.1 defaults to 100 bar, unlike Studio's explicit zero.
            values['external_pressure'] = 100.0
        project.cell_opt = CellOptimizationConfig.model_validate(values)
        extras = set(node) - (set(CellOptimizationConfig.model_fields) - {'stress_tensor', 'initial_symmetry'})
        if extras:
            warnings.append(i18n_msg('Settings not imported from {p0}: ', code='studio.a9bc38f5f9aae344', p0='MOTION/CELL_OPT') + i18n_join(', ', sorted(extras)))
    if run == 'VIBRATIONAL_ANALYSIS':
        node = tree.get('+vibrational_analysis', {})
        if '+mode_selective' in node:
            raise ValueError(i18n_msg('VIBRATIONAL_ANALYSIS import supports only the full Hessian; MODE_SELECTIVE cannot be represented by this workflow.', code='vib.import_selective'))
        for key in ['dx', 'nproc_rep', 'proc_dist_type', 'fully_periodic', 'thermochemistry', 'tc_temperature', 'tc_pressure']:
            if key in node:
                value = node[key].upper() if key == 'proc_dist_type' else node[key]
                setattr(project.vibrational, key, value)
        def enabled(section):
            return section is not None and str(section.get('_', True)).lower() not in {'false', 'off', '0'}
        prints = node.get('+print', {})
        project.vibrational.molden_vib = enabled(prints.get('+molden_vib'))
        project.vibrational.hessian = enabled(prints.get('+hessian'))
        linres = fe.get('+properties', {}).get('+linres', {})
        polar = linres.get('+polar')
        moments = d.get('+print', {}).get('+moments')
        project.vibrational.linres_preconditioner = linres.get('preconditioner', 'NONE').upper()
        project.vibrational.linres_energy_gap = linres.get('energy_gap', 0.2)
        if node.get('intensities', False):
            ir = enabled(moments)
            raman = enabled(polar) and polar.get('do_raman', True)
            if not ir and not raman:
                raise ValueError(i18n_msg('VIBRATIONAL_ANALYSIS import requires at least one enabled IR or Raman property workflow when INTENSITIES is enabled. Required properties cannot be omitted.', code='vib.import_intensities'))
            project.vibrational.ir_enabled = bool(ir)
            project.vibrational.raman_enabled = bool(raman)
            # Never drop explicit k points or silently translate a local operator
            # into a Berry-phase one (or vice versa) during a round trip.
            from core.vibrational import validate_spectroscopy_input
            issues = validate_spectroscopy_input(project, tree)
            if issues:
                raise ValueError(i18n_join('\n', issues))
        project.vibrational.linres_eps = linres.get('eps', 1e-6)
        project.vibrational.linres_max_iter = linres.get('max_iter', 50)
    constraint = tree.get('+motion', {}).get('+constraint', {})
    fixed = {}
    for section in constraint.get('+fixed_atoms', []):
        if set(section) - {'components_to_fix', 'list'} or not section.get('list'):
            warnings.append(i18n_msg('FIXED_ATOMS with extra selectors or RESTRAINT was not imported. Retain and check the original input.', code='studio.d15e886442533dd1'))
            continue
        components = section.get('components_to_fix', 'xyz').upper()
        for numbers in section['list']:
            numbers = (numbers,) if isinstance(numbers, int) else numbers
            for number in numbers:
                if type(number) is not int or not 1 <= number <= len(project.structure.atom_ids):
                    raise ValueError(i18n_msg('FIXED_ATOMS/LIST contains invalid atom indices', code='studio.9402b3cf7919388c'))
                atom_id = project.structure.atom_ids[number - 1]
                fixed[atom_id] = i18n_join('', (axis for axis in 'XYZ' if axis in fixed.get(atom_id, '') + components))
    project.structure.fixed_atoms = [dict(atom_id=atom_id, components=components) for atom_id, components in fixed.items()]
    supported={'+global':{'project_name','run_type','print_level'},'FORCE_EVAL':{'method','+dft','+subsys'},
        'DFT':{'basis_set_file_name','potential_file_name','charge','multiplicity','uks','lsd','surface_dipole_correction','surf_dip_dir','+qs','+mgrid','+poisson','+scf','+xc'},
        'SCF':{'eps_scf','max_scf','scf_guess','added_mos','+ot','+diagonalization','+mixing','+smear','+outer_scf'},
        'SUBSYS':{'+cell','+coord','+kind','+topology'}}
    if run == 'VIBRATIONAL_ANALYSIS':
        supported['FORCE_EVAL'].add('+properties')
        supported['DFT'].add('+print')
    if run == 'CELL_OPT':
        supported['FORCE_EVAL'].add('stress_tensor')
    for name,node in [('+global',g),('FORCE_EVAL',fe),('DFT',d),('SCF',s),('SUBSYS',sub)]:
        extra=set(node)-supported[name]
        if extra:warnings.append(i18n_msg('Settings not imported from {p0}: ', code='studio.a9bc38f5f9aae344', p0=name)+i18n_join(', ', sorted(extra)))
    for name,node,keys in [
        ('DFT/QS',d.get('+qs',{}),{'method','eps_default'}),
        ('DFT/MGRID',d.get('+mgrid',{}),{'cutoff','rel_cutoff','ngrids'}),
        ('DFT/XC',d.get('+xc',{}),{'+xc_functional'}),
        ('SCF/OT',s.get('+ot',{}),{'minimizer','preconditioner','energy_gap','_'}),
        ('SCF/OUTER_SCF',s.get('+outer_scf',{}),{'max_scf','eps_scf','_'}),
        ('MOTION',tree.get('+motion',{}),{'+geo_opt', '+constraint'} | ({'+cell_opt'} if run == 'CELL_OPT' else set()) | ({'+md', '+print'} if run == 'MD' else set())),
        ('MOTION/CONSTRAINT',constraint,{'+fixed_atoms'}),
        ('MOTION/GEO_OPT',geo,{'optimizer','max_iter','max_force','rms_force','max_dr','rms_dr'})]:
        extra=set(node)-keys
        if extra:warnings.append(i18n_msg('Settings not imported from {p0}: ', code='studio.a9bc38f5f9aae344', p0=name)+i18n_join(', ', sorted(extra)))
    if s.get('+outer_scf',{}).get('eps_scf',sc.eps_scf)!=sc.eps_scf:
        warnings.append(i18n_msg('Original OUTER_SCF EPS_SCF differs from the inner threshold. This interface uses one threshold; please review.', code='studio.2ec98c2c8463f644'))
    if run == 'VIBRATIONAL_ANALYSIS':
        vibration = tree.get('+vibrational_analysis', {})
        for name, node, keys in [
            ('VIBRATIONAL_ANALYSIS', vibration, {'dx', 'nproc_rep', 'proc_dist_type', 'fully_periodic', 'intensities', 'thermochemistry', 'tc_temperature', 'tc_pressure', '+print'}),
            ('VIBRATIONAL_ANALYSIS/PRINT', vibration.get('+print', {}), {'+molden_vib', '+hessian'}),
            ('VIBRATIONAL_ANALYSIS/PRINT/MOLDEN_VIB', vibration.get('+print', {}).get('+molden_vib', {}), {'_'}),
            ('VIBRATIONAL_ANALYSIS/PRINT/HESSIAN', vibration.get('+print', {}).get('+hessian', {}), {'_'}),
            ('DFT/PRINT', d.get('+print', {}), {'+moments'}),
            ('DFT/PRINT/MOMENTS', moments or {}, {'_', 'periodic', 'reference', 'max_moment'}),
            ('PROPERTIES', fe.get('+properties', {}), {'+linres'}),
            ('PROPERTIES/LINRES', linres, {'eps', 'max_iter', 'preconditioner', 'energy_gap', '+polar'}),
            ('PROPERTIES/LINRES/POLAR', polar or {}, {'_', 'do_raman', 'periodic_dipole_operator', '+print'}),
            ('PROPERTIES/LINRES/POLAR/PRINT', (polar or {}).get('+print', {}), {'+polar_matrix'})]:
            extra = set(node) - keys
            if extra:
                warnings.append(i18n_msg('Settings not imported from {p0}: ', code='studio.a9bc38f5f9aae344', p0=name) + i18n_join(', ', sorted(extra)))
    catalog=project_catalog(project);basis_paths,potential_paths=resource_paths(project,catalog)
    for label,kind in project.kinds.items():
        for category,name,paths,ref in [('basis',kind.basis_set,basis_paths,'basis_ref'),('potential',kind.potential,potential_paths,'potential_ref')]:
            matches=[e for p in paths for e in catalog.find(category,kind.element,name,p)]
            if matches:
                from core.models import DatabaseReference
                setattr(kind,ref,DatabaseReference(**matches[0].reference()))
            else:warnings.append(i18n_msg('{p1} for KIND {p0} could not be matched to the actual database. The original name was retained for review.', code='studio.0cd7ba7abccf55cf', p0=label, p1=name))
    return project,warnings
