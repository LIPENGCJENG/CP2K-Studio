"""Generated Qt extraction markers. Edit Message templates in UI/core sources."""
from PySide6.QtCore import QCoreApplication

def catalog_sources():
    return [
        # ui/simulation_box_dialog.py:25
        QCoreApplication.translate("CP2KStudio", 'Cubic Box', 'box.cubic'),
        # ui/structure_panel.py:388
        QCoreApplication.translate("CP2KStudio", 'Centered simulation box generated. Review vacuum and Poisson convergence.', 'box.done'),
        # core/models.py:47
        QCoreApplication.translate("CP2KStudio", 'All A/B/C box lengths must be finite positive numbers.', 'box.invalid_lengths'),
        # ui/simulation_box_dialog.py:26
        QCoreApplication.translate("CP2KStudio", 'Manual Input', 'box.manual'),
        # ui/simulation_box_dialog.py:41
        QCoreApplication.translate("CP2KStudio", 'Vacuum margin on each side (Å)', 'box.margin'),
        # ui/simulation_box_dialog.py:28
        QCoreApplication.translate("CP2KStudio", 'Generation Method', 'box.method'),
        # core/structure.py:80
        QCoreApplication.translate("CP2KStudio", 'Enter all three A/B/C box lengths.', 'box.missing_lengths'),
        # ui/simulation_box_dialog.py:57
        QCoreApplication.translate("CP2KStudio", 'Generates an orthogonal PERIODIC NONE box and centers the molecule. Review vacuum and Poisson convergence.', 'box.note'),
        # ui/simulation_box_dialog.py:67
        QCoreApplication.translate("CP2KStudio", 'OK', 'box.ok'),
        # ui/simulation_box_dialog.py:24
        QCoreApplication.translate("CP2KStudio", 'Vacuum Padding', 'box.padding'),
        # core/structure.py:85
        QCoreApplication.translate("CP2KStudio", 'The box is too small along {axes}. Increase the corresponding A/B/C lengths; no coordinates were changed.', 'box.too_small'),
        # core/validator.py:75
        QCoreApplication.translate("CP2KStudio", 'WAVELET with PERIODIC NONE requires an orthogonal cubic box (A = B = C). Use Generate Simulation Box → Cubic Box; the current cell has not been changed.', 'box.wavelet_cubic'),
        # ui/cell_opt_panel.py:26
        QCoreApplication.translate("CP2KStudio", 'KEEP_ANGLES', 'cellopt.angles_label'),
        # ui/cell_opt_panel.py:29
        QCoreApplication.translate("CP2KStudio", 'CONSTRAINT', 'cellopt.constraint_label'),
        # ui/cell_opt_panel.py:24
        QCoreApplication.translate("CP2KStudio", 'KEEP_ANGLES preserves cell-vector angles. KEEP_SYMMETRY requires an explicit compatible initial CELL / SYMMETRY; it preserves cell shape symmetry, not the atomic space group. CONSTRAINT fixes the specified cell components through the pressure tensor. Existing FIXED_ATOMS are retained in fractional coordinates, so Cartesian positions may move with the cell.', 'cellopt.constraints_help'),
        # ui/cell_opt_panel.py:24
        QCoreApplication.translate("CP2KStudio", 'Cell Constraints', 'cellopt.constraints_title'),
        # core/cell_optimization.py:62
        QCoreApplication.translate("CP2KStudio", 'CELL_OPT uses analytical stress with the current Gamma-point GPW configuration. Test basis, grid, SCF and Brillouin-zone sampling convergence for cell parameters and stress; static validation does not certify convergence. This workflow is for 3D bulk crystals, not vacuum slabs. PERIODIC XYZ alone does not identify whether a structure is bulk; confirm the physical model before using it.', 'cellopt.convergence_info'),
        # ui/cell_opt_panel.py:17
        QCoreApplication.translate("CP2KStudio", 'Convergence Criteria', 'cellopt.convergence_title'),
        # ui/export_panel.py:28
        QCoreApplication.translate("CP2KStudio", '06 Cell Optimization', 'cellopt.error_page'),
        # core/export_notes_generator.py:23
        QCoreApplication.translate("CP2KStudio", '7. CELL OPTIMIZATION\nCoordinates and cell vectors are optimized together with ANALYTICAL stress. The obsolete CELL_OPT / TYPE keyword is not emitted.\nExternal pressure: {pressure} bar; pressure tolerance: {tolerance} bar.\nOnly 3D PERIODIC XYZ with Quickstep/GPW and POISSON_SOLVER PERIODIC is supported by this release.\nFIXED_ATOMS, when present, constrain fractional coordinates; their Cartesian positions may move with the cell. KEEP_SYMMETRY refers to the explicitly selected initial cell symmetry, not the atomic space group.\ninput.inp and structure.xyz contain the INITIAL structure. Optimized cells, stresses and optimization steps are produced only by an actual CP2K run; inspect output.out and CP2K restart/trajectory files and confirm convergence. No calculation or geometry optimization has been run by Studio.\nTest stress, basis, grid, SCF and Brillouin-zone sampling convergence; the generated GPW input uses Gamma-point sampling.\n', 'cellopt.export_notes'),
        # core/cell_optimization.py:61
        QCoreApplication.translate("CP2KStudio", 'CELL_OPT: FIXED_ATOMS constraints are retained and fix fractional coordinates. Cartesian positions can move as the cell changes; confirm these constraints match the intended optimization.', 'cellopt.fixed_warning'),
        # core/input_import.py:171
        QCoreApplication.translate("CP2KStudio", 'CELL_OPT import supports one scalar EXTERNAL_PRESSURE, not a pressure tensor.', 'cellopt.import_pressure_error'),
        # core/input_import.py:160
        QCoreApplication.translate("CP2KStudio", 'CELL_OPT import supports joint cell/coordinate optimization only, without a separate GEO_OPT section.', 'cellopt.import_type_error'),
        # ui/cell_opt_panel.py:30
        QCoreApplication.translate("CP2KStudio", 'CELL / SYMMETRY', 'cellopt.initial_symmetry_label'),
        # ui/cell_opt_panel.py:14
        QCoreApplication.translate("CP2KStudio", 'MAX_ITER', 'cellopt.iter_label'),
        # core/models.py:252
        QCoreApplication.translate("CP2KStudio", 'CELL_OPT: legacy TYPE must be DIRECT_CELL_OPT. Other optimization schemes cannot be migrated to joint cell/coordinate optimization.', 'cellopt.legacy_type_error'),
        # ui/cell_opt_panel.py:21
        QCoreApplication.translate("CP2KStudio", 'MAX_DR', 'cellopt.max_dr_label'),
        # ui/cell_opt_panel.py:19
        QCoreApplication.translate("CP2KStudio", 'MAX_FORCE', 'cellopt.max_force_label'),
        # core/presets.py:185
        QCoreApplication.translate("CP2KStudio", 'Cell Optimization', 'cellopt.name'),
        # ui/main_window.py:338
        QCoreApplication.translate("CP2KStudio", '06  Cell Optimization', 'cellopt.nav'),
        # ui/cell_opt_panel.py:13
        QCoreApplication.translate("CP2KStudio", 'OPTIMIZER', 'cellopt.optimizer_label'),
        # core/cell_optimization.py:55
        QCoreApplication.translate("CP2KStudio", 'CELL_OPT: CP2K requires A along +X and B in the XY plane, with positive diagonal components. Reorient the cell and all atomic coordinates together before importing; no components have been truncated or rotated.', 'cellopt.orientation_error'),
        # ui/cell_opt_panel.py:9
        QCoreApplication.translate("CP2KStudio", '06 · Cell Optimization', 'cellopt.page_title'),
        # core/cell_optimization.py:46
        QCoreApplication.translate("CP2KStudio", 'CELL_OPT: only PERIODIC XYZ is supported in this release. Use GEO_OPT for nonperiodic systems; 1D/2D cell optimization is not implemented. Periodicity was not changed.', 'cellopt.periodicity_error'),
        # ui/cell_opt_panel.py:15
        QCoreApplication.translate("CP2KStudio", 'EXTERNAL_PRESSURE', 'cellopt.pressure_label'),
        # core/validator.py:180
        QCoreApplication.translate("CP2KStudio", 'CELL_OPT: omit MOTION/CELL_OPT/TYPE. This keyword has been removed in newer CP2K executables, which always use joint cell/coordinate optimization. Acceptance by a historical XML schema does not prove runtime compatibility.', 'cellopt.removed_type_error'),
        # ui/cell_opt_panel.py:22
        QCoreApplication.translate("CP2KStudio", 'RMS_DR', 'cellopt.rms_dr_label'),
        # ui/cell_opt_panel.py:20
        QCoreApplication.translate("CP2KStudio", 'RMS_FORCE', 'cellopt.rms_force_label'),
        # ui/cell_opt_panel.py:11
        QCoreApplication.translate("CP2KStudio", 'Cell optimization optimizes atomic coordinates and cell vectors together. The obsolete CELL_OPT / TYPE keyword is omitted. This release supports PERIODIC XYZ, Quickstep/GPW, the PERIODIC Poisson solver and ANALYTICAL stress. External pressure and pressure tolerance are in bar; external pressure is always written explicitly.', 'cellopt.settings_help'),
        # ui/cell_opt_panel.py:11
        QCoreApplication.translate("CP2KStudio", 'Optimization Settings', 'cellopt.settings_title'),
        # core/cell_optimization.py:42
        QCoreApplication.translate("CP2KStudio", 'CELL_OPT: this release supports analytical stress with Quickstep/GPW and POISSON_SOLVER PERIODIC only. Other solver combinations are not implemented; the solver was not changed.', 'cellopt.stress_error'),
        # ui/cell_opt_panel.py:45
        QCoreApplication.translate("CP2KStudio", 'CUBIC', 'cellopt.sym.cubic'),
        # ui/cell_opt_panel.py:42
        QCoreApplication.translate("CP2KStudio", 'HEXAGONAL', 'cellopt.sym.hexagonal'),
        # ui/cell_opt_panel.py:44
        QCoreApplication.translate("CP2KStudio", 'HEXAGONAL_GAMMA_120', 'cellopt.sym.hexagonal_120'),
        # ui/cell_opt_panel.py:43
        QCoreApplication.translate("CP2KStudio", 'HEXAGONAL_GAMMA_60', 'cellopt.sym.hexagonal_60'),
        # ui/cell_opt_panel.py:34
        QCoreApplication.translate("CP2KStudio", 'MONOCLINIC', 'cellopt.sym.monoclinic'),
        # ui/cell_opt_panel.py:35
        QCoreApplication.translate("CP2KStudio", 'MONOCLINIC_GAMMA_AB', 'cellopt.sym.monoclinic_ab'),
        # ui/cell_opt_panel.py:32
        QCoreApplication.translate("CP2KStudio", 'NONE', 'cellopt.sym.none'),
        # ui/cell_opt_panel.py:36
        QCoreApplication.translate("CP2KStudio", 'ORTHORHOMBIC', 'cellopt.sym.orthorhombic'),
        # ui/cell_opt_panel.py:41
        QCoreApplication.translate("CP2KStudio", 'RHOMBOHEDRAL', 'cellopt.sym.rhombohedral'),
        # ui/cell_opt_panel.py:40
        QCoreApplication.translate("CP2KStudio", 'TETRAGONAL', 'cellopt.sym.tetragonal'),
        # ui/cell_opt_panel.py:37
        QCoreApplication.translate("CP2KStudio", 'TETRAGONAL_AB', 'cellopt.sym.tetragonal_ab'),
        # ui/cell_opt_panel.py:38
        QCoreApplication.translate("CP2KStudio", 'TETRAGONAL_AC', 'cellopt.sym.tetragonal_ac'),
        # ui/cell_opt_panel.py:39
        QCoreApplication.translate("CP2KStudio", 'TETRAGONAL_BC', 'cellopt.sym.tetragonal_bc'),
        # ui/cell_opt_panel.py:33
        QCoreApplication.translate("CP2KStudio", 'TRICLINIC', 'cellopt.sym.triclinic'),
        # ui/cell_opt_panel.py:27
        QCoreApplication.translate("CP2KStudio", 'KEEP_SYMMETRY', 'cellopt.symmetry_label'),
        # core/cell_optimization.py:59
        QCoreApplication.translate("CP2KStudio", 'CELL_OPT: initial CELL / SYMMETRY {symmetry} does not match the current cell lengths and angles. Correct the selection or geometry; the cell was not modified.', 'cellopt.symmetry_mismatch'),
        # core/cell_optimization.py:57
        QCoreApplication.translate("CP2KStudio", 'CELL_OPT / KEEP_SYMMETRY: select an explicit initial CELL / SYMMETRY compatible with the current cell. NONE cannot preserve a requested cell symmetry.', 'cellopt.symmetry_missing'),
        # ui/cell_opt_panel.py:16
        QCoreApplication.translate("CP2KStudio", 'PRESSURE_TOLERANCE', 'cellopt.tolerance_label'),
        # core/cell_optimization.py:51
        QCoreApplication.translate("CP2KStudio", 'CELL_OPT: the cell must have finite positive volume and three independent right-handed vectors.', 'cellopt.volume_error'),
        # ui/dft_panel.py:39
        QCoreApplication.translate("CP2KStudio", 'EPS_DEFAULT · Quickstep Numerical Accuracy\n\nEPS_DEFAULT controls the default numerical accuracy thresholds used by Quickstep.\n\nFor demanding calculations, the following heuristic may be considered:\nEPS_DEFAULT ≤ (EPS_SCF)² × 100\n\nExamples:\n• EPS_SCF = 1E-6 → EPS_DEFAULT ≤ 1E-10\n• EPS_SCF = 1E-7 → EPS_DEFAULT ≤ 1E-12\n• EPS_SCF = 1E-8 → EPS_DEFAULT ≤ 1E-14\n\nThis is a heuristic, not a mandatory CP2K rule. Tighter thresholds may increase computational cost. Convergence testing is still required for accurate energies, forces, stresses, and vibrational frequencies.', 'dft.eps_default_help'),
        # core/validator.py:78
        QCoreApplication.translate("CP2KStudio", 'DFT / SURFACE_DIPOLE_CORRECTION: confirm an asymmetric slab with its surface normal parallel to Cartesian {direction} and sufficient vacuum. Studio does not infer surface symmetry or verify electron-density decay.', 'dipole.applicability_info'),
        # ui/dft_panel.py:51
        QCoreApplication.translate("CP2KStudio", 'Enable Surface Dipole Correction', 'dipole.enable'),
        # ui/dft_panel.py:47
        QCoreApplication.translate("CP2KStudio", 'Surface Dipole Correction\n\nReduces artificial electrostatic fields caused by interactions between periodic images of asymmetric slab models.\n\n• Intended primarily for asymmetric slabs modeled using 3D periodic supercells.\n• Does not replace nonperiodic boundary conditions.', 'dipole.help'),
        # core/validator.py:80
        QCoreApplication.translate("CP2KStudio", 'DFT / SURFACE_DIPOLE_CORRECTION: this correction is intended primarily for 3D periodic asymmetric slabs and is generally inappropriate for an isolated PERIODIC NONE molecule. Review whether to disable it; boundary settings have not been changed.', 'dipole.molecule_info'),
        # core/validator.py:82
        QCoreApplication.translate("CP2KStudio", 'DFT / SURFACE_DIPOLE_CORRECTION: partial periodicity {periodic} requires review of compatibility between the Poisson boundary treatment and dipole correction. This does not certify the combination; settings have not been changed.', 'dipole.partial_info'),
        # core/validator.py:84
        QCoreApplication.translate("CP2KStudio", 'DFT / SURFACE_DIPOLE_CORRECTION: review compatibility with POISSON_SOLVER {solver}. The standard 3D periodic slab workflow uses PERIODIC; Studio has not changed the solver.', 'dipole.solver_info'),
        # ui/dft_panel.py:46
        QCoreApplication.translate("CP2KStudio", 'Surface Dipole Correction', 'dipole.title'),
        # core/environment_check.py:571
        QCoreApplication.translate("CP2KStudio", 'Architecture', 'env.architecture'),
        # core/environment_check.py:573
        QCoreApplication.translate("CP2KStudio", 'Available Logical Cores (OS / affinity)', 'env.available_cores'),
        # core/environment_check.py:575
        QCoreApplication.translate("CP2KStudio", 'Available Memory', 'env.available_memory'),
        # core/environment_check.py:506
        QCoreApplication.translate("CP2KStudio", 'Build Type', 'env.build'),
        # core/environment_check.py:503
        QCoreApplication.translate("CP2KStudio", 'MPI', 'env.build_mpi'),
        # core/environment_check.py:502
        QCoreApplication.translate("CP2KStudio", 'MPI + OpenMP', 'env.build_mpi_omp'),
        # core/environment_check.py:505
        QCoreApplication.translate("CP2KStudio", 'Serial', 'env.build_serial'),
        # core/environment_check.py:504
        QCoreApplication.translate("CP2KStudio", 'Serial + OpenMP', 'env.build_serial_omp'),
        # core/environment_check.py:216
        QCoreApplication.translate("CP2KStudio", 'Build capabilities are not reported.', 'env.build_unknown'),
        # ui/environment_dialog.py:13
        QCoreApplication.translate("CP2KStudio", 'Environment Check', 'env.button'),
        # core/environment_check.py:431
        QCoreApplication.translate("CP2KStudio", 'Cancelled', 'env.cancelled'),
        # core/environment_check.py:463
        QCoreApplication.translate("CP2KStudio", 'This check could not be completed; other checks continue.', 'env.check_failed'),
        # core/environment_check.py:74
        QCoreApplication.translate("CP2KStudio", 'Checked at: {time}', 'env.checked_at'),
        # ui/environment_dialog.py:97
        QCoreApplication.translate("CP2KStudio", 'Checking environment…', 'env.checking'),
        # ui/environment_dialog.py:75
        QCoreApplication.translate("CP2KStudio", 'Close', 'env.close'),
        # ui/environment_dialog.py:143
        QCoreApplication.translate("CP2KStudio", 'Report copied to clipboard.', 'env.copied'),
        # ui/environment_dialog.py:74
        QCoreApplication.translate("CP2KStudio", 'Copy Report', 'env.copy'),
        # core/environment_check.py:472
        QCoreApplication.translate("CP2KStudio", 'CP2K Not Found', 'env.cp2k_missing'),
        # core/environment_check.py:497
        QCoreApplication.translate("CP2KStudio", 'CP2K Version', 'env.cp2k_version'),
        # core/environment_check.py:572
        QCoreApplication.translate("CP2KStudio", 'CPU', 'env.cpu'),
        # core/environment_check.py:574
        QCoreApplication.translate("CP2KStudio", 'Known CPU Capacity (OS / affinity / quota)', 'env.cpu_capacity'),
        # core/environment_check.py:471
        QCoreApplication.translate("CP2KStudio", 'Executable', 'env.executable'),
        # core/environment_check.py:429
        QCoreApplication.translate("CP2KStudio", 'Exit code {exitcode}', 'env.exit_code'),
        # core/environment_check.py:507
        QCoreApplication.translate("CP2KStudio", 'Reported Features', 'env.features'),
        # core/environment_check.py:507
        QCoreApplication.translate("CP2KStudio", 'Not reported; no features were assumed.', 'env.features_unknown'),
        # ui/environment_dialog.py:128
        QCoreApplication.translate("CP2KStudio", 'Inspection finished. No calculation was run.', 'env.finished'),
        # core/environment_check.py:28
        QCoreApplication.translate("CP2KStudio", 'CP2K Installation', 'env.group_cp2k'),
        # core/environment_check.py:30
        QCoreApplication.translate("CP2KStudio", 'Runtime & Scientific Libraries', 'env.group_libraries'),
        # core/environment_check.py:29
        QCoreApplication.translate("CP2KStudio", 'MPI Environment', 'env.group_mpi'),
        # core/environment_check.py:31
        QCoreApplication.translate("CP2KStudio", 'Python Dependencies', 'env.group_python'),
        # core/environment_check.py:32
        QCoreApplication.translate("CP2KStudio", 'System Information', 'env.group_system'),
        # core/environment_check.py:478
        QCoreApplication.translate("CP2KStudio", 'GUI PATH', 'env.gui_path'),
        # core/environment_check.py:579
        QCoreApplication.translate("CP2KStudio", 'Host / VM Available Memory', 'env.host_available_memory'),
        # core/environment_check.py:578
        QCoreApplication.translate("CP2KStudio", 'Host / VM Total Memory', 'env.host_memory'),
        # core/environment_check.py:580
        QCoreApplication.translate("CP2KStudio", 'Host / VM Memory Usage', 'env.host_memory_percent'),
        # core/environment_check.py:566
        QCoreApplication.translate("CP2KStudio", 'Installed', 'env.installed'),
        # core/environment_check.py:36
        QCoreApplication.translate("CP2KStudio", 'Issues Detected', 'env.issues'),
        # core/environment_check.py:556
        QCoreApplication.translate("CP2KStudio", 'Runtime Library', 'env.library'),
        # core/environment_check.py:557
        QCoreApplication.translate("CP2KStudio", 'Only observed dynamic links are listed. Missing names do not prove absent static libraries or disabled optional features. macOS shared-cache, transitive and late-loaded libraries may remain unverified.', 'env.library_scope'),
        # core/environment_check.py:392
        QCoreApplication.translate("CP2KStudio", 'Dependency inspection did not complete successfully ({status}).', 'env.linker_failed'),
        # core/environment_check.py:386
        QCoreApplication.translate("CP2KStudio", 'The platform dependency inspection tool is unavailable.', 'env.linker_missing'),
        # core/environment_check.py:573
        QCoreApplication.translate("CP2KStudio", 'Logical Cores', 'env.logical'),
        # core/environment_check.py:575
        QCoreApplication.translate("CP2KStudio", 'Total Memory', 'env.memory'),
        # core/environment_check.py:581
        QCoreApplication.translate("CP2KStudio", 'Container Memory Headroom (conservative estimate)', 'env.memory_headroom'),
        # core/environment_check.py:581
        QCoreApplication.translate("CP2KStudio", 'Container Memory Limit', 'env.memory_limit'),
        # core/environment_check.py:576
        QCoreApplication.translate("CP2KStudio", 'Memory Usage', 'env.memory_percent'),
        # core/environment_check.py:566
        QCoreApplication.translate("CP2KStudio", 'Version Mismatch', 'env.mismatch'),
        # core/environment_check.py:566
        QCoreApplication.translate("CP2KStudio", 'Missing', 'env.missing'),
        # core/environment_check.py:472
        QCoreApplication.translate("CP2KStudio", 'Check installation and the GUI process PATH. Common platform installation and current Python/Conda locations were also checked. Input generation remains available.', 'env.missing_note'),
        # core/environment_check.py:536
        QCoreApplication.translate("CP2KStudio", 'MPI Runtime', 'env.mpi'),
        # core/environment_check.py:542
        QCoreApplication.translate("CP2KStudio", 'Launcher presence does not verify ABI compatibility with CP2K. No MPI job was launched.', 'env.mpi_abi'),
        # core/environment_check.py:542
        QCoreApplication.translate("CP2KStudio", 'Configured MPI Compatibility', 'env.mpi_compatibility'),
        # core/environment_check.py:521
        QCoreApplication.translate("CP2KStudio", 'mpirun / mpiexec not found.', 'env.mpi_missing'),
        # core/environment_check.py:536
        QCoreApplication.translate("CP2KStudio", 'Unknown implementation/version', 'env.mpi_unknown'),
        # core/environment_check.py:551
        QCoreApplication.translate("CP2KStudio", 'No CP2K executable is available to inspect.', 'env.no_library_target'),
        # core/environment_check.py:554
        QCoreApplication.translate("CP2KStudio", 'No resolvable dynamic links were reported.', 'env.no_links'),
        # core/environment_check.py:37
        QCoreApplication.translate("CP2KStudio", 'CP2K Not Installed', 'env.not_installed'),
        # core/environment_check.py:432
        QCoreApplication.translate("CP2KStudio", 'Not probed within the time budget', 'env.not_probed'),
        # core/environment_check.py:547
        QCoreApplication.translate("CP2KStudio", 'Not set', 'env.not_set'),
        # core/environment_check.py:479
        QCoreApplication.translate("CP2KStudio", 'CP2K was found outside the GUI PATH. Finder and Terminal may have different environments. Configure the target terminal before Local Run; Studio did not modify PATH.', 'env.off_path'),
        # core/environment_check.py:547
        QCoreApplication.translate("CP2KStudio", 'Invalid OpenMP thread-count value (not copied).', 'env.omp_invalid'),
        # core/environment_check.py:564
        QCoreApplication.translate("CP2KStudio", 'Optional', 'env.optional'),
        # core/environment_check.py:557
        QCoreApplication.translate("CP2KStudio", 'Optional / Static Scientific Libraries', 'env.optional_libraries'),
        # core/environment_check.py:571
        QCoreApplication.translate("CP2KStudio", 'Operating System', 'env.os'),
        # core/environment_check.py:434
        QCoreApplication.translate("CP2KStudio", 'Output limit exceeded', 'env.output_limit'),
        # core/environment_check.py:567
        QCoreApplication.translate("CP2KStudio", '{name} · {kind}', 'env.package_label'),
        # core/environment_check.py:567
        QCoreApplication.translate("CP2KStudio", '{state}; installed: {version}; required: {specifier}', 'env.package_value'),
        # core/environment_check.py:313
        QCoreApplication.translate("CP2KStudio", 'The packaging library is unavailable; requirements cannot be evaluated.', 'env.packaging_missing'),
        # core/environment_check.py:38
        QCoreApplication.translate("CP2KStudio", 'Partially Verified', 'env.partial'),
        # core/environment_check.py:572
        QCoreApplication.translate("CP2KStudio", 'Physical Cores', 'env.physical'),
        # core/environment_check.py:537
        QCoreApplication.translate("CP2KStudio", '{path}; {status}', 'env.probe_detail'),
        # core/environment_check.py:459
        QCoreApplication.translate("CP2KStudio", 'Checking: {section}', 'env.progress'),
        # core/environment_check.py:339
        QCoreApplication.translate("CP2KStudio", 'pyproject.toml could not be evaluated; dependency metadata is incomplete.', 'env.pyproject_unknown'),
        # core/environment_check.py:560
        QCoreApplication.translate("CP2KStudio", 'Current Python', 'env.python'),
        # ui/environment_dialog.py:98
        QCoreApplication.translate("CP2KStudio", 'Inspecting this computer without changing calculation settings.', 'env.readonly'),
        # core/environment_check.py:35
        QCoreApplication.translate("CP2KStudio", 'Environment Ready', 'env.ready'),
        # ui/environment_dialog.py:73
        QCoreApplication.translate("CP2KStudio", 'Recheck', 'env.recheck'),
        # core/environment_check.py:215
        QCoreApplication.translate("CP2KStudio", 'Reported build flags', 'env.reported_flags'),
        # core/environment_check.py:564
        QCoreApplication.translate("CP2KStudio", 'Required (declared)', 'env.required'),
        # core/environment_check.py:341
        QCoreApplication.translate("CP2KStudio", 'Dependency declarations are unavailable; include requirements.txt and distribution metadata when packaging.', 'env.requirements_missing'),
        # core/environment_check.py:588
        QCoreApplication.translate("CP2KStudio", 'Comparison is local; the exported configuration may target another machine. CPU and memory alone cannot predict DFT completion.', 'env.resource_note'),
        # core/environment_check.py:588
        QCoreApplication.translate("CP2KStudio", 'MPI: {mpi}; OpenMP: {omp}; required logical slots: {slots}', 'env.resource_values'),
        # core/environment_check.py:588
        QCoreApplication.translate("CP2KStudio", 'Configured Resources (read-only)', 'env.resources'),
        # core/environment_check.py:86
        QCoreApplication.translate("CP2KStudio", 'Local inspection only. No DFT, SCF, or MD calculation was run. Installation checks do not verify all CP2K functions or numerical correctness. Results do not change the project, XML schema, or exported run settings.', 'env.scope'),
        # core/environment_check.py:544
        QCoreApplication.translate("CP2KStudio", 'Exported run.sh', 'env.script'),
        # core/environment_check.py:544
        QCoreApplication.translate("CP2KStudio", 'The existing script expects cp2k.psmp on PATH. This inspection does not change the script or choose another executable for it.', 'env.script_note'),
        # core/environment_check.py:475
        QCoreApplication.translate("CP2KStudio", 'Current Detection Target', 'env.selected'),
        # core/environment_check.py:540
        QCoreApplication.translate("CP2KStudio", 'Multiple MPI ranks are configured, but the selected CP2K build is serial.', 'env.serial_warning'),
        # core/environment_check.py:390
        QCoreApplication.translate("CP2KStudio", 'Static or unlisted libraries cannot be verified from dynamic-link output; they are not marked missing.', 'env.static_libraries'),
        # core/environment_check.py:213
        QCoreApplication.translate("CP2KStudio", 'Inferred from executable suffix; not a numerical test.', 'env.suffix_note'),
        # core/environment_check.py:430
        QCoreApplication.translate("CP2KStudio", 'Timed out', 'env.timeout'),
        # core/environment_check.py:73
        QCoreApplication.translate("CP2KStudio", 'CP2K Studio · Environment Check', 'env.title'),
        # core/environment_check.py:433
        QCoreApplication.translate("CP2KStudio", 'Unavailable or permission denied', 'env.unavailable'),
        # core/environment_check.py:505
        QCoreApplication.translate("CP2KStudio", 'Unknown', 'env.unknown'),
        # core/environment_check.py:494
        QCoreApplication.translate("CP2KStudio", '{path}; revision: {revision}', 'env.version_detail'),
        # core/environment_check.py:496
        QCoreApplication.translate("CP2KStudio", '{detail}. Studio targets CP2K 2026.1; input specifications may differ. XML and calculation settings were not changed.', 'env.version_mismatch'),
        # core/environment_check.py:383
        QCoreApplication.translate("CP2KStudio", 'Native Windows DLL resolution is not verified. WSL2 is inspected as Linux.', 'env.windows_libraries'),
        # ui/environment_dialog.py:14
        QCoreApplication.translate("CP2KStudio", 'Inspection could not be completed. Recheck or copy the partial report.', 'env.worker_failed'),
        # ui/help_dialog.py:34
        QCoreApplication.translate("CP2KStudio", 'Developer', 'help.developer'),
        # ui/help_dialog.py:28
        QCoreApplication.translate("CP2KStudio", 'Purpose', 'help.purpose'),
        # ui/help_dialog.py:29
        QCoreApplication.translate("CP2KStudio", 'CP2K Studio is a visual tool for generating CP2K input files. Configure calculation parameters through the graphical interface and quickly generate CP2K input files (.inp), simplifying the input-writing process.', 'help.purpose_text'),
        # ui/help_dialog.py:31
        QCoreApplication.translate("CP2KStudio", 'Quick Start', 'help.quick_start'),
        # ui/help_dialog.py:32
        QCoreApplication.translate("CP2KStudio", 'Follow the numbered steps in the interface to enter or select calculation parameters. After checking the parameters, click Export to generate the CP2K input file.', 'help.quick_start_text'),
        # ui/help_dialog.py:11
        QCoreApplication.translate("CP2KStudio", 'CP2K Studio · Help', 'help.title'),
        # core/local_run.py:219
        QCoreApplication.translate("CP2KStudio", 'A calculation or pending terminal launch already exists for this folder. Check the existing terminals before starting another run.', 'local.active_directory'),
        # core/local_run.py:193
        QCoreApplication.translate("CP2KStudio", 'macOS denied Terminal automation. Allow the application hosting Python/CP2K Studio to control Terminal in System Settings → Privacy & Security → Automation, then retry.', 'local.automation_denied'),
        # core/local_run.py:190
        QCoreApplication.translate("CP2KStudio", 'Terminal automation timed out. The terminal may have opened; inspect it before retrying.', 'local.automation_timeout'),
        # ui/local_run_dialog.py:170
        QCoreApplication.translate("CP2KStudio", 'Local Run', 'local.button'),
        # ui/local_run_dialog.py:50
        QCoreApplication.translate("CP2KStudio", 'Cancel', 'local.cancel'),
        # ui/local_run_dialog.py:161
        QCoreApplication.translate("CP2KStudio", 'Cannot Start Local Run', 'local.cannot_start'),
        # ui/local_run_dialog.py:23
        QCoreApplication.translate("CP2KStudio", 'Run Command', 'local.command'),
        # core/local_run.py:211
        QCoreApplication.translate("CP2KStudio", 'Confirm Run before executing the selected script.', 'local.confirm_required'),
        # core/local_run.py:147
        QCoreApplication.translate("CP2KStudio", 'This launch was cancelled or superseded before execution. run.sh was not started.', 'local.console_cancelled'),
        # core/local_run.py:148
        QCoreApplication.translate("CP2KStudio", 'A calculation already owns this directory. This second script was not started.', 'local.console_duplicate'),
        # core/local_run.py:144
        QCoreApplication.translate("CP2KStudio", '\nrun.sh exit code: {exit_code}. This is the script status, not proof of CP2K convergence; inspect the calculation terminal and log.', 'local.console_exit'),
        # core/local_run.py:146
        QCoreApplication.translate("CP2KStudio", 'Could not run the selected script: {error}', 'local.console_failed'),
        # core/local_run.py:145
        QCoreApplication.translate("CP2KStudio", 'Press Enter to close this terminal command…', 'local.console_hold'),
        # core/local_run.py:149
        QCoreApplication.translate("CP2KStudio", 'Ctrl+C received; waiting for the foreground run.sh to exit.', 'local.console_interrupted'),
        # core/local_run.py:141
        QCoreApplication.translate("CP2KStudio", 'Output monitor: {directory}/output.out\nFollowing file changes (tail -n 30 -F behavior). Ctrl+C stops only this monitor.', 'local.console_monitor'),
        # core/local_run.py:151
        QCoreApplication.translate("CP2KStudio", 'Output monitoring stopped. No stop signal was sent to the calculation.', 'local.console_monitor_stopped'),
        # core/local_run.py:142
        QCoreApplication.translate("CP2KStudio", 'An existing output.out was found. Unchanged pre-launch content is excluded; waiting for new output. No success is inferred from log contents.', 'local.console_old_log'),
        # core/local_run.py:150
        QCoreApplication.translate("CP2KStudio", 'Cannot read output.out yet: {error}. Retrying…', 'local.console_read_error'),
        # core/local_run.py:140
        QCoreApplication.translate("CP2KStudio", 'Calculation directory: {directory}\nRunning: bash run.sh', 'local.console_running'),
        # core/local_run.py:143
        QCoreApplication.translate("CP2KStudio", 'Waiting for output.out to be created…', 'local.console_waiting'),
        # ui/local_run_dialog.py:22
        QCoreApplication.translate("CP2KStudio", 'Calculation Directory', 'local.directory'),
        # core/local_run.py:66
        QCoreApplication.translate("CP2KStudio", 'Extract the ZIP package first, then select its calculation folder.', 'local.extract_zip'),
        # core/windows_local_run.py:229
        QCoreApplication.translate("CP2KStudio", 'Follow output.out (equivalent to tail -n 30 -F).', 'local.follow'),
        # core/local_run.py:169
        QCoreApplication.translate("CP2KStudio", 'The bundled Local Run helper is missing or cannot be executed. Rebuild or restore the complete CP2K Studio.app.', 'local.helper_missing'),
        # core/local_run.py:68
        QCoreApplication.translate("CP2KStudio", 'Calculation directory does not exist: {path}', 'local.missing_directory'),
        # core/local_run.py:72
        QCoreApplication.translate("CP2KStudio", 'Missing {filename} in the calculation folder.', 'local.missing_file'),
        # core/local_run.py:115
        QCoreApplication.translate("CP2KStudio", 'Bash is not available. Configure Bash before running this package; no installation or PATH changes were made.', 'local.no_bash'),
        # core/local_run.py:93
        QCoreApplication.translate("CP2KStudio", 'No graphical desktop session was detected. Local Run requires a visible system terminal; no background calculation was started.', 'local.no_display'),
        # core/local_run.py:106
        QCoreApplication.translate("CP2KStudio", 'No supported graphical terminal is available. macOS requires Terminal.app; Linux supports gnome-terminal, konsole, xfce4-terminal or xterm.', 'local.no_terminal'),
        # ui/local_run_dialog.py:40
        QCoreApplication.translate("CP2KStudio", 'Existing output.out is retained. Unchanged old content will be skipped by the monitor; run.sh itself may overwrite results.', 'local.old_output'),
        # ui/local_run_dialog.py:24
        QCoreApplication.translate("CP2KStudio", 'Output Monitor', 'local.output_monitor'),
        # ui/local_run_dialog.py:174
        QCoreApplication.translate("CP2KStudio", 'The calculation terminal was opened, but the output monitor could not be opened: {error}\n\nThe script may already be running. Check the calculation terminal; do not start it again just to open a monitor.', 'local.partial'),
        # ui/local_run_dialog.py:51
        QCoreApplication.translate("CP2KStudio", 'Run', 'local.run'),
        # ui/local_run_dialog.py:104
        QCoreApplication.translate("CP2KStudio", 'Select Calculation Folder', 'local.select_folder'),
        # ui/local_run_dialog.py:176
        QCoreApplication.translate("CP2KStudio", 'run.sh started in the calculation terminal. A separate terminal follows output.out. Startup does not confirm CP2K success; inspect the script exit code and logs. Closing the monitor or Studio does not stop the calculation.', 'local.started'),
        # core/local_run.py:194
        QCoreApplication.translate("CP2KStudio", 'Terminal could not be opened: {error}', 'local.terminal_failed'),
        # ui/local_run_dialog.py:36
        QCoreApplication.translate("CP2KStudio", 'This executes the selected run.sh on your computer. Only run packages you created or trust.', 'local.trust'),
        # ui/local_run_dialog.py:45
        QCoreApplication.translate("CP2KStudio", 'A previous launch has no confirmed exit status. Check existing terminals and processes before running again. Manually started jobs cannot be detected reliably.', 'local.uncertain'),
        # ui/local_run_dialog.py:178
        QCoreApplication.translate("CP2KStudio", 'Terminal launch requests were sent, but script startup has not been confirmed. Check both terminals before retrying. Terminal startup is not proof of CP2K success.', 'local.unconfirmed'),
        # core/local_run.py:77
        QCoreApplication.translate("CP2KStudio", 'Cannot read {filename}: {error}', 'local.unreadable'),
        # core/local_run.py:134
        QCoreApplication.translate("CP2KStudio", 'Unsupported terminal adapter: {name}', 'local.unsupported_terminal'),
        # core/local_run.py:105
        QCoreApplication.translate("CP2KStudio", 'Local Run currently supports macOS and Linux graphical terminals. Windows/WSL launching is not configured; CMD will not be used.', 'local.windows_unsupported'),
        # core/md.py:134
        QCoreApplication.translate("CP2KStudio", 'MD: all atomic components are fixed; no dynamical degrees of freedom remain.', 'md.all_fixed'),
        # ui/md_panel.py:44
        QCoreApplication.translate("CP2KStudio", 'Backup Copies', 'md.backup_copies'),
        # ui/md_panel.py:14
        QCoreApplication.translate("CP2KStudio", 'Born–Oppenheimer AIMD uses the existing Quickstep DFT forces. NVT maintains constant temperature and volume; NVE conserves energy. TIMESTEP is in fs; test timestep convergence, especially for hydrogen and fast vibrations. TEMPERATURE is the NVT target, or initializes velocities in NVE when none are supplied. NVE is not continuously thermostatted. STEPS counts additional steps from the restart counter.', 'md.basic_help'),
        # ui/md_panel.py:14
        QCoreApplication.translate("CP2KStudio", 'MD Basic Settings', 'md.basic_title'),
        # ui/md_panel.py:49
        QCoreApplication.translate("CP2KStudio", 'Choose Restart…', 'md.choose_restart'),
        # ui/md_panel.py:61
        QCoreApplication.translate("CP2KStudio", 'Choose MD Restart', 'md.choose_restart_title'),
        # ui/md_panel.py:45
        QCoreApplication.translate("CP2KStudio", 'Continue from Restart', 'md.continue'),
        # core/md.py:121
        QCoreApplication.translate("CP2KStudio", 'MD: check total-energy drift in NVE, and temperature stability and thermal equilibration in NVT.', 'md.ensemble_info'),
        # ui/md_panel.py:16
        QCoreApplication.translate("CP2KStudio", 'ENSEMBLE', 'md.ensemble_label'),
        # ui/export_panel.py:26
        QCoreApplication.translate("CP2KStudio", '06 Molecular Dynamics', 'md.error_page'),
        # core/export_notes_generator.py:31
        QCoreApplication.translate("CP2KStudio", '7. BORN–OPPENHEIMER AIMD\nEnsemble: {ensemble}; steps: {steps}; timestep: {dt} fs; duration: {duration} ps; temperature: {temperature} K.\nNVT uses CSVR; NVE has no thermostat and TEMPERATURE only initializes absent velocities.\nTrajectory: {trajectory}, format {format}, interval {interval} steps. Restart output: {restart}, interval {restart_interval} steps, backup copies {copies}.\nCP2K produces trajectory files (typically project-pos-1.xyz or EXTXYZ) and project-1.ener containing step/time, temperature, kinetic energy, potential energy and conserved quantity. In NVE, also inspect kinetic plus potential energy drift; in NVT, conserved quantity includes the thermostat contribution. Actual filenames follow CP2K print conventions. No trajectory, energies or other calculation results are included in this package.\nContinuation: {continuation}. When enabled, EXT_RESTART restores coordinates, velocities, cell and counters; CSVR energy and RNG state are restored explicitly for NVT. STEPS counts additional steps from the restored counter. The viewer and structure.xyz show the project structure, while CP2K reads restart positions at runtime. WFN restart is independent; SCF_GUESS is not changed. Verify electronic settings and physical continuity after resuming; XML and static restart checks are not a runtime verification.\nRun each segment in a fresh package directory. Studio does not concatenate trajectories or implement output appending. Keep the source restart and previous output files separately.\nTest timestep, SCF and grid convergence. NVE needs energy-drift checks; NVT needs temperature and equilibration checks. Simulation length alone does not establish statistical equilibrium. FIXED_ATOMS are retained in fractional coordinates.\n', 'md.export_notes'),
        # core/md.py:132
        QCoreApplication.translate("CP2KStudio", 'MD: FIXED_ATOMS are retained in fractional coordinates. Check constrained degrees of freedom and thermostat temperature interpretation.', 'md.fixed_info'),
        # core/input_import.py:117
        QCoreApplication.translate("CP2KStudio", 'MD: NVE input must not contain a thermostat.', 'md.import_nve'),
        # core/input_import.py:141
        QCoreApplication.translate("CP2KStudio", 'MD: partial EXT_RESTART settings cannot be represented as full MD continuation. Keep the original input or configure a complete restart explicitly.', 'md.import_partial_restart'),
        # core/input_import.py:121
        QCoreApplication.translate("CP2KStudio", 'MD: only one MOTION/PRINT configuration can be imported.', 'md.import_prints'),
        # core/input_import.py:27
        QCoreApplication.translate("CP2KStudio", 'Explicitly specify a supported RUN_TYPE: ENERGY, GEO_OPT, VIBRATIONAL_ANALYSIS, CELL_OPT or MD', 'md.import_run_error'),
        # core/input_import.py:115
        QCoreApplication.translate("CP2KStudio", 'MD: only GLOBAL CSVR thermostats can be imported for NVT.', 'md.import_thermostat'),
        # core/models.py:357
        QCoreApplication.translate("CP2KStudio", 'MD: {parameter} must be an integer greater than or equal to {minimum}.', 'md.integer_error'),
        # core/presets.py:186
        QCoreApplication.translate("CP2KStudio", 'Molecular Dynamics', 'md.name'),
        # ui/main_window.py:340
        QCoreApplication.translate("CP2KStudio", '06  Molecular Dynamics', 'md.nav'),
        # core/models.py:372
        QCoreApplication.translate("CP2KStudio", 'MD: {parameter} must be a finite nonnegative number.', 'md.nonnegative_error'),
        # ui/md_panel.py:18
        QCoreApplication.translate("CP2KStudio", 'NVE — Constant Energy', 'md.nve'),
        # ui/md_panel.py:17
        QCoreApplication.translate("CP2KStudio", 'NVT — Constant T & V', 'md.nvt'),
        # core/models.py:384
        QCoreApplication.translate("CP2KStudio", 'MD: unsupported {parameter}; supported values: {choices}.', 'md.option_error'),
        # ui/md_panel.py:35
        QCoreApplication.translate("CP2KStudio", 'Trajectory files are generated only by CP2K. EXTXYZ preserves cell information for periodic systems. The energy file records MD step/time, temperature, kinetic and potential energies and the conserved quantity. Studio does not run dynamics or append previous trajectories.', 'md.output_help'),
        # ui/md_panel.py:35
        QCoreApplication.translate("CP2KStudio", 'Trajectory & Output', 'md.output_title'),
        # core/md.py:161
        QCoreApplication.translate("CP2KStudio", 'MD: an initial atom pair is closer than 0.2 Å, including periodic images. Check the structure before dynamics.', 'md.overlap_error'),
        # core/bundle_checks.py:36
        QCoreApplication.translate("CP2KStudio", 'MD: final packaged restart is invalid: {detail}', 'md.package_restart_error'),
        # core/bundle_checks.py:22
        QCoreApplication.translate("CP2KStudio", 'MD: continuation requires exactly one final EXT_RESTART/RESTART_FILE_NAME reference.', 'md.package_restart_reference'),
        # ui/md_panel.py:12
        QCoreApplication.translate("CP2KStudio", '06 · Molecular Dynamics', 'md.page_title'),
        # core/md.py:143
        QCoreApplication.translate("CP2KStudio", 'MD: {detail}', 'md.path_warning'),
        # core/models.py:374
        QCoreApplication.translate("CP2KStudio", 'MD: {parameter} must be a finite positive number.', 'md.positive_error'),
        # core/md.py:119
        QCoreApplication.translate("CP2KStudio", 'MD: start from a sufficiently relaxed structure to reduce unphysical initial forces. No geometry optimization has been verified.', 'md.relax_info'),
        # core/md.py:61
        QCoreApplication.translate("CP2KStudio", 'MD: restart atom count, KIND labels or atom order differ from the current structure. Import matching structure settings first.', 'md.restart_atoms'),
        # core/md.py:79
        QCoreApplication.translate("CP2KStudio", 'MD: restart cell or periodicity is missing, invalid or differs from the current fixed-volume cell. Import matching cell settings first.', 'md.restart_cell'),
        # core/md.py:43
        QCoreApplication.translate("CP2KStudio", 'MD: restart requires complete embedded atomic coordinates.', 'md.restart_coords'),
        # core/bundle_checks.py:34
        QCoreApplication.translate("CP2KStudio", 'MD: the copied restart differs from its source. The file may have changed during export; regenerate the package.', 'md.restart_copy_changed'),
        # core/md.py:84
        QCoreApplication.translate("CP2KStudio", 'MD: restart requires valid STEP_START_VAL and TIME_START_VAL counters.', 'md.restart_counters'),
        # core/md.py:95
        QCoreApplication.translate("CP2KStudio", 'MD: NVT restart requires the GLOBAL CSVR thermostat energy and RNG state. Incomplete or other thermostat restarts are not supported.', 'md.restart_csvr'),
        # core/md.py:64
        QCoreApplication.translate("CP2KStudio", 'MD: restart KIND element definitions do not match the current structure.', 'md.restart_elements'),
        # core/md.py:86
        QCoreApplication.translate("CP2KStudio", 'MD: restart ensemble must match the selected NVT/NVE ensemble in this release.', 'md.restart_ensemble'),
        # core/md.py:163
        QCoreApplication.translate("CP2KStudio", 'MD: restart or initial structure check failed: {detail}', 'md.restart_error'),
        # ui/md_panel.py:62
        QCoreApplication.translate("CP2KStudio", 'CP2K Restart (*.restart);;All Files (*)', 'md.restart_filter'),
        # core/md.py:156
        QCoreApplication.translate("CP2KStudio", 'MD: restart coordinates must be finite.', 'md.restart_finite'),
        # ui/md_panel.py:40
        QCoreApplication.translate("CP2KStudio", 'MD restart is separate from WFN restart. Continuation requires matching atom/KIND order and cell, positions, velocities and counters; NVT also requires GLOBAL CSVR energy and RNG state. Self-contained text .restart files are supported. SCF_GUESS is unchanged. Static checks do not prove physical continuity; verify the resumed trajectory and electronic settings. The package copies the source under data/ and never overwrites it.', 'md.restart_help'),
        # core/md.py:157
        QCoreApplication.translate("CP2KStudio", 'MD: EXT_RESTART restores positions, velocities, cell and counters at runtime; the viewer shows the project structure. Verify electronic settings and continuity after restarting. WFN restart is separate and SCF_GUESS is unchanged. Restart state has only been checked statically.', 'md.restart_info'),
        # ui/md_panel.py:43
        QCoreApplication.translate("CP2KStudio", 'Restart Interval', 'md.restart_interval'),
        # core/md.py:35
        QCoreApplication.translate("CP2KStudio", 'MD: restart must contain one Quickstep FORCE_EVAL.', 'md.restart_method'),
        # core/md.py:53
        QCoreApplication.translate("CP2KStudio", 'MD: choose an existing, readable .restart file.', 'md.restart_missing'),
        # ui/md_panel.py:48
        QCoreApplication.translate("CP2KStudio", 'Select a complete MD .restart file', 'md.restart_placeholder'),
        # core/md.py:28
        QCoreApplication.translate("CP2KStudio", 'MD: only self-contained text restart files without preprocessor directives are supported.', 'md.restart_preprocessor'),
        # core/md.py:110
        QCoreApplication.translate("CP2KStudio", 'MD: CSVR RNG state is not a valid CP2K 2026.1 fixed-width stream record.', 'md.restart_rng'),
        # core/md.py:25
        QCoreApplication.translate("CP2KStudio", 'MD: restart exceeds the 100 MB limit.', 'md.restart_size'),
        # core/md.py:165
        QCoreApplication.translate("CP2KStudio", 'MD: a matching project structure is required before continuing from restart.', 'md.restart_structure'),
        # core/md.py:37
        QCoreApplication.translate("CP2KStudio", 'MD: select a molecular-dynamics restart, not an XYZ frame or optimization restart.', 'md.restart_task'),
        # ui/md_panel.py:40
        QCoreApplication.translate("CP2KStudio", 'Restart Settings', 'md.restart_title'),
        # core/md.py:154
        QCoreApplication.translate("CP2KStudio", 'MD: unsupported restart coordinate unit.', 'md.restart_unit'),
        # core/md.py:68
        QCoreApplication.translate("CP2KStudio", 'MD: restart is missing complete finite atomic velocities; a final XYZ frame is not a full MD restart.', 'md.restart_velocity'),
        # core/md.py:31
        QCoreApplication.translate("CP2KStudio", 'MD: restart XML validation failed: {detail}', 'md.restart_xml'),
        # core/md.py:120
        QCoreApplication.translate("CP2KStudio", 'MD: test timestep convergence. Simulation length does not establish statistical equilibrium; diffusion and other dynamical properties usually require longer sampling.', 'md.sampling_info'),
        # core/md.py:123
        QCoreApplication.translate("CP2KStudio", 'MD: EPS_SCF exceeds 1E-6; test tighter SCF thresholds for reliable forces and energy conservation.', 'md.scf_warning'),
        # ui/md_panel.py:19
        QCoreApplication.translate("CP2KStudio", 'STEPS', 'md.steps_label'),
        # ui/md_panel.py:43
        QCoreApplication.translate("CP2KStudio", 'steps', 'md.steps_unit'),
        # ui/md_panel.py:21
        QCoreApplication.translate("CP2KStudio", 'TEMPERATURE', 'md.temperature_label'),
        # ui/md_panel.py:30
        QCoreApplication.translate("CP2KStudio", 'CSVR is used only for NVT. TIMECON is the coupling time in fs; excessively short coupling may perturb dynamics. NVE generates no thermostat. Switching ensemble preserves TIMECON.', 'md.thermostat_help'),
        # ui/md_panel.py:30
        QCoreApplication.translate("CP2KStudio", 'Thermostat Settings', 'md.thermostat_title'),
        # ui/md_panel.py:32
        QCoreApplication.translate("CP2KStudio", 'THERMOSTAT TYPE', 'md.thermostat_type'),
        # core/md.py:127
        QCoreApplication.translate("CP2KStudio", 'MD: CSVR TIMECON is smaller than TIMESTEP; strong thermostat coupling may distort dynamics.', 'md.timecon_warning'),
        # ui/md_panel.py:20
        QCoreApplication.translate("CP2KStudio", 'TIMESTEP', 'md.timestep_label'),
        # core/md.py:125
        QCoreApplication.translate("CP2KStudio", 'MD: the selected timestep is large for unconstrained AIMD, especially with hydrogen. Test a smaller timestep.', 'md.timestep_warning'),
        # ui/md_panel.py:72
        QCoreApplication.translate("CP2KStudio", 'Total Simulation Time: {time} ps', 'md.total_time'),
        # ui/md_panel.py:74
        QCoreApplication.translate("CP2KStudio", 'Total Simulation Time: —', 'md.total_time_invalid'),
        # ui/md_panel.py:38
        QCoreApplication.translate("CP2KStudio", 'Trajectory Format', 'md.trajectory_format'),
        # ui/md_panel.py:39
        QCoreApplication.translate("CP2KStudio", 'Trajectory Interval', 'md.trajectory_interval'),
        # ui/md_panel.py:42
        QCoreApplication.translate("CP2KStudio", 'Write Restart', 'md.write_restart'),
        # ui/md_panel.py:37
        QCoreApplication.translate("CP2KStudio", 'Write Trajectory', 'md.write_trajectory'),
        # core/md.py:129
        QCoreApplication.translate("CP2KStudio", 'MD: zero-temperature CSVR dynamics needs special care; verify initialization and thermostat suitability.', 'md.zero_temperature'),
        # ui/structure_panel.py:133
        QCoreApplication.translate("CP2KStudio", 'Confirm Isolated Molecule…', 'periodicity.confirm_button'),
        # ui/structure_panel.py:330
        QCoreApplication.translate("CP2KStudio", 'Confirm that this is an isolated non-periodic molecule? PERIODIC will be fixed to NONE. The cell vectors and coordinates will remain unchanged.', 'periodicity.confirm_text'),
        # ui/structure_panel.py:329
        QCoreApplication.translate("CP2KStudio", 'Confirm Isolated Molecule', 'periodicity.confirm_title'),
        # ui/structure_panel.py:315
        QCoreApplication.translate("CP2KStudio", 'The imported structure is a non-periodic molecule. Periodicity is fixed to NONE.', 'periodicity.lock_tooltip'),
        # core/models.py:73
        QCoreApplication.translate("CP2KStudio", 'CELL: a confirmed isolated molecule must use PERIODIC NONE. Periodic presets or project data cannot override this structure type.', 'periodicity.molecule_error'),
        # core/presets.py:141
        QCoreApplication.translate("CP2KStudio", 'CELL: a periodic preset cannot unlock a confirmed isolated molecule. Import the new periodic structure explicitly.', 'periodicity.preset_error'),
        # ui/structure_panel.py:368
        QCoreApplication.translate("CP2KStudio", 'XSD structure type is unconfirmed. Review PERIODIC, or explicitly confirm an isolated molecule before locking NONE.', 'periodicity.unconfirmed_hint'),
        # ui/widgets/poisson_reference.py:50
        QCoreApplication.translate("CP2KStudio", '1D periodic systems', 'poisson.app.analytic_wire'),
        # ui/widgets/poisson_reference.py:65
        QCoreApplication.translate("CP2KStudio", 'Constant-potential electrodes and related interface models', 'poisson.app.implicit_electrode'),
        # ui/widgets/poisson_reference.py:64
        QCoreApplication.translate("CP2KStudio", 'Implicit solvation effects', 'poisson.app.implicit_solvent'),
        # ui/widgets/poisson_reference.py:42
        QCoreApplication.translate("CP2KStudio", 'Isolated clusters with net charge', 'poisson.app.mt_charge'),
        # ui/widgets/poisson_reference.py:43
        QCoreApplication.translate("CP2KStudio", 'Elongated isolated molecules or finite polymer segments', 'poisson.app.mt_polymer'),
        # ui/widgets/poisson_reference.py:44
        QCoreApplication.translate("CP2KStudio", '2D periodic surface models', 'poisson.app.mt_surface'),
        # ui/widgets/poisson_reference.py:57
        QCoreApplication.translate("CP2KStudio", 'Electrostatic decoupling of QM regions, for example in QM/MM calculations', 'poisson.app.multipole_qmmm'),
        # ui/widgets/poisson_reference.py:26
        QCoreApplication.translate("CP2KStudio", 'Amorphous bulk models', 'poisson.app.periodic_amorphous'),
        # ui/widgets/poisson_reference.py:25
        QCoreApplication.translate("CP2KStudio", '3D crystalline materials', 'poisson.app.periodic_crystal'),
        # ui/widgets/poisson_reference.py:27
        QCoreApplication.translate("CP2KStudio", '3D periodic solid–liquid interface supercells', 'poisson.app.periodic_interface'),
        # ui/widgets/poisson_reference.py:33
        QCoreApplication.translate("CP2KStudio", '0D isolated molecules, clusters and ion pairs', 'poisson.app.wavelet_molecule'),
        # ui/widgets/poisson_reference.py:34
        QCoreApplication.translate("CP2KStudio", '2D orthogonal surface models with the nonperiodic normal along Y', 'poisson.app.wavelet_surface'),
        # ui/widgets/poisson_reference.py:73
        QCoreApplication.translate("CP2KStudio", 'Recommended Applications', 'poisson.applications'),
        # ui/widgets/poisson_reference.py:74
        QCoreApplication.translate("CP2KStudio", 'Constraints & Notes', 'poisson.constraints'),
        # core/validator.py:65
        QCoreApplication.translate("CP2KStudio", 'MT requires a sufficiently large simulation cell. Check the electron-density extent, vacuum size, and convergence.', 'poisson.mt_info'),
        # ui/widgets/poisson_reference.py:53
        QCoreApplication.translate("CP2KStudio", 'Geometry: for Z periodicity, check the XY cross-section shape requirements; for XY periodicity, check the nonperiodic direction orthogonality.', 'poisson.note.analytic_geometry'),
        # ui/widgets/poisson_reference.py:54
        QCoreApplication.translate("CP2KStudio", 'Listed directions are reference orientations. The official 2026.1 description covers 0D, 1D and 2D generally; Studio retains its existing dimension-based validation.', 'poisson.note.analytic_scope'),
        # ui/widgets/poisson_reference.py:52
        QCoreApplication.translate("CP2KStudio", 'Size: nonperiodic cell lengths must accommodate the electron-density distribution.', 'poisson.note.analytic_size'),
        # ui/widgets/poisson_reference.py:68
        QCoreApplication.translate("CP2KStudio", 'ANY denotes 0D/1D/2D/3D coverage, not a value to write into the CP2K PERIODIC keyword.', 'poisson.note.implicit_any'),
        # ui/widgets/poisson_reference.py:67
        QCoreApplication.translate("CP2KStudio", 'Supported boundary conditions and grid requirements depend on the selected model and configuration.', 'poisson.note.implicit_model'),
        # ui/widgets/poisson_reference.py:47
        QCoreApplication.translate("CP2KStudio", 'Geometry: nonperiodic directions must satisfy the solver cell-orthogonality requirements.', 'poisson.note.mt_geometry'),
        # ui/widgets/poisson_reference.py:46
        QCoreApplication.translate("CP2KStudio", 'Size: nonperiodic cell lengths must accommodate the electron-density extent D; use L > 2D as a reference and check convergence.', 'poisson.note.mt_size'),
        # ui/widgets/poisson_reference.py:60
        QCoreApplication.translate("CP2KStudio", 'Applicability: intended for specific electrostatic boundary and QM periodic-image decoupling needs.', 'poisson.note.multipole_scope'),
        # ui/widgets/poisson_reference.py:59
        QCoreApplication.translate("CP2KStudio", 'Cell shape: use an orthogonal QM simulation box meeting the solver requirements.', 'poisson.note.multipole_shape'),
        # ui/widgets/poisson_reference.py:30
        QCoreApplication.translate("CP2KStudio", 'Suitable for 3D periodic cell optimization with a supported stress calculation.', 'poisson.note.periodic_cell'),
        # ui/widgets/poisson_reference.py:29
        QCoreApplication.translate("CP2KStudio", 'For asymmetric slabs, assess surface dipoles and whether dipole correction is appropriate.', 'poisson.note.periodic_dipole'),
        # ui/widgets/poisson_reference.py:69
        QCoreApplication.translate("CP2KStudio", 'Reference only: this solver is not available in the current Studio selector.', 'poisson.note.reference_only'),
        # ui/widgets/poisson_reference.py:37
        QCoreApplication.translate("CP2KStudio", 'Boundaries: electron density must decay sufficiently at nonperiodic faces. Test vacuum convergence; this can avoid unnecessarily large grids.', 'poisson.note.wavelet_density'),
        # ui/widgets/poisson_reference.py:39
        QCoreApplication.translate("CP2KStudio", 'FFT setting: PREFERRED_FFT_LIBRARY FFTSG is required.', 'poisson.note.wavelet_fft'),
        # ui/widgets/poisson_reference.py:38
        QCoreApplication.translate("CP2KStudio", 'FFT grid: sizes may be restricted by the implementation and factorization requirements.', 'poisson.note.wavelet_grid'),
        # ui/widgets/poisson_reference.py:36
        QCoreApplication.translate("CP2KStudio", 'Cell shape: NONE requires a cubic cell; XZ requires an orthogonal cell satisfying the solver geometry conditions.', 'poisson.note.wavelet_shape'),
        # ui/widgets/poisson_reference.py:149
        QCoreApplication.translate("CP2KStudio", '; ', 'poisson.separator'),
        # ui/main_window.py:227
        QCoreApplication.translate("CP2KStudio", 'Cell optimization', 'run_type.cell_opt'),
        # ui/main_window.py:225
        QCoreApplication.translate("CP2KStudio", 'Energy', 'run_type.energy'),
        # ui/main_window.py:226
        QCoreApplication.translate("CP2KStudio", 'Geometry optimization', 'run_type.geo_opt'),
        # ui/main_window.py:228
        QCoreApplication.translate("CP2KStudio", 'Ab initio molecular dynamics', 'run_type.md'),
        # ui/main_window.py:229
        QCoreApplication.translate("CP2KStudio", 'Vibration Analysis', 'run_type.vibrational'),
        # ui/scf_panel.py:66
        QCoreApplication.translate("CP2KStudio", 'Auto (-1.0)', 'scf.energy_gap_auto'),
        # ui/scf_panel.py:67
        QCoreApplication.translate("CP2KStudio", "ENERGY_GAP · OT Preconditioner Gap\n\nENERGY_GAP is an estimated electronic gap used by the OT preconditioner, in Hartree (Ha). It does not modify the physical band gap.\n\nRecommendations:\n• For wide-gap insulators or polymers, values around 0.08–0.1 Ha may be tested and compared with smaller values.\n• For small-gap systems, such as oxygen-deficient oxides, trying 0.2–0.5 Ha may help damp unstable SCF iterations.\n• With the FULL_ALL preconditioner, ENERGY_GAP should generally underestimate the actual HOMO–LUMO gap. Smaller values such as 0.001–0.002 Ha are also recommended in CP2K documentation.\n• Larger values do not guarantee faster convergence and may reduce preconditioning efficiency.\n• Auto uses CP2K's default behavior.\n\nCompare iteration counts, total runtime, and convergence stability.", 'scf.energy_gap_help'),
        # ui/scf_panel.py:61
        QCoreApplication.translate("CP2KStudio", 'MINIMIZER · OT Minimization Algorithm\n\nDIIS — Usually faster\n• Often converges faster for well-behaved systems.\n• More sensitive to the initial electronic structure and preconditioner.\n• Try CG if iterations oscillate or fail to converge.\n\nCG — Usually more robust\n• Conjugate gradients offer reliable convergence.\n• Suitable for difficult-to-converge systems.\n• May be slower than DIIS for some systems.\n\nRecommendation: Try DIIS first; switch to CG for persistent oscillations or convergence difficulties.', 'scf.minimizer_help'),
        # ui/forms.py:138
        QCoreApplication.translate("CP2KStudio", '{p0}: enter a finite real number or leave blank for Auto', 'scf.optional_number_error'),
        # core/comprehensive_check.py:34
        QCoreApplication.translate("CP2KStudio", 'Configuration Completeness', 'stage.configuration'),
        # core/comprehensive_check.py:34
        QCoreApplication.translate("CP2KStudio", 'External Dependencies', 'stage.dependencies'),
        # core/comprehensive_check.py:34
        QCoreApplication.translate("CP2KStudio", 'Runtime & Calculation Package', 'stage.runtime'),
        # core/comprehensive_check.py:34
        QCoreApplication.translate("CP2KStudio", 'XML Syntax Validation', 'stage.xml'),
        # core/structure.py:19
        QCoreApplication.translate("CP2KStudio", 'Supported Structures ({patterns});;{formats};;All Files (*)', 'structure.file_filter'),
        # ui/structure_panel.py:109
        QCoreApplication.translate("CP2KStudio", 'Import Structure （{formats}）', 'structure.import_button'),
        # ui/export_panel.py:106
        QCoreApplication.translate("CP2KStudio", 'Save Current Settings as Preset', 'studio.00738bccecb44c96'),
        # ui/structure_panel.py:443
        QCoreApplication.translate("CP2KStudio", 'Fixed fractional components: ', 'studio.007eaedd5c3ddb19'),
        # core/input_import.py:77
        QCoreApplication.translate("CP2KStudio", 'No supported cell parameters were provided; set the cell manually.', 'studio.00c6cdd3d906d9e1'),
        # ui/structure_view.py:309
        QCoreApplication.translate("CP2KStudio", 'Import a structure to view it', 'studio.017f4634c538a9dc'),
        # core/database_manager.py:166
        QCoreApplication.translate("CP2KStudio", 'Bundled Official Cache v2026.1', 'studio.01f0769d7b7f3af5'),
        # ui/main_window.py:371
        QCoreApplication.translate("CP2KStudio", 'The XML schema or a dependency changed. Run comprehensive validation again.', 'studio.0245b3f019b965c7'),
        # core/potential_database.py:42
        QCoreApplication.translate("CP2KStudio", 'Invalid NLCC count', 'studio.02d12ac7c5d99dfb'),
        # core/basis_database.py:23
        QCoreApplication.translate("CP2KStudio", 'Basis nset must be in 1..100', 'studio.02fe2d8bcf3b6864'),
        # ui/main_window.py:587
        QCoreApplication.translate("CP2KStudio", 'Import Structure', 'studio.0336447acd3a1674'),
        # core/atom_constraints.py:18
        QCoreApplication.translate("CP2KStudio", 'Coordinate range must be finite', 'studio.0406fe44a28c5977'),
        # core/comprehensive_check.py:103
        QCoreApplication.translate("CP2KStudio", 'Invalid configuration: {p0}. Correct the fields, data sources, or runtime settings.', 'studio.043ec2473d76cc4a'),
        # ui/preset_dialogs.py:48
        QCoreApplication.translate("CP2KStudio", 'Save reusable calculation parameters without changing the current project. Incomplete drafts are allowed but are not marked as CP2K XML-validated. KIND configurations must be matched to elements when applying.', 'studio.0485ecd6ae412f62'),
        # ui/database_dialog.py:46
        QCoreApplication.translate("CP2KStudio", 'Declare the version explicitly if no manifest or official fingerprint identifies it; this produces a Warning', 'studio.05a15885f61ad974'),
        # ui/xml_dialog.py:93
        QCoreApplication.translate("CP2KStudio", 'Select a custom XML file', 'studio.05f6d1958b9968bd'),
        # core/database_manager.py:144
        QCoreApplication.translate("CP2KStudio", 'File and version verified', 'studio.0633042e6cedc935'),
        # core/comprehensive_check.py:63
        QCoreApplication.translate("CP2KStudio", 'Errors: {p0}', 'studio.063abdaa463dea33'),
        # ui/main_window.py:621
        QCoreApplication.translate("CP2KStudio", '\nPreset Notes:\n', 'studio.06b3347c508bfe57'),
        # ui/structure_panel.py:421
        QCoreApplication.translate("CP2KStudio", 'Fixed: {p0} atoms · Selected: {p1} atoms', 'studio.06ef9262cb4ac576'),
        # ui/database_dialog.py:119
        QCoreApplication.translate("CP2KStudio", 'Fetch Failed; Existing Data Preserved', 'studio.0723847bee37d038'),
        # i18n/messages.py:93
        QCoreApplication.translate("CP2KStudio", '{p0}: {p1}', 'studio.07e3a63ea0ed5b58'),
        # core/presets.py:182
        QCoreApplication.translate("CP2KStudio", 'Basis, pseudopotential, and database sources', 'studio.082c13c38ebd1e32'),
        # ui/kind_panel.py:421
        QCoreApplication.translate("CP2KStudio", 'KIND {p0} is no longer in the current structure', 'studio.093c56cd9eb20622'),
        # i18n/messages.py:101
        QCoreApplication.translate("CP2KStudio", ', ', 'studio.0a07f659461970d8'),
        # ui/main_window.py:638
        QCoreApplication.translate("CP2KStudio", '\nThe current structure, coordinates, and cell will be preserved.', 'studio.0b0c5632b664f1fa'),
        # core/database_manager.py:174
        QCoreApplication.translate("CP2KStudio", 'Bundled Official', 'studio.0be64517931d478f'),
        # core/input_import.py:276
        QCoreApplication.translate("CP2KStudio", '{p1} for KIND {p0} could not be matched to the actual database. The original name was retained for review.', 'studio.0cd7ba7abccf55cf'),
        # ui/main_window.py:179
        QCoreApplication.translate("CP2KStudio", 'Open Water Example…', 'studio.0dc2da7d79a720cc'),
        # ui/main_window.py:131
        QCoreApplication.translate("CP2KStudio", 'New Project', 'studio.0e1a7040390fb03e'),
        # ui/kind_panel.py:381
        QCoreApplication.translate("CP2KStudio", '\nA q match is a specific consistency check, not a guarantee of physical applicability, accuracy, or convergence.', 'studio.0e8291844148fd26'),
        # ui/main_window.py:652
        QCoreApplication.translate("CP2KStudio", ' · Draft', 'studio.0efb1ee4ab8edf50'),
        # core/validator.py:99
        QCoreApplication.translate("CP2KStudio", 'Basis source', 'studio.0f2583faf419190a'),
        # core/models.py:28
        QCoreApplication.translate("CP2KStudio", 'Text fields cannot contain newlines or NUL characters', 'studio.0fe848c9c6c07ae3'),
        # core/kind_validator.py:133
        QCoreApplication.translate("CP2KStudio", 'A higher-priority basis with the same name shadows {p0}; adjust library order or exclude the conflict', 'studio.0ffce5de7709947b'),
        # ui/preset_dialogs.py:165
        QCoreApplication.translate("CP2KStudio", 'Included', 'studio.107319b8b39da106'),
        # ui/main_window.py:493
        QCoreApplication.translate("CP2KStudio", 'Running comprehensive validation…', 'studio.108b77566772f0c8'),
        # ui/run_environment_panel.py:43
        QCoreApplication.translate("CP2KStudio", 'Required Logical Cores', 'studio.10d9ce32248249c0'),
        # ui/recommendation_dialog.py:187
        QCoreApplication.translate("CP2KStudio", '{p0} / {p1}', 'studio.1110bdd690bab3e7'),
        # ui/recommendation_dialog.py:36
        QCoreApplication.translate("CP2KStudio", 'Not selected', 'studio.1182c5454f113db5'),
        # ui/validation_state.py:50
        QCoreApplication.translate("CP2KStudio", 'Configuration status does not certify numerical accuracy, physical applicability, or convergence.', 'studio.11860e89fffe2870'),
        # core/presets.py:212
        QCoreApplication.translate("CP2KStudio", 'Invalid preset identifier', 'studio.12860345cff0140d'),
        # core/validator.py:94
        QCoreApplication.translate("CP2KStudio", 'POISSON: select an electrostatic solver', 'studio.13030ba077c1e3af'),
        # ui/recommendation_dialog.py:68
        QCoreApplication.translate("CP2KStudio", 'KIND / Element', 'studio.133344485a0218af'),
        # core/comprehensive_check.py:166
        QCoreApplication.translate("CP2KStudio", 'Commands, input/output filenames, and runtime settings agree in run.sh and EXPORT_NOTES.txt. Local CP2K/MPI installation was not checked.', 'studio.13bf4fcd8a5f60cf'),
        # ui/main_window.py:634
        QCoreApplication.translate("CP2KStudio", 'Settings to update: ', 'studio.13fe698a1554dc96'),
        # ui/main_window.py:796
        QCoreApplication.translate("CP2KStudio", 'Expand the dependency details, or use “Open Export Folder” in step 08.', 'studio.148183c6f2305ffe'),
        # ui/preset_dialogs.py:126
        QCoreApplication.translate("CP2KStudio", 'Edit / Rename', 'studio.1512e1c6754ba3b8'),
        # ui/main_window.py:659
        QCoreApplication.translate("CP2KStudio", '{p0} preset files could not be read; review them in the manager', 'studio.1530fbb4606e0326'),
        # ui/main_window.py:826
        QCoreApplication.translate("CP2KStudio", 'Choose Parent Folder for the Calculation Package', 'studio.1541a806c8a607ba'),
        # ui/scf_panel.py:54
        QCoreApplication.translate("CP2KStudio", 'SCF Solver', 'studio.159e6116ca2c0cc5'),
        # ui/main_window.py:834
        QCoreApplication.translate("CP2KStudio", 'Enter a single folder name', 'studio.15aae2216543728f'),
        # core/comprehensive_check.py:134
        QCoreApplication.translate("CP2KStudio", '{p0}: XML validation service failed: {p1}. Check the schema and retry.', 'studio.16ee3017a83c1b3d'),
        # core/potential_database.py:48
        QCoreApplication.translate("CP2KStudio", 'Invalid NLCC data', 'studio.18242596dab6d48d'),
        # core/input_import.py:104
        QCoreApplication.translate("CP2KStudio", 'The Poisson solver is unspecified and remains unselected.', 'studio.182441fa5188c085'),
        # ui/main_window.py:152
        QCoreApplication.translate("CP2KStudio", 'XML Schema', 'studio.18f7c81abe3fb5c7'),
        # ui/preset_dialogs.py:33
        QCoreApplication.translate("CP2KStudio", 'Description (Optional)', 'studio.19ad97a6aca8b249'),
        # ui/kind_panel.py:294
        QCoreApplication.translate("CP2KStudio", 'KIND {p0}\nELEMENT {p1}', 'studio.1a13dd2c86ca9c1e'),
        # ui/main_window.py:794
        QCoreApplication.translate("CP2KStudio", 'Exported:\n{p0}\n\nXML syntax validation passed; no calculation was run.', 'studio.1a87117c3c3dc6ef'),
        # ui/main_window.py:567
        QCoreApplication.translate("CP2KStudio", 'Cannot Save Yet', 'studio.1a8735c6e13148f3'),
        # core/validator.py:108
        QCoreApplication.translate("CP2KStudio", '{p0}: path contains a newline or NUL', 'studio.1b3bfcdd6b793c22'),
        # core/kind_recommender.py:25
        QCoreApplication.translate("CP2KStudio", 'Conventional calculation candidate', 'studio.1b4eda0ff06a0337'),
        # ui/export_panel.py:125
        QCoreApplication.translate("CP2KStudio", 'Not validated yet · Live configuration: {p0} errors, {p1} warnings\nClick “Validate Configuration” to check these settings.', 'studio.1bf8fb13f5531f16'),
        # core/database_format.py:37
        QCoreApplication.translate("CP2KStudio", 'Database file exceeds 50 MB', 'studio.1c8a891c965af62d'),
        # ui/main_window.py:538
        QCoreApplication.translate("CP2KStudio", 'CP2K Studio (*.json);;All Files (*)', 'studio.1cba47f6efcec745'),
        # core/kind_recommender.py:29
        QCoreApplication.translate("CP2KStudio", '; matching q and XC names', 'studio.1d688d06aa785a69'),
        # ui/main_window.py:506
        QCoreApplication.translate("CP2KStudio", 'The validation service encountered an error.', 'studio.1d9d5a8ef86b170a'),
        # ui/main_window.py:245
        QCoreApplication.translate("CP2KStudio", 'Optimizer & Iteration Settings', 'studio.1e07f6cdf4c14689'),
        # ui/structure_panel.py:290
        QCoreApplication.translate("CP2KStudio", '{p0} atoms · {p1}\nSource: {p2}', 'studio.1e186b1b2fbae2a3'),
        # core/presets.py:63
        QCoreApplication.translate("CP2KStudio", 'Preset name cannot be empty', 'studio.1e396cf6fce01868'),
        # core/comprehensive_check.py:42
        QCoreApplication.translate("CP2KStudio", '[{p0}] {p1}', 'studio.1f1bfbba8910790c'),
        # ui/xml_dialog.py:72
        QCoreApplication.translate("CP2KStudio", 'Pending check; version and required Sections will be verified before confirmation.', 'studio.1f2af1396020a712'),
        # core/database_format.py:60
        QCoreApplication.translate("CP2KStudio", 'Expected an integer; got {p0}', 'studio.1f3e3ebf433c601b'),
        # ui/main_window.py:457
        QCoreApplication.translate("CP2KStudio", '! Configuration is incomplete or invalid; no runnable input was generated.\n! Valid draft settings can still be saved.\n\n', 'studio.1f73ff1dc17e0340'),
        # core/validator.py:56
        QCoreApplication.translate("CP2KStudio", 'KIND {p0}: basis or pseudopotential name is empty or contains invalid characters', 'studio.207ab9fea7e8c88c'),
        # core/input_import.py:83
        QCoreApplication.translate("CP2KStudio", 'Only embedded COORD or a single-frame XYZ reference is supported', 'studio.20ea6c884343dc6f'),
        # ui/run_environment_panel.py:36
        QCoreApplication.translate("CP2KStudio", 'OpenMP Threads per Process', 'studio.2151e9c4f0a07820'),
        # ui/forms.py:141
        QCoreApplication.translate("CP2KStudio", '{p0}: enter a valid number', 'studio.217fa2782cc1be44'),
        # core/input_import.py:30
        QCoreApplication.translate("CP2KStudio", 'Only parameters supported by the current model are imported. Arbitrary INP cannot be round-tripped completely; retain the original input.', 'studio.21fd24a8b764f0db'),
        # ui/structure_panel.py:155
        QCoreApplication.translate("CP2KStudio", 'Fix Selected', 'studio.22de130a828addda'),
        # core/basis_database.py:46
        QCoreApplication.translate("CP2KStudio", '{p0} {p1} contains an invalid element symbol; no correction was guessed and the entry was excluded', 'studio.22fa676214235406'),
        # core/input_export.py:32
        QCoreApplication.translate("CP2KStudio", 'INP filename conflicts with an automatically generated dependency', 'studio.238b96c601e33fdc'),
        # core/kind_validator.py:159
        QCoreApplication.translate("CP2KStudio", 'UZH protocol matching is not independently verified; matching q/XC names does not prove protocol compatibility', 'studio.23d5410b387d104b'),
        # core/validator.py:76
        QCoreApplication.translate("CP2KStudio", 'WAVELET sets FFTSG; electron density must approach zero at nonperiodic boundaries', 'studio.24d25b06c30f6626'),
        # ui/main_window.py:316
        QCoreApplication.translate("CP2KStudio", 'Coordinates in Å', 'studio.2511cb9a63dc70a0'),
        # ui/structure_view.py:349
        QCoreApplication.translate("CP2KStudio", ' · Previewing the first 3000 atoms', 'studio.2561994c2b497360'),
        # ui/export_panel.py:65
        QCoreApplication.translate("CP2KStudio", 'Current Configuration', 'studio.256efb657a687a83'),
        # ui/main_window.py:619
        QCoreApplication.translate("CP2KStudio", ' · Review unmatched elements and draft warnings', 'studio.2578ac877384dae9'),
        # core/bundle_checks.py:49
        QCoreApplication.translate("CP2KStudio", '{p0}: cannot read the final referenced database {p1}: {p2}. Reload the data file.', 'studio.26b75527fa69b987'),
        # ui/main_window.py:766
        QCoreApplication.translate("CP2KStudio", 'Overwrite {p0}?', 'studio.2746f204a01c802c'),
        # ui/main_window.py:210
        QCoreApplication.translate("CP2KStudio", 'Complete the configuration before exporting.', 'studio.2764c68b25e3bdb7'),
        # ui/preset_dialogs.py:194
        QCoreApplication.translate("CP2KStudio", 'Delete Preset', 'studio.28786d90697520ac'),
        # core/kind_validator.py:135
        QCoreApplication.translate("CP2KStudio", '{p0} has different contents under the same name; resolved using the recorded file / priority', 'studio.2968c01f2f57b28a'),
        # ui/xml_dialog.py:27
        QCoreApplication.translate("CP2KStudio", 'Browse File…', 'studio.29d75b8eb8866bb4'),
        # core/validator.py:106
        QCoreApplication.translate("CP2KStudio", '{p0}: path cannot be empty', 'studio.2a38ea9387d5b4d4'),
        # ui/preset_dialogs.py:147
        QCoreApplication.translate("CP2KStudio", ' · Draft / Incomplete', 'studio.2ab1ac70f0619483'),
        # core/kind_validator.py:161
        QCoreApplication.translate("CP2KStudio", 'UZH bases and non-UZH pseudopotentials cannot be treated as one protocol; select a matching source family or conventional library', 'studio.2b5bacc5adced7b1'),
        # ui/kind_panel.py:378
        QCoreApplication.translate("CP2KStudio", '! Review', 'studio.2c9b3c21bcd90fdd'),
        # ui/coordinate_range_dialog.py:36
        QCoreApplication.translate("CP2KStudio", 'Cancel', 'studio.2cd0f3be8738a86c'),
        # core/presets.py:71
        QCoreApplication.translate("CP2KStudio", 'Preset calculation parameters cannot implicitly include structure, XML, or project format settings', 'studio.2d7c76018b9d74f8'),
        # ui/database_dialog.py:101
        QCoreApplication.translate("CP2KStudio", 'Choose Custom CP2K Data Files', 'studio.2df9a7ae05bf73d1'),
        # ui/database_dialog.py:117
        QCoreApplication.translate("CP2KStudio", 'Get Official 2026.1 Data', 'studio.2e29276b7336ba30'),
        # core/input_import.py:252
        QCoreApplication.translate("CP2KStudio", 'Original OUTER_SCF EPS_SCF differs from the inner threshold. This interface uses one threshold; please review.', 'studio.2ec98c2c8463f644'),
        # core/file_references.py:89
        QCoreApplication.translate("CP2KStudio", 'The reference resolves outside the package', 'studio.2f7bb880fed4faa9'),
        # ui/preset_dialogs.py:127
        QCoreApplication.translate("CP2KStudio", 'Delete', 'studio.2f9daa828907b93f'),
        # core/structure.py:37
        QCoreApplication.translate("CP2KStudio", 'Only XSD, CIF, XYZ, and EXTXYZ files are supported', 'studio.304d6824d7aef772'),
        # ui/export_panel.py:34
        QCoreApplication.translate("CP2KStudio", 'Top Toolbar: XML Schema', 'studio.311def56f4616726'),
        # ui/structure_panel.py:479
        QCoreApplication.translate("CP2KStudio", 'Updated constraints for {p0} atoms', 'studio.31271b08f236be6b'),
        # ui/recommendation_dialog.py:112
        QCoreApplication.translate("CP2KStudio", 'Apply', 'studio.31e392d1c0378bec'),
        # ui/structure_panel.py:105
        QCoreApplication.translate("CP2KStudio", '01 · Structure & Cell', 'studio.32d69f2433650d2c'),
        # ui/main_window.py:202
        QCoreApplication.translate("CP2KStudio", '05  Basis Sets & Pseudopotentials', 'studio.32ebcdaa48de6986'),
        # ui/xml_dialog.py:44
        QCoreApplication.translate("CP2KStudio", 'Check Schema', 'studio.33a2c664588eb925'),
        # ui/main_window.py:810
        QCoreApplication.translate("CP2KStudio", 'Open Containing Folder', 'studio.348e2fde4e191226'),
        # ui/export_panel.py:122
        QCoreApplication.translate("CP2KStudio", '{p0} · {p1} atoms', 'studio.349e181aa4b43e79'),
        # ui/main_window.py:697
        QCoreApplication.translate("CP2KStudio", 'INP Import Complete', 'studio.34de73496924c727'),
        # ui/recommendation_dialog.py:153
        QCoreApplication.translate("CP2KStudio", 'background:{p0}; border:0;', 'studio.351655897d85b130'),
        # ui/export_panel.py:122
        QCoreApplication.translate("CP2KStudio", 'Structure Embedded in Project', 'studio.363f2b5862ff4102'),
        # core/comprehensive_check.py:158
        QCoreApplication.translate("CP2KStudio", 'Package: structure.xyz, basis and pseudopotential references are accessible and contain matching entries; INP paths are relative to the package.', 'studio.3664d2a34c19f65d'),
        # core/comprehensive_check.py:61
        QCoreApplication.translate("CP2KStudio", 'Validation Passed', 'studio.36f0f2f7ec0f4a31'),
        # core/validator.py:61
        QCoreApplication.translate("CP2KStudio", 'POISSON: the PERIODIC solver requires XYZ periodicity', 'studio.3816b7dab122782b'),
        # core/database_format.py:56
        QCoreApplication.translate("CP2KStudio", 'Expected {p0} integers; got {p1}', 'studio.38220f73ff20225b'),
        # ui/kind_panel.py:378
        QCoreApplication.translate("CP2KStudio", '○ Info', 'studio.38401e4efcf55c16'),
        # core/potential_database.py:105
        QCoreApplication.translate("CP2KStudio", 'Empty pseudopotential database', 'studio.3953f8adfa99e27a'),
        # core/basis_database.py:32
        QCoreApplication.translate("CP2KStudio", 'Invalid shell integer', 'studio.397b316fc975e621'),
        # ui/main_window.py:177
        QCoreApplication.translate("CP2KStudio", 'File', 'studio.39932f24fe11a6ba'),
        # ui/widgets/help_icon.py:38
        QCoreApplication.translate("CP2KStudio", 'QLabel#helpIcon {{ color:{p0}; font-size:16px; }}QToolTip {{ background:{p1}; color:{p2}; border:1px solid {p3}; border-radius:6px; padding:8px; max-width:360px; }}', 'studio.3a5bc72d0aacc0ce'),
        # ui/export_panel.py:129
        QCoreApplication.translate("CP2KStudio", '{p0} errors · Update: ', 'studio.3a963a308279d4d3'),
        # ui/dft_panel.py:42
        QCoreApplication.translate("CP2KStudio", 'Poisson & Periodicity', 'studio.3abb25ebb0073bc6'),
        # ui/structure_panel.py:294
        QCoreApplication.translate("CP2KStudio", 'No structure imported', 'studio.3b2ba961a7fc56f5'),
        # ui/database_dialog.py:80
        QCoreApplication.translate("CP2KStudio", 'Not read', 'studio.3b3307980018c0c4'),
        # ui/scf_panel.py:83
        QCoreApplication.translate("CP2KStudio", 'Mixing & Electronic Smearing', 'studio.3bef0599de223a3b'),
        # core/models.py:85
        QCoreApplication.translate("CP2KStudio", 'Element and coordinate counts differ', 'studio.3c7ff8799e4cbc68'),
        # ui/main_window.py:468
        QCoreApplication.translate("CP2KStudio", 'Configuration check passed.', 'studio.3c9e08a34715d9c1'),
        # ui/main_window.py:649
        QCoreApplication.translate("CP2KStudio", 'My Presets', 'studio.3cbfca23b6e20dd5'),
        # ui/xml_dialog.py:100
        QCoreApplication.translate("CP2KStudio", 'Load check passed · Version 2026.1 and required Sections confirmed', 'studio.3e08d2e223a47c6b'),
        # ui/main_window.py:667
        QCoreApplication.translate("CP2KStudio", 'Cannot Save Preset', 'studio.3e13d1a6b98cfbfd'),
        # core/kind_recommender.py:28
        QCoreApplication.translate("CP2KStudio", ' · Short-range SR form', 'studio.3e5521b4f03bc04f'),
        # ui/main_window.py:805
        QCoreApplication.translate("CP2KStudio", 'Export Complete', 'studio.3e6886d17a1cf43c'),
        # core/file_references.py:86
        QCoreApplication.translate("CP2KStudio", 'A complete package INP must use paths relative to the package', 'studio.3f502bfeae6d9c1a'),
        # core/kind_validator.py:149
        QCoreApplication.translate("CP2KStudio", 'XC label is unknown; functional compatibility cannot be confirmed automatically', 'studio.3f8e745f847d07f5'),
        # core/database_manager.py:168
        QCoreApplication.translate("CP2KStudio", 'User Custom File', 'studio.3fc5ddfcb4133a7c'),
        # core/validator.py:182
        QCoreApplication.translate("CP2KStudio", 'CP2K 2026.1 syntax validation failed: {p0}', 'studio.40df4cf19ae11085'),
        # ui/structure_panel.py:166
        QCoreApplication.translate("CP2KStudio", 'Clear All Fixed', 'studio.410a52677fd2675f'),
        # ui/structure_panel.py:154
        QCoreApplication.translate("CP2KStudio", 'Range selection uses true Cartesian XYZ coordinates (Å); selection does not fix atoms.\nCP2K 2026.1 FIXED_ATOMS fixes fractional components, which differ from Cartesian XYZ in nonorthogonal cells.\nCtrl/Cmd for multiple selection, Shift for a range. Row numbers follow the final INP order; sorting only changes the display.', 'studio.410e84884db83b24'),
        # ui/widgets/help_icon.py:36
        QCoreApplication.translate("CP2KStudio", 'Description', 'studio.4262c45dc797bb0c'),
        # ui/preset_dialogs.py:78
        QCoreApplication.translate("CP2KStudio", 'Overwrite Preset', 'studio.426c18d792670d65'),
        # ui/structure_panel.py:443
        QCoreApplication.translate("CP2KStudio", 'Not fixed', 'studio.42bf633a6e628976'),
        # core/basis_database.py:27
        QCoreApplication.translate("CP2KStudio", 'Missing basis shell dimensions', 'studio.42f4cac587132391'),
        # core/potential_database.py:67
        QCoreApplication.translate("CP2KStudio", 'Invalid projector count', 'studio.431548aa8316845d'),
        # core/potential_database.py:32
        QCoreApplication.translate("CP2KStudio", 'Local coefficient count mismatch', 'studio.43c2379e522c3233'),
        # ui/recommendation_dialog.py:236
        QCoreApplication.translate("CP2KStudio", 'Select a basis and pseudopotential combination first', 'studio.44d39f359c6c1821'),
        # core/validator.py:112
        QCoreApplication.translate("CP2KStudio", '{p0}: file does not exist or is not loaded: {p1}', 'studio.451fbcee836f91fc'),
        # ui/coordinate_range_dialog.py:27
        QCoreApplication.translate("CP2KStudio", 'Maximum (Å)', 'studio.458886e6f1789318'),
        # core/database_format.py:67
        QCoreApplication.translate("CP2KStudio", '{p0}: invalid entry header {p1}', 'studio.45be267617669551'),
        # ui/main_window.py:830
        QCoreApplication.translate("CP2KStudio", 'ZIP filename (must not already exist):', 'studio.45f313de6bac191c'),
        # core/comprehensive_check.py:57
        QCoreApplication.translate("CP2KStudio", 'Warning · ', 'studio.45f51b987466bddc'),
        # ui/xml_dialog.py:20
        QCoreApplication.translate("CP2KStudio", 'Use Verified Custom XML', 'studio.47275797813649bf'),
        # core/comprehensive_check.py:146
        QCoreApplication.translate("CP2KStudio", 'CP2K 2026.1 XML validation passed; the final INP generated from this configuration was checked.', 'studio.47d98214973e699a'),
        # ui/recommendation_dialog.py:40
        QCoreApplication.translate("CP2KStudio", 'color:{p0};', 'studio.483b2b6509af7049'),
        # ui/kind_panel.py:210
        QCoreApplication.translate("CP2KStudio", ' records; open Database Manager for paths, fingerprints, and excluded records.', 'studio.4895fbbdbf0865a7'),
        # ui/kind_panel.py:142
        QCoreApplication.translate("CP2KStudio", 'Database Files', 'studio.48f7454669e02185'),
        # core/input_import.py:48
        QCoreApplication.translate("CP2KStudio", 'The functional is unspecified or unsupported and remains unselected.', 'studio.494adeb521acb130'),
        # ui/kind_panel.py:145
        QCoreApplication.translate("CP2KStudio", 'Recommend…', 'studio.495427d709e4ee6a'),
        # ui/main_window.py:184
        QCoreApplication.translate("CP2KStudio", 'Quit', 'studio.498e1d59b4d787ee'),
        # ui/xml_dialog.py:16
        QCoreApplication.translate("CP2KStudio", 'CP2K 2026.1 · XML Schema', 'studio.49e19bfec4131089'),
        # ui/preset_dialogs.py:114
        QCoreApplication.translate("CP2KStudio", 'Preset folder: {p0}\nBuilt-in presets remain in the top menu; manage personal presets here.', 'studio.4a00046ddba45a08'),
        # ui/main_window.py:807
        QCoreApplication.translate("CP2KStudio", 'Exported:\n{p0}', 'studio.4a1fb92e018434dd'),
        # core/basis_database.py:72
        QCoreApplication.translate("CP2KStudio", 'Empty basis database', 'studio.4a38a45d40d4dab3'),
        # ui/preset_dialogs.py:79
        QCoreApplication.translate("CP2KStudio", 'Save with Another Name', 'studio.4a9f59c187d30c3d'),
        # ui/dft_panel.py:29
        QCoreApplication.translate("CP2KStudio", 'DFT Method & XC Functional', 'studio.4bb93242a34a7d81'),
        # ui/xml_dialog.py:79
        QCoreApplication.translate("CP2KStudio", 'Choose CP2K 2026.1 XML', 'studio.4bf4e106ebc7d18d'),
        # core/database_format.py:69
        QCoreApplication.translate("CP2KStudio", 'Invalid database name: {p0}', 'studio.4cb29e23744e7efd'),
        # core/database_manager.py:135
        QCoreApplication.translate("CP2KStudio", 'Unknown', 'studio.4d8c1c5b42830791'),
        # core/database_manager.py:199
        QCoreApplication.translate("CP2KStudio", 'The bundled official version manifest is unavailable; download version cannot be verified', 'studio.4dda470a0496a2c3'),
        # core/potential_database.py:18
        QCoreApplication.translate("CP2KStudio", '{p0} {p1} is marked NA, unavailable, and excluded', 'studio.4df4ef0ad0087f73'),
        # ui/preset_dialogs.py:24
        QCoreApplication.translate("CP2KStudio", 'Edit Preset', 'studio.4e32d8dbf1bef946'),
        # core/kind_validator.py:128
        QCoreApplication.translate("CP2KStudio", 'The entry contents for {p0} changed', 'studio.4e7e13f5909ec162'),
        # ui/preset_dialogs.py:10
        QCoreApplication.translate("CP2KStudio", 'Custom', 'studio.4eafa9e925b30bcd'),
        # ui/main_window.py:609
        QCoreApplication.translate("CP2KStudio", 'Cannot Apply Preset', 'studio.4f2cdc9031872d17'),
        # core/kind_validator.py:147
        QCoreApplication.translate("CP2KStudio", 'Pseudopotential XC={p0} differs from the current functional {p1}; please review', 'studio.4f5014984d8ce4ea'),
        # core/database_manager.py:144
        QCoreApplication.translate("CP2KStudio", 'User-declared version; not certified as official data', 'studio.4f59e1eb8a7cbb90'),
        # ui/main_window.py:381
        QCoreApplication.translate("CP2KStudio", 'Parameters changed; validation is out of date. Click “Validate Configuration” again.', 'studio.508380ae2a94a6f3'),
        # ui/run_environment_panel.py:35
        QCoreApplication.translate("CP2KStudio", 'MPI Processes', 'studio.50867c721b9898fe'),
        # core/presets.py:103
        QCoreApplication.translate("CP2KStudio", 'Single-Point Preset', 'studio.5091f86f26dfeeeb'),
        # core/kind_recommender.py:26
        QCoreApplication.translate("CP2KStudio", 'Available basis candidate', 'studio.50ad4c65aeb99ac1'),
        # ui/kind_panel.py:440
        QCoreApplication.translate("CP2KStudio", 'A recommended source file is missing, changed, or has an invalid version. Reload the database.', 'studio.50ba1a15709f090b'),
        # ui/export_panel.py:93
        QCoreApplication.translate("CP2KStudio", 'Export .inp File', 'studio.50e54d4173bdb499'),
        # ui/preset_dialogs.py:39
        QCoreApplication.translate("CP2KStudio", 'Category', 'studio.515559957fd3acbd'),
        # ui/dft_panel.py:17
        QCoreApplication.translate("CP2KStudio", 'Spin-polarized UKS', 'studio.52358a7cb44c6b1a'),
        # core/input_import.py:106
        QCoreApplication.translate("CP2KStudio", 'CELL and POISSON periodicity differ; lossless import is not possible', 'studio.523e3e64258fca21'),
        # ui/database_dialog.py:45
        QCoreApplication.translate("CP2KStudio", 'Not declared', 'studio.524a0bd8be900fcf'),
        # core/presets.py:191
        QCoreApplication.translate("CP2KStudio", 'Cell & Periodicity', 'studio.5261b980378d173d'),
        # core/presets.py:237
        QCoreApplication.translate("CP2KStudio", 'Preset filename does not match its identifier', 'studio.52944b7bcb075369'),
        # ui/main_window.py:178
        QCoreApplication.translate("CP2KStudio", 'Save Project As…', 'studio.52aefded530dd2ec'),
        # core/comprehensive_check.py:56
        QCoreApplication.translate("CP2KStudio", 'Error · ', 'studio.52d4395a320bcf3c'),
        # core/comprehensive_check.py:144
        QCoreApplication.translate("CP2KStudio", 'Standalone INP', 'studio.5328fbb43263806e'),
        # ui/preset_dialogs.py:41
        QCoreApplication.translate("CP2KStudio", 'Include cell and periodicity (confirmation required when applying)', 'studio.538cc19f2f73dc92'),
        # ui/kind_panel.py:153
        QCoreApplication.translate("CP2KStudio", 'Quality', 'studio.55847d2e5bed2ac5'),
        # core/presets.py:183
        QCoreApplication.translate("CP2KStudio", 'Geometry Optimization', 'studio.5688511fca2c8507'),
        # ui/main_window.py:202
        QCoreApplication.translate("CP2KStudio", '07  Runtime Settings', 'studio.56aa9cc7f7010ba2'),
        # core/file_references.py:37
        QCoreApplication.translate("CP2KStudio", '{p0}: path cannot be safely written directly into CP2K INP: {p1!r}. Export a complete package to normalize filenames, or rename the source file first.', 'studio.56ceeae123ffa617'),
        # ui/recommendation_dialog.py:242
        QCoreApplication.translate("CP2KStudio", 'Application failed: {p0}', 'studio.570e9d8af11fa767'),
        # ui/main_window.py:641
        QCoreApplication.translate("CP2KStudio", 'Apply Preset', 'studio.57a1cd214175a24d'),
        # core/presets.py:105
        QCoreApplication.translate("CP2KStudio", 'Unknown built-in preset: {p0}', 'studio.585d3ad95c8aa494'),
        # ui/kind_panel.py:456
        QCoreApplication.translate("CP2KStudio", 'The current project has invalid draft parameters; the recommendation was not committed. Correct them and retry.', 'studio.58c28c6010cc6251'),
        # core/run_config.py:29
        QCoreApplication.translate("CP2KStudio", 'Hybrid MPI + OpenMP', 'studio.592b04c989251f53'),
        # ui/export_panel.py:88
        QCoreApplication.translate("CP2KStudio", 'Export Calculation Package…', 'studio.5a2a8c4abb373954'),
        # core/database_format.py:122
        QCoreApplication.translate("CP2KStudio", '{p0} {p1}: name q value conflicts with the data', 'studio.5abfd053fae4e2db'),
        # core/presets.py:54
        QCoreApplication.translate("CP2KStudio", 'Description cannot contain NUL characters', 'studio.5b1f33296bb9dd40'),
        # ui/validation_state.py:17
        QCoreApplication.translate("CP2KStudio", 'ENERGY does not require geometry optimization', 'studio.5b89963a22120553'),
        # core/schema.py:17
        QCoreApplication.translate("CP2KStudio", 'CP2K 2026.1 XML is required; found {p0}', 'studio.5b9edbd269dba7f4'),
        # ui/export_panel.py:46
        QCoreApplication.translate("CP2KStudio", '06 Geometry Optimization', 'studio.5bf6471ffb2ae052'),
        # ui/coordinate_range_dialog.py:23
        QCoreApplication.translate("CP2KStudio", 'e.g. -3.0 or -3e0', 'studio.5c4739d3a58813d6'),
        # ui/main_window.py:785
        QCoreApplication.translate("CP2KStudio", 'Exported: {p0}', 'studio.5c7ef7224c1de956'),
        # core/file_references.py:93
        QCoreApplication.translate("CP2KStudio", '{p0}: dependency is inaccessible: {p1!r} (working directory {p2}): {p3}', 'studio.5c8624e46e9af3fd'),
        # ui/kind_panel.py:378
        QCoreApplication.translate("CP2KStudio", '✓ q={p0} matched', 'studio.5d391c3fa733b5fd'),
        # ui/main_window.py:469
        QCoreApplication.translate("CP2KStudio", 'Project Migration · ', 'studio.5d5ede6dd286d2f1'),
        # core/comprehensive_check.py:159
        QCoreApplication.translate("CP2KStudio", 'Standalone INP: coordinates are embedded; external basis/pseudopotential sources must remain accessible in the target environment. Merged files are generated alongside the INP.', 'studio.5f2292b560c08716'),
        # ui/export_panel.py:101
        QCoreApplication.translate("CP2KStudio", 'Packages include run.sh; run "bash run.sh" in the target terminal. Standalone INP export does not generate a script.', 'studio.5f2c3726cf5a68f8'),
        # ui/main_window.py:871
        QCoreApplication.translate("CP2KStudio", 'Background Task Still Running', 'studio.5f55a8a20e03c950'),
        # ui/preset_dialogs.py:165
        QCoreApplication.translate("CP2KStudio", 'Excluded', 'studio.5f60ffcf600ae19c'),
        # ui/preset_dialogs.py:30
        QCoreApplication.translate("CP2KStudio", 'Preset Name', 'studio.5fe110aa6d1dca31'),
        # core/validator.py:69
        QCoreApplication.translate("CP2KStudio", 'POISSON: WAVELET supports only NONE, XZ, or XYZ periodicity', 'studio.5fe7a7185adbc017'),
        # core/run_config.py:29
        QCoreApplication.translate("CP2KStudio", 'Pure MPI', 'studio.6076939a7e3a7b0d'),
        # ui/structure_panel.py:160
        QCoreApplication.translate("CP2KStudio", 'CP2K fixes fractional components; these are independent of the Cartesian range-selection axis', 'studio.60cfdbf4c58a0226'),
        # ui/forms.py:64
        QCoreApplication.translate("CP2KStudio", '— Select explicitly —', 'studio.621cb18802e2551d'),
        # core/presets.py:193
        QCoreApplication.translate("CP2KStudio", 'Atomic structure and coordinates (explicitly included in preset)', 'studio.624c007a881b5b2d'),
        # ui/preset_dialogs.py:10
        QCoreApplication.translate("CP2KStudio", 'Single Point', 'studio.6257cf612978bdc4'),
        # ui/export_panel.py:36
        QCoreApplication.translate("CP2KStudio", '05 Basis Sets & Pseudopotentials', 'studio.6275eb51c31a24d4'),
        # core/basis_database.py:60
        QCoreApplication.translate("CP2KStudio", 'No valid basis entry header found', 'studio.628c4b18903c763a'),
        # ui/main_window.py:524
        QCoreApplication.translate("CP2KStudio", 'Save the current changes?', 'studio.62b2bd3c00c5214c'),
        # ui/main_window.py:583
        QCoreApplication.translate("CP2KStudio", 'Save Failed', 'studio.6309a3bb5ba4c714'),
        # ui/kind_panel.py:181
        QCoreApplication.translate("CP2KStudio", 'Status', 'studio.6320b4a8722a851f'),
        # ui/main_window.py:524
        QCoreApplication.translate("CP2KStudio", 'Unsaved Project', 'studio.635a265f503379b5'),
        # ui/xml_dialog.py:19
        QCoreApplication.translate("CP2KStudio", 'Use Bundled CP2K 2026.1 XML', 'studio.63fe2caa9ad240e6'),
        # ui/coordinate_range_dialog.py:26
        QCoreApplication.translate("CP2KStudio", 'Minimum (Å)', 'studio.645720ed6b2e7056'),
        # ui/main_window.py:580
        QCoreApplication.translate("CP2KStudio", 'Project saved: {p0}', 'studio.646961ecbf06c5b6'),
        # ui/run_environment_panel.py:20
        QCoreApplication.translate("CP2KStudio", 'Target Operating System', 'studio.647b20d8b66de930'),
        # ui/coordinate_range_dialog.py:14
        QCoreApplication.translate("CP2KStudio", 'Select Atoms by Coordinate Range', 'studio.6486ad9312cad7fc'),
        # ui/run_environment_panel.py:92
        QCoreApplication.translate("CP2KStudio", 'run_environment: {p0}', 'studio.649058b14d12527e'),
        # ui/xml_dialog.py:39
        QCoreApplication.translate("CP2KStudio", 'Schema Version', 'studio.64f58bcd239b5eb0'),
        # ui/kind_panel.py:223
        QCoreApplication.translate("CP2KStudio", 'All Qualities', 'studio.65b0f156dcafd4b4'),
        # ui/preset_dialogs.py:42
        QCoreApplication.translate("CP2KStudio", 'Include coordinates (excluded by default; confirmation required when applying)', 'studio.675ed6a577012d59'),
        # core/models.py:93
        QCoreApplication.translate("CP2KStudio", 'Fixed atom IDs are duplicated or absent from the current structure', 'studio.69538b36b7981e5e'),
        # ui/export_panel.py:62
        QCoreApplication.translate("CP2KStudio", '08 · Export & Presets', 'studio.69883ef520401d5a'),
        # ui/validation_state.py:16
        QCoreApplication.translate("CP2KStudio", 'Nonblocking warnings are present', 'studio.69a081b6e4703570'),
        # core/validator.py:145
        QCoreApplication.translate("CP2KStudio", 'DFT: CHARGE, MULTIPLICITY, and pseudopotential valence electron count have inconsistent parity or counts', 'studio.69cda7083d3901ba'),
        # ui/recommendation_dialog.py:52
        QCoreApplication.translate("CP2KStudio", 'Only existing conventional GPW/GTH entries with matching q/XC names are shown. UZH has no independently verified protocol here and is not recommended automatically.\nSelect a row and click Apply to update that KIND only. Recommendations do not guarantee accuracy or convergence.', 'studio.6a72d7d9c8263001'),
        # core/structure.py:49
        QCoreApplication.translate("CP2KStudio", 'Partial or mixed CIF occupancies are not supported; construct an explicit ordered structure first', 'studio.6ab570a20987cc3f'),
        # core/bundle_checks.py:83
        QCoreApplication.translate("CP2KStudio", 'RUN_ENVIRONMENT: the package is missing input.inp, which run.sh requires. Export again.', 'studio.6ae9a6ba2db87959'),
        # ui/main_window.py:743
        QCoreApplication.translate("CP2KStudio", 'Wait for validation or export to finish', 'studio.6b5ab7f8d1d55dc6'),
        # core/input_import.py:85
        QCoreApplication.translate("CP2KStudio", 'A complete, single-frame XYZ is required', 'studio.6b97eaae2619df54'),
        # core/potential_database.py:103
        QCoreApplication.translate("CP2KStudio", '{p0}: corrupt entry excluded: {p1}', 'studio.6bf80154d34da2de'),
        # core/input_import.py:91
        QCoreApplication.translate("CP2KStudio", 'Missing ELEMENT definition for KIND {p0}', 'studio.6c4e221b785ed522'),
        # ui/export_panel.py:107
        QCoreApplication.translate("CP2KStudio", 'Save current DFT, SCF, basis, optimization, and related settings for reuse. Cell and coordinates are excluded by default; incomplete drafts are marked accordingly.', 'studio.6c9eacd0d1efad66'),
        # core/file_references.py:27
        QCoreApplication.translate("CP2KStudio", 'No file-keyword serialization rule is defined for {p0}', 'studio.6cba4fab0637f991'),
        # ui/structure_view.py:345
        QCoreApplication.translate("CP2KStudio", '{p0} atoms · {p1}', 'studio.6d5c69da8964adc1'),
        # ui/database_dialog.py:40
        QCoreApplication.translate("CP2KStudio", 'CP2K data folder (leave empty for local discovery and the official cache)', 'studio.6d7dd1c1cd1e8add'),
        # ui/preset_dialogs.py:167
        QCoreApplication.translate("CP2KStudio", 'No personal presets yet. Save the current settings in step 08.', 'studio.6dbb6181b426442d'),
        # ui/structure_panel.py:153
        QCoreApplication.translate("CP2KStudio", 'Atomic Coordinates', 'studio.6dc715068235b1cd'),
        # core/bundle_checks.py:85
        QCoreApplication.translate("CP2KStudio", 'RUN_ENVIRONMENT: run.sh does not switch to the package directory; relative dependency paths cannot be guaranteed.', 'studio.6dcd8a964ebedc04'),
        # ui/main_window.py:843
        QCoreApplication.translate("CP2KStudio", 'Export Failed', 'studio.6e4445df69575d79'),
        # ui/main_window.py:223
        QCoreApplication.translate("CP2KStudio", 'Calculation Task', 'studio.6f4d044498527dbe'),
        # ui/export_panel.py:86
        QCoreApplication.translate("CP2KStudio", 'Generate input for CP2K. Standalone INP uses the same generator as the preview; export a calculation package when moving to another computing environment.\n\nCoordinates are embedded in standalone INP; basis and pseudopotential dependencies must remain accessible. Multiple pseudopotential sources produce the required merged file.', 'studio.700fe78d70968dbd'),
        # core/potential_database.py:30
        QCoreApplication.translate("CP2KStudio", 'Invalid local coefficient count', 'studio.7100309caf64f3c6'),
        # core/comprehensive_check.py:64
        QCoreApplication.translate("CP2KStudio", 'No CP2K calculation was run. Static checks and XML syntax validation do not guarantee physical applicability or SCF convergence.', 'studio.712969f113692e34'),
        # ui/main_window.py:145
        QCoreApplication.translate("CP2KStudio", 'Presets', 'studio.71d67829caf43b18'),
        # ui/preset_dialogs.py:111
        QCoreApplication.translate("CP2KStudio", 'Manage My Presets', 'studio.72b4a4fb714a4398'),
        # ui/validation_state.py:48
        QCoreApplication.translate("CP2KStudio", '\nNot validated yet, or configuration changed. Click “Validate Configuration” in step 08.\n', 'studio.73decc9a48e4a1b5'),
        # ui/main_window.py:314
        QCoreApplication.translate("CP2KStudio", 'Validation Report', 'studio.73ded52ed89ccae6'),
        # core/database_manager.py:161
        QCoreApplication.translate("CP2KStudio", 'User-Specified Folder', 'studio.73fc5c2ef0ef34eb'),
        # ui/main_window.py:829
        QCoreApplication.translate("CP2KStudio", 'Export Calculation Package', 'studio.74a1fb3c37f0f2a1'),
        # core/database_format.py:131
        QCoreApplication.translate("CP2KStudio", 'Cannot confirm automatically', 'studio.76835fdb33c70096'),
        # core/validator.py:63
        QCoreApplication.translate("CP2KStudio", 'POISSON: MT supports only 0D or 2D systems', 'studio.76ff8199fee0aa41'),
        # ui/run_environment_panel.py:38
        QCoreApplication.translate("CP2KStudio", 'Logical Execution Slots', 'studio.77f1e559989ef41f'),
        # core/models.py:90
        QCoreApplication.translate("CP2KStudio", 'Atom IDs must be unique positive integers corresponding to this structure', 'studio.78d4e2923e2ab09d'),
        # ui/coordinate_range_dialog.py:24
        QCoreApplication.translate("CP2KStudio", 'e.g. 8.0', 'studio.797152927a6b5fcf'),
        # ui/structure_panel.py:468
        QCoreApplication.translate("CP2KStudio", 'Constraints are unchanged', 'studio.797db3bfa2fecd61'),
        # ui/main_window.py:122
        QCoreApplication.translate("CP2KStudio", 'Project Files', 'studio.79f326be4409d51f'),
        # ui/xml_dialog.py:38
        QCoreApplication.translate("CP2KStudio", 'XML File', 'studio.7a58742e7c1d52c3'),
        # core/database_format.py:29
        QCoreApplication.translate("CP2KStudio", 'Invalid numeric value: {p0}', 'studio.7af3fb33081efbc3'),
        # ui/main_window.py:822
        QCoreApplication.translate("CP2KStudio", 'Calculation Package Format', 'studio.7c2aa04c4bc126ea'),
        # core/validator.py:51
        QCoreApplication.translate("CP2KStudio", 'CELL: provide three independent right-handed cell vectors (a box is also required for nonperiodic systems)', 'studio.7c4841cad4d6ad33'),
        # ui/main_window.py:822
        QCoreApplication.translate("CP2KStudio", 'Folder', 'studio.7c7802d8adaed72e'),
        # ui/kind_panel.py:197
        QCoreApplication.translate("CP2KStudio", 'Add Custom Pseudopotential…', 'studio.7c9068cfbaf9b93c'),
        # ui/main_window.py:513
        QCoreApplication.translate("CP2KStudio", 'Validation finished · {p0} errors · {p1} warnings; no calculation was run', 'studio.7cf761111bf3b957'),
        # ui/recommendation_dialog.py:133
        QCoreApplication.translate("CP2KStudio", 'Configured {p0}/{p1} elements', 'studio.7d2db2a6398bc21a'),
        # core/potential_database.py:63
        QCoreApplication.translate("CP2KStudio", 'Negative nonlocal radius', 'studio.7d5697d7e1c282c3'),
        # ui/kind_panel.py:156
        QCoreApplication.translate("CP2KStudio", 'All XC', 'studio.7d86678c5d4dfa0d'),
        # ui/recommendation_dialog.py:113
        QCoreApplication.translate("CP2KStudio", 'Close', 'studio.7d9eb7acb13e2462'),
        # core/bundle_checks.py:74
        QCoreApplication.translate("CP2KStudio", 'RUN_ENVIRONMENT: the command in EXPORT_NOTES.txt differs from run.sh or the current configuration. Regenerate the package.', 'studio.7da13f14652b3504'),
        # ui/export_panel.py:120
        QCoreApplication.translate("CP2KStudio", 'Target system: {p0}\nMPI processes: {p1}    OpenMP threads: {p2}\nRequired logical cores: {p3} · {p4}', 'studio.7e8f59aa8196df78'),
        # core/bundle_checks.py:87
        QCoreApplication.translate("CP2KStudio", 'RUN_ENVIRONMENT: required logical cores do not equal MPI × OpenMP.', 'studio.7f70374bc3179a09'),
        # core/validator.py:110
        QCoreApplication.translate("CP2KStudio", 'Basis Set', 'studio.810ecb3582cd0af1'),
        # core/models.py:100
        QCoreApplication.translate("CP2KStudio", 'Invalid atom KIND label', 'studio.8111a7b668ccfcbc'),
        # ui/xml_dialog.py:97
        QCoreApplication.translate("CP2KStudio", 'Bundled Official Schema', 'studio.81c441462ada0138'),
        # ui/scf_panel.py:51
        QCoreApplication.translate("CP2KStudio", 'Enable OUTER_SCF', 'studio.81e0db11b47de9f6'),
        # ui/main_window.py:822
        QCoreApplication.translate("CP2KStudio", 'Export as:', 'studio.81eadc7355d0cf3b'),
        # core/potential_database.py:38
        QCoreApplication.translate("CP2KStudio", 'Invalid NLCC header', 'studio.82c59442534eca99'),
        # ui/kind_panel.py:209
        QCoreApplication.translate("CP2KStudio", 'Loaded: ', 'studio.83948700a8b72d85'),
        # core/validator.py:58
        QCoreApplication.translate("CP2KStudio", 'KINDs absent from the current structure will not be exported', 'studio.83f827f106c66d59'),
        # core/runner.py:6
        QCoreApplication.translate("CP2KStudio", 'This version does not execute CP2K; export the input and run it in the target environment', 'studio.84bf2369949d367f'),
        # ui/structure_panel.py:411
        QCoreApplication.translate("CP2KStudio", 'SUBSYS: cell or coordinates contain invalid numbers', 'studio.84bfbc9f8ff5db0e'),
        # core/models.py:178
        QCoreApplication.translate("CP2KStudio", 'ELEMENT must be a real element', 'studio.8513a8530df01c40'),
        # core/atom_constraints.py:12
        QCoreApplication.translate("CP2KStudio", 'Coordinate axis must be X, Y, or Z', 'studio.8537e7a03aeab99a'),
        # ui/database_dialog.py:54
        QCoreApplication.translate("CP2KStudio", 'Entries', 'studio.860082f1436f1ecc'),
        # core/comprehensive_check.py:156
        QCoreApplication.translate("CP2KStudio", 'Final input.inp or a dependency cannot be read: {p0}. Check the files and export again.', 'studio.864d370fa15ec908'),
        # core/kind_validator.py:118
        QCoreApplication.translate("CP2KStudio", '{p0} was not found in the loaded {p1} database for this element, or its source is missing / has an unknown version', 'studio.864dee99194af37a'),
        # ui/main_window.py:222
        QCoreApplication.translate("CP2KStudio", 'Project Name', 'studio.867698fb7b0c730c'),
        # core/comprehensive_check.py:113
        QCoreApplication.translate("CP2KStudio", 'XML schema is unavailable; no temporary calculation package was prepared.', 'studio.868e9f33b470b4b5'),
        # ui/main_window.py:462
        QCoreApplication.translate("CP2KStudio", 'CP2K Studio · {p0}', 'studio.869fbe4b5d604047'),
        # ui/run_environment_panel.py:25
        QCoreApplication.translate("CP2KStudio", 'MPI / OpenMP Settings', 'studio.87218a622e2c2621'),
        # ui/export_panel.py:96
        QCoreApplication.translate("CP2KStudio", 'Open Export Folder', 'studio.8863740eb2039729'),
        # ui/main_window.py:180
        QCoreApplication.translate("CP2KStudio", 'Import Existing INP…', 'studio.890b0f9253480355'),
        # ui/main_window.py:699
        QCoreApplication.translate("CP2KStudio", 'INP Import Failed', 'studio.8a5efa5b228fa0cb'),
        # ui/structure_panel.py:450
        QCoreApplication.translate("CP2KStudio", 'Correct invalid cell or coordinate values first', 'studio.8ab436fd945cf042'),
        # ui/kind_panel.py:402
        QCoreApplication.translate("CP2KStudio", 'Explicitly Add CP2K 2026.1 Data (User-Declared Version)', 'studio.8ad5f0067f16f480'),
        # ui/preset_dialogs.py:165
        QCoreApplication.translate("CP2KStudio", 'No description', 'studio.8ae96d747e59609e'),
        # core/input_import.py:97
        QCoreApplication.translate("CP2KStudio", 'This coordinate unit is not supported', 'studio.8b4f1dc706a99bcc'),
        # ui/structure_view.py:106
        QCoreApplication.translate("CP2KStudio", 'No valid cell {p0} vector was provided', 'studio.8b611d6013de8616'),
        # ui/preset_dialogs.py:127
        QCoreApplication.translate("CP2KStudio", 'Update from Current Configuration', 'studio.8b73328b3869ac77'),
        # core/atom_constraints.py:32
        QCoreApplication.translate("CP2KStudio", 'Selected atoms are no longer in the current structure; select them again', 'studio.8b9d8370a584c569'),
        # ui/main_window.py:165
        QCoreApplication.translate("CP2KStudio", 'Language:', 'studio.8c16819a2bd49b95'),
        # core/comprehensive_check.py:140
        QCoreApplication.translate("CP2KStudio", 'Standalone INP cannot safely represent the source path: {p0}. Use the package with normalized paths.', 'studio.8c66fadfa9f5f384'),
        # core/presets.py:234
        QCoreApplication.translate("CP2KStudio", 'Preset file exceeds 100 MB', 'studio.8ca34bc2eb1ba4ff'),
        # core/potential_database.py:25
        QCoreApplication.translate("CP2KStudio", 'Missing pseudopotential local term', 'studio.8cf1509d71824172'),
        # ui/main_window.py:554
        QCoreApplication.translate("CP2KStudio", 'Cannot Open Project', 'studio.8cf36a6b4cf16b94'),
        # ui/kind_panel.py:321
        QCoreApplication.translate("CP2KStudio", 'The current selection does not match these filters and has been preserved. Filtering never changes the configuration.\n', 'studio.8d52f428a7b4d0d5'),
        # ui/preset_dialogs.py:126
        QCoreApplication.translate("CP2KStudio", 'Load', 'studio.8f8f907784631b04'),
        # ui/main_window.py:751
        QCoreApplication.translate("CP2KStudio", 'Comprehensive Validation Failed', 'studio.8fa92f9e2d4d76e9'),
        # ui/structure_panel.py:291
        QCoreApplication.translate("CP2KStudio", 'Structure stored in the project configuration', 'studio.8fe24b751141071f'),
        # ui/structure_panel.py:460
        QCoreApplication.translate("CP2KStudio", 'Select atoms first', 'studio.904b699d134086dc'),
        # core/models.py:104
        QCoreApplication.translate("CP2KStudio", 'One KIND label cannot refer to different elements', 'studio.90f6280efb0dea6e'),
        # ui/xml_dialog.py:105
        QCoreApplication.translate("CP2KStudio", 'Load failed: {p0}', 'studio.91df1b36811ee28b'),
        # ui/xml_dialog.py:12
        QCoreApplication.translate("CP2KStudio", 'XML Schema · CP2K 2026.1', 'studio.9219baf48a5d736a'),
        # ui/preset_dialogs.py:29
        QCoreApplication.translate("CP2KStudio", 'Required, e.g. PBE · OT · Geometry Optimization', 'studio.929111cca381af37'),
        # ui/main_window.py:746
        QCoreApplication.translate("CP2KStudio", 'Cannot Export This Configuration', 'studio.92c4fbdb0e47bd8e'),
        # ui/run_environment_panel.py:74
        QCoreApplication.translate("CP2KStudio", '{p0}: enter the package folder in a Bash terminal and run bash run.sh.', 'studio.92d64f06f8ed50d9'),
        # core/models.py:95
        QCoreApplication.translate("CP2KStudio", 'The structure contains invalid elements or dummy atoms', 'studio.92f32b7edc292e79'),
        # core/input_import.py:224
        QCoreApplication.translate("CP2KStudio", 'FIXED_ATOMS/LIST contains invalid atom indices', 'studio.9402b3cf7919388c'),
        # ui/run_environment_panel.py:15
        QCoreApplication.translate("CP2KStudio", '07 · Runtime Settings', 'studio.94039019f8868e02'),
        # core/input_import.py:72
        QCoreApplication.translate("CP2KStudio", 'The importer currently supports one orbital basis per KIND', 'studio.94b9f46f7476389a'),
        # core/atom_constraints.py:20
        QCoreApplication.translate("CP2KStudio", 'Minimum cannot exceed maximum', 'studio.94dcd65668a3a126'),
        # ui/scf_panel.py:40
        QCoreApplication.translate("CP2KStudio", 'SCF Basic Settings', 'studio.953a6174a85a454b'),
        # ui/structure_view.py:61
        QCoreApplication.translate("CP2KStudio", 'Reset camera and fit structure', 'studio.9595b75cbb077bfe'),
        # ui/structure_panel.py:170
        QCoreApplication.translate("CP2KStudio", 'Fixed: 0 atoms · Selected: 0 atoms', 'studio.95e94df25073aa21'),
        # ui/structure_panel.py:508
        QCoreApplication.translate("CP2KStudio", 'No atoms match the range', 'studio.962b3bd541bb11d3'),
        # ui/structure_panel.py:165
        QCoreApplication.translate("CP2KStudio", 'Select by Coordinate Range…', 'studio.96a1eac2d8ebb65a'),
        # core/kind_validator.py:126
        QCoreApplication.translate("CP2KStudio", 'The database fingerprint for {p0} changed; the original selection was preserved. Review and reselect it.', 'studio.98026d6a5b4e1862'),
        # ui/structure_panel.py:161
        QCoreApplication.translate("CP2KStudio", 'Fix components:', 'studio.989ef351d02d4727'),
        # core/comprehensive_check.py:53
        QCoreApplication.translate("CP2KStudio", '○ Not run: ', 'studio.9912ba5b51b69dde'),
        # ui/main_window.py:471
        QCoreApplication.translate("CP2KStudio", 'Syntax validation does not verify numerical accuracy or convergence.', 'studio.99ec5b4f0c08b1eb'),
        # ui/export_panel.py:129
        QCoreApplication.translate("CP2KStudio", '\nClick an error below to locate its settings.', 'studio.9a531bcc5beb203e'),
        # core/database_manager.py:137
        QCoreApplication.translate("CP2KStudio", 'Contents are absent from the pinned official manifest; explicitly add the custom file and declare its version', 'studio.9b07e34d190bf30d'),
        # ui/kind_panel.py:43
        QCoreApplication.translate("CP2KStudio", ' · Original entry not loaded / filtered out (preserved)', 'studio.9b9cb33eea4144d3'),
        # core/bundle_checks.py:78
        QCoreApplication.translate("CP2KStudio", 'RUN_ENVIRONMENT: EXPORT_NOTES.txt has a missing or incorrect {p0} value. Regenerate the notes.', 'studio.9c398b954cb84e4c'),
        # ui/kind_panel.py:323
        QCoreApplication.translate("CP2KStudio", 'Select an actual database entry', 'studio.9ca0f694480bfc6e'),
        # ui/export_panel.py:122
        QCoreApplication.translate("CP2KStudio", 'No Structure Imported', 'studio.9d5f4ff4800d3f67'),
        # ui/main_window.py:465
        QCoreApplication.translate("CP2KStudio", 'CP2K 2026.1 · Configuration Check', 'studio.9da7cf46a3db5697'),
        # ui/preset_dialogs.py:77
        QCoreApplication.translate("CP2KStudio", 'Preset “{p0}” already exists. Overwrite it, or return and save with another name.', 'studio.9de110d307c3ff3b'),
        # ui/export_panel.py:81
        QCoreApplication.translate("CP2KStudio", 'Validate Configuration', 'studio.9edac2fe10788eb8'),
        # ui/kind_panel.py:182
        QCoreApplication.translate("CP2KStudio", 'KIND label / actual ELEMENT', 'studio.9f1912c6ee43ee3e'),
        # ui/kind_panel.py:218
        QCoreApplication.translate("CP2KStudio", 'All Sources', 'studio.9f357adb6100face'),
        # core/database_manager.py:173
        QCoreApplication.translate("CP2KStudio", 'Project Record', 'studio.9f3c96e2f7b3f072'),
        # core/validator.py:73
        QCoreApplication.translate("CP2KStudio", 'WAVELET: only axis-aligned, orthogonal, positive cell vectors are currently supported', 'studio.9fb2cb7210b85d80'),
        # ui/validation_state.py:17
        QCoreApplication.translate("CP2KStudio", 'Configuration is incomplete or invalid', 'studio.9fb5ee285638ac47'),
        # core/comprehensive_check.py:55
        QCoreApplication.translate("CP2KStudio", '! Warnings present', 'studio.a0245c0ceba51295'),
        # ui/main_window.py:126
        QCoreApplication.translate("CP2KStudio", 'Project', 'studio.a049dca9d8f1e021'),
        # core/kind_validator.py:157
        QCoreApplication.translate("CP2KStudio", 'Basis label XC={p0} differs from the current functional {p1}; please review', 'studio.a0b9a0e806c1036f'),
        # ui/recommendation_dialog.py:64
        QCoreApplication.translate("CP2KStudio", 'Element configuration progress', 'studio.a0fefa8b05953324'),
        # ui/structure_panel.py:182
        QCoreApplication.translate("CP2KStudio", 'Element', 'studio.a1c1675f5df836a8'),
        # ui/xml_dialog.py:25
        QCoreApplication.translate("CP2KStudio", 'Choose an XML file generated by CP2K 2026.1', 'studio.a27b42f2bb23b5c8'),
        # ui/export_panel.py:85
        QCoreApplication.translate("CP2KStudio", 'Export CP2K Input', 'studio.a28ffa3b4bd36466'),
        # core/comprehensive_check.py:49
        QCoreApplication.translate("CP2KStudio", 'CP2K Studio · Comprehensive Validation', 'studio.a313548c904ec74e'),
        # ui/structure_view.py:347
        QCoreApplication.translate("CP2KStudio", ' · Selected (cyan): {p0} · Fixed (gold): {p1}', 'studio.a32c4d7e1419622a'),
        # ui/main_window.py:538
        QCoreApplication.translate("CP2KStudio", 'Open CP2K Studio Project', 'studio.a41dc714971719a0'),
        # ui/xml_dialog.py:38
        QCoreApplication.translate("CP2KStudio", 'Source', 'studio.a488e93d69cc1296'),
        # core/comprehensive_check.py:63
        QCoreApplication.translate("CP2KStudio", 'Warnings: {p0}', 'studio.a4924e37614f278b'),
        # ui/main_window.py:678
        QCoreApplication.translate("CP2KStudio", 'Correct the current fields first', 'studio.a4e9891ad4f837a6'),
        # ui/xml_dialog.py:39
        QCoreApplication.translate("CP2KStudio", 'Load Status', 'studio.a52bef0c615ce659'),
        # ui/main_window.py:133
        QCoreApplication.translate("CP2KStudio", 'Save Project', 'studio.a637cf4680fb5487'),
        # core/presets.py:170
        QCoreApplication.translate("CP2KStudio", 'KIND {p0} / {p1}: no unique preset match exists. Selection remains empty; configure its basis and pseudopotential.', 'studio.a777b684a3f0c770'),
        # ui/xml_dialog.py:51
        QCoreApplication.translate("CP2KStudio", 'Only target version 2026.1 is accepted. Schema changes do not modify the structure, calculation parameters, or INP preview; cancelling preserves project settings.', 'studio.a79dcca298bc393d'),
        # core/comprehensive_check.py:160
        QCoreApplication.translate("CP2KStudio", 'Standalone INP: path checks were skipped because source paths cannot be serialized safely; package paths were normalized.', 'studio.a84d03414247ea86'),
        # core/kind_validator.py:151
        QCoreApplication.translate("CP2KStudio", 'The current method is GPW/GTH; all-electron and non-GTH potentials are not supported', 'studio.a85b961961646612'),
        # core/validator.py:95
        QCoreApplication.translate("CP2KStudio", 'Basis file {p0}', 'studio.a85f6f29a980c76e'),
        # ui/xml_dialog.py:70
        QCoreApplication.translate("CP2KStudio", 'No file selected', 'studio.a96f374e86bc73e4'),
        # core/input_import.py:268
        QCoreApplication.translate("CP2KStudio", 'Settings not imported from {p0}: ', 'studio.a9bc38f5f9aae344'),
        # core/validator.py:134
        QCoreApplication.translate("CP2KStudio", 'SCF: smearing requires at least one additional orbital, ADDED_MOS', 'studio.a9d6812deca09a55'),
        # core/validator.py:86
        QCoreApplication.translate("CP2KStudio", 'DFT: explicitly set total CHARGE (enter 0 for a neutral system)', 'studio.a9d84cb7d9c13cda'),
        # core/input_import.py:42
        QCoreApplication.translate("CP2KStudio", 'The input does not explicitly specify CHARGE or MULTIPLICITY. These remain unset for user confirmation.', 'studio.a9f78c688b691c30'),
        # core/validator.py:147
        QCoreApplication.translate("CP2KStudio", 'Some pseudopotential names lack a -qN suffix; valence electron count and multiplicity were not checked', 'studio.aa2b2e275016f35d'),
        # core/bundle_checks.py:89
        QCoreApplication.translate("CP2KStudio", 'RUN_ENVIRONMENT: runtime settings or script files are unavailable: {p0}. Check step 07 and export again.', 'studio.aa50f82ce236fac6'),
        # ui/recommendation_dialog.py:207
        QCoreApplication.translate("CP2KStudio", 'No confirmed recommendation is available for this element/XC. Review actual candidates manually; no configuration is generated.', 'studio.aa7be42eb492ee8f'),
        # ui/dft_panel.py:13
        QCoreApplication.translate("CP2KStudio", 'Electronic State', 'studio.aa878a5d377835ba'),
        # ui/preset_dialogs.py:194
        QCoreApplication.translate("CP2KStudio", 'Delete personal preset “{p0}”?', 'studio.ac6bba918bb666e0'),
        # ui/main_window.py:243
        QCoreApplication.translate("CP2KStudio", '06 · Geometry Optimization', 'studio.acc062999902c75c'),
        # ui/export_panel.py:140
        QCoreApplication.translate("CP2KStudio", '{p0} · {p1}', 'studio.ae04d0e6f63d1e51'),
        # ui/main_window.py:295
        QCoreApplication.translate("CP2KStudio", 'Left-drag empty space to rotate · Click an atom to select · Right-drag to pan · Scroll to zoom. Bonds are not inferred.', 'studio.aed0843ffedd93b3'),
        # ui/main_window.py:822
        QCoreApplication.translate("CP2KStudio", 'ZIP Archive', 'studio.aeef5e29dcd4d482'),
        # core/models.py:128
        QCoreApplication.translate("CP2KStudio", 'Reordering or deletion used duplicate or unknown atom IDs', 'studio.af2d61440d4e288c'),
        # ui/validation_state.py:16
        QCoreApplication.translate("CP2KStudio", 'Required settings are complete; no known blocking errors', 'studio.afabec563bb0bd23'),
        # core/kind_validator.py:155
        QCoreApplication.translate("CP2KStudio", 'The current GPW/GTH workflow does not support all-electron bases; GAPW/all-electron calculations are not implemented', 'studio.afbe1290da67b26c'),
        # core/comprehensive_check.py:135
        QCoreApplication.translate("CP2KStudio", 'Package INP', 'studio.b0366e982a01c040'),
        # ui/main_window.py:329
        QCoreApplication.translate("CP2KStudio", 'Ready', 'studio.b073db9c0bd6f2ed'),
        # core/potential_database.py:92
        QCoreApplication.translate("CP2KStudio", 'No valid pseudopotential entry header found', 'studio.b07ddd79efca277a'),
        # core/run_config.py:71
        QCoreApplication.translate("CP2KStudio", 'Legacy runtime resources could not be converted reliably. Using Linux, MPI=16, OpenMP=1; review step 07.', 'studio.b08cfdf9dc4df1ce'),
        # core/comprehensive_check.py:106
        QCoreApplication.translate("CP2KStudio", 'Configuration completeness has blocking errors; a complete INP cannot be generated. Correct the first-stage issues first.', 'studio.b0d1609276358f00'),
        # ui/kind_panel.py:161
        QCoreApplication.translate("CP2KStudio", 'Valence q', 'studio.b163663a997add3d'),
        # ui/main_window.py:342
        QCoreApplication.translate("CP2KStudio", '06  Geometry Optimization', 'studio.b16f44f63f620bf3'),
        # ui/recommendation_dialog.py:22
        QCoreApplication.translate("CP2KStudio", 'KIND {p0} / ELEMENT {p1}', 'studio.b17cd0c5ceee2eec'),
        # ui/main_window.py:770
        QCoreApplication.translate("CP2KStudio", 'Generating, validating, and exporting INP…', 'studio.b2701880f1be6fed'),
        # ui/database_dialog.py:110
        QCoreApplication.translate("CP2KStudio", 'Verifying and fetching official data…', 'studio.b288a6b36f6844dc'),
        # core/validator.py:114
        QCoreApplication.translate("CP2KStudio", '{p0}: {p1} was resolved to an actual database file', 'studio.b2fb2f7f78313e8a'),
        # core/kind_validator.py:144
        QCoreApplication.translate("CP2KStudio", 'Missing q information; valence electron compatibility cannot be confirmed automatically', 'studio.b3684135c1beed9b'),
        # ui/kind_panel.py:62
        QCoreApplication.translate("CP2KStudio", 'Not selected · Type to search', 'studio.b3c03a0a71860d95'),
        # ui/coordinate_range_dialog.py:25
        QCoreApplication.translate("CP2KStudio", 'Axis (Cartesian)', 'studio.b49fbd64fc3aadaf'),
        # ui/kind_panel.py:132
        QCoreApplication.translate("CP2KStudio", '05 · Basis Sets & Pseudopotentials', 'studio.b5ea402fe0d220b2'),
        # ui/main_window.py:641
        QCoreApplication.translate("CP2KStudio", 'Apply “{p0}”?\n\n{p1}', 'studio.b6aa28c1ffe87e11'),
        # core/input_import.py:20
        QCoreApplication.translate("CP2KStudio", 'Only one FORCE_EVAL using Quickstep GPW can currently be imported', 'studio.b743214d0067c28b'),
        # ui/scf_panel.py:90
        QCoreApplication.translate("CP2KStudio", 'Fermi–Dirac Smearing', 'studio.b770653c619f7dae'),
        # ui/main_window.py:248
        QCoreApplication.translate("CP2KStudio", 'Convergence Thresholds', 'studio.b78b772cbbd1f76f'),
        # ui/kind_panel.py:328
        QCoreApplication.translate("CP2KStudio", '{p0} selected entries do not match the current filters and remain selected.', 'studio.b7d12343f4ff282c'),
        # core/validator.py:96
        QCoreApplication.translate("CP2KStudio", 'Pseudopotential file', 'studio.b7fdc12ded3be5f3'),
        # core/models.py:97
        QCoreApplication.translate("CP2KStudio", 'KIND label count differs from atom count', 'studio.b82781d7de03f191'),
        # ui/kind_panel.py:193
        QCoreApplication.translate("CP2KStudio", 'Basis Files (One per Line)', 'studio.b8c50ec53b4af5b4'),
        # ui/preset_dialogs.py:76
        QCoreApplication.translate("CP2KStudio", 'Preset Name Already Exists', 'studio.b94afae5ef8532fa'),
        # ui/database_dialog.py:54
        QCoreApplication.translate("CP2KStudio", 'Type', 'studio.ba40014ff496f64e'),
        # core/database_manager.py:85
        QCoreApplication.translate("CP2KStudio", '{p0} {p1}: same name, different contents (', 'studio.ba6572f598a3a639'),
        # ui/kind_panel.py:210
        QCoreApplication.translate("CP2KStudio", '\nCP2K {p0} · ', 'studio.ba683fae8953596f'),
        # ui/xml_dialog.py:104
        QCoreApplication.translate("CP2KStudio", 'Target Version Not Confirmed', 'studio.ba8a821987167ac7'),
        # core/database_manager.py:207
        QCoreApplication.translate("CP2KStudio", '{p0}: downloaded fingerprint does not match the pinned version', 'studio.bb307a5ca9f5e296'),
        # ui/preset_dialogs.py:165
        QCoreApplication.translate("CP2KStudio", '{p0}\nCP2K {p1} · Cell: {p2} · Coordinates: {p3} · Not CP2K syntax-certified', 'studio.bbad784deed494ef'),
        # core/validator.py:88
        QCoreApplication.translate("CP2KStudio", 'DFT: explicitly set spin MULTIPLICITY', 'studio.bcb243f50f952247'),
        # ui/main_window.py:673
        QCoreApplication.translate("CP2KStudio", ' (Draft / Incomplete)', 'studio.bcd798341592e388'),
        # core/presets.py:103
        QCoreApplication.translate("CP2KStudio", 'Geometry Optimization Preset', 'studio.bd64d9d635949360'),
        # core/atom_constraints.py:34
        QCoreApplication.translate("CP2KStudio", 'Unsupported fixed components', 'studio.be445cf0961ef93e'),
        # ui/export_panel.py:42
        QCoreApplication.translate("CP2KStudio", '01 Structure & Cell', 'studio.be6ce7489badaec9'),
        # ui/main_window.py:571
        QCoreApplication.translate("CP2KStudio", 'Save Project (Drafts Allowed)', 'studio.bed343b1926b5b52'),
        # core/input_import.py:23
        QCoreApplication.translate("CP2KStudio", 'INP import currently supports Quickstep / GPW only', 'studio.bef3e8778bc52812'),
        # ui/main_window.py:294
        QCoreApplication.translate("CP2KStudio", '3D Structure Viewer', 'studio.bf78457b5577d76a'),
        # ui/main_window.py:697
        QCoreApplication.translate("CP2KStudio", 'Supported settings were restored. Review them and save as a project.\n\n', 'studio.bf83c5fff371dde6'),
        # ui/main_window.py:132
        QCoreApplication.translate("CP2KStudio", 'Open Project...', 'studio.c0eaf52157af601f'),
        # core/basis_database.py:37
        QCoreApplication.translate("CP2KStudio", 'Insufficient contracted basis shells', 'studio.c15c3911b1df441a'),
        # core/kind_validator.py:109
        QCoreApplication.translate("CP2KStudio", 'Explicitly select both a basis set and a pseudopotential', 'studio.c1c1399a7e3a8dd0'),
        # core/potential_database.py:22
        QCoreApplication.translate("CP2KStudio", 'Invalid pseudopotential electron configuration', 'studio.c1c2e57b68dba56c'),
        # core/presets.py:247
        QCoreApplication.translate("CP2KStudio", 'Preset “{p0}” already exists; confirm overwrite or choose another name', 'studio.c1f8311bbe7e3e0c'),
        # ui/preset_dialogs.py:202
        QCoreApplication.translate("CP2KStudio", 'Delete Failed', 'studio.c228558cf257fc49'),
        # ui/recommendation_dialog.py:169
        QCoreApplication.translate("CP2KStudio", 'All Elements', 'studio.c267807c83aabf89'),
        # ui/main_window.py:687
        QCoreApplication.translate("CP2KStudio", 'CP2K (*.inp *.restart);;All Files (*)', 'studio.c2dfd14c0296c58b'),
        # core/bundle_checks.py:57
        QCoreApplication.translate("CP2KStudio", "KIND {p0}: the final INP's {p1} file does not contain the required {p2} / {p3} entry. Check data sources and file order, then reselect the entry.", 'studio.c3197cd5d0c68893'),
        # ui/run_environment_panel.py:49
        QCoreApplication.translate("CP2KStudio", 'The target environment must provide mpirun and cp2k.psmp on PATH with compatible MPI implementations.', 'studio.c3a93b0864d416e9'),
        # core/comprehensive_check.py:61
        QCoreApplication.translate("CP2KStudio", 'Validation Completed with Warnings', 'studio.c4fb32fba754cd3f'),
        # ui/export_panel.py:123
        QCoreApplication.translate("CP2KStudio", 'Project: {p0}    Task: {p1}\nDFT: Quickstep / GPW    SCF: {p2}\nStructure: {p3}', 'studio.c51bdb837205503c'),
        # core/kind_recommender.py:25
        QCoreApplication.translate("CP2KStudio", 'Relatively small basis', 'studio.c54b857416db6fc3'),
        # core/comprehensive_check.py:142
        QCoreApplication.translate("CP2KStudio", 'Standalone INP generation failed: {p0}. Correct the parameters and retry.', 'studio.c651d210d7125b83'),
        # core/input_export.py:36
        QCoreApplication.translate("CP2KStudio", 'Dependency already exists with different contents: {p0}. Choose a new folder or export a calculation package.', 'studio.c677e14a74bd0495'),
        # ui/database_dialog.py:54
        QCoreApplication.translate("CP2KStudio", 'Source / CP2K Version', 'studio.c6a64b78b6f8ce82'),
        # ui/structure_panel.py:159
        QCoreApplication.translate("CP2KStudio", 'Fixed components (fractional coordinates)', 'studio.c6e9bf994796e74d'),
        # ui/database_dialog.py:54
        QCoreApplication.translate("CP2KStudio", 'File Path', 'studio.c71200b5952e3781'),
        # ui/structure_panel.py:108
        QCoreApplication.translate("CP2KStudio", 'Structure Import', 'studio.c77dc73ab554bf6c'),
        # core/comprehensive_check.py:55
        QCoreApplication.translate("CP2KStudio", '× Failed', 'studio.c7f4ebbc24b92c26'),
        # ui/main_window.py:687
        QCoreApplication.translate("CP2KStudio", 'Import Supported INP Settings', 'studio.c81292edbf6efb64'),
        # ui/main_window.py:673
        QCoreApplication.translate("CP2KStudio", 'Preset saved: {p0}', 'studio.c825bc2249725e61'),
        # core/run_config.py:53
        QCoreApplication.translate("CP2KStudio", 'Ignored legacy total_cpu_cores; current runtime settings were retained.', 'studio.c8545f203bfc44e3'),
        # ui/main_window.py:202
        QCoreApplication.translate("CP2KStudio", '08  Export & Presets', 'studio.c86dd81d809dee26'),
        # ui/kind_panel.py:161
        QCoreApplication.translate("CP2KStudio", 'e.g. 6', 'studio.c9566523da347bed'),
        # core/project_io.py:186
        QCoreApplication.translate("CP2KStudio", 'Export folder already exists; choose a new folder: {p0}', 'studio.ca0a92650f6bc7e0'),
        # ui/main_window.py:673
        QCoreApplication.translate("CP2KStudio", ' (Not XML-Certified)', 'studio.ca49ec7ca1226495'),
        # core/validator.py:47
        QCoreApplication.translate("CP2KStudio", 'SUBSYS: import a nonempty structure', 'studio.ca7f89367263988f'),
        # core/bundle_checks.py:72
        QCoreApplication.translate("CP2KStudio", 'RUN_ENVIRONMENT: MPI/OpenMP settings or input.inp/output.out commands in run.sh differ from this configuration. Regenerate the package.', 'studio.cb047e962f3bc670'),
        # ui/main_window.py:754
        QCoreApplication.translate("CP2KStudio", 'There are {p0} warnings; the actual files will be checked again during export.', 'studio.cb3369b5545f6da3'),
        # ui/main_window.py:157
        QCoreApplication.translate("CP2KStudio", 'Help', 'studio.cb4ba40bf823511d'),
        # core/basis_database.py:44
        QCoreApplication.translate("CP2KStudio", 'Exponent or contraction coefficient count does not match the shell definition', 'studio.cb5f73dede3b02fc'),
        # ui/main_window.py:834
        QCoreApplication.translate("CP2KStudio", 'Invalid Folder Name', 'studio.cb65a8eed82eb073'),
        # core/structure.py:45
        QCoreApplication.translate("CP2KStudio", 'The file must contain exactly one structure; select and save the required frame separately', 'studio.cbc2777159c49897'),
        # ui/database_dialog.py:80
        QCoreApplication.translate("CP2KStudio", '{p0}\n{p1} · CP2K {p2}\nSHA256 {p3}\n{p4}', 'studio.cc09339ad516a7c3'),
        # core/potential_database.py:75
        QCoreApplication.translate("CP2KStudio", 'Nonlocal triangular-matrix coefficient count mismatch', 'studio.cc7dba22c44eea41'),
        # core/database_format.py:48
        QCoreApplication.translate("CP2KStudio", '{p0}: data block ended early', 'studio.cc8cfb858d5ad3de'),
        # ui/kind_panel.py:144
        QCoreApplication.translate("CP2KStudio", 'Database Manager…', 'studio.cd1ec226a7396f90'),
        # core/kind_validator.py:169
        QCoreApplication.translate("CP2KStudio", 'The same element / pseudopotential name has different selected contents and cannot be merged unambiguously', 'studio.cd405a7b1d8fb5d5'),
        # ui/main_window.py:636
        QCoreApplication.translate("CP2KStudio", '\nThis preset explicitly includes the cell or coordinates. Confirming will replace those settings.', 'studio.cd4c8608417c225b'),
        # ui/scf_panel.py:73
        QCoreApplication.translate("CP2KStudio", 'Diagonalization Parameters', 'studio.cd6b53247ad1090d'),
        # ui/export_panel.py:135
        QCoreApplication.translate("CP2KStudio", 'Validation passed · {p0} warnings', 'studio.cd741ca95e098949'),
        # ui/xml_dialog.py:71
        QCoreApplication.translate("CP2KStudio", 'Not Checked', 'studio.cdbc0434f568fc9e'),
        # core/comprehensive_check.py:121
        QCoreApplication.translate("CP2KStudio", 'Temporary package preparation failed: {p0}. Check source files and path permissions.', 'studio.ce74b6892260325e'),
        # core/comprehensive_check.py:61
        QCoreApplication.translate("CP2KStudio", 'Validation Failed', 'studio.cea8aae4ccdfeba2'),
        # ui/recommendation_dialog.py:86
        QCoreApplication.translate("CP2KStudio", 'Current Selections', 'studio.cf6da91a404d0589'),
        # core/comprehensive_check.py:45
        QCoreApplication.translate("CP2KStudio", 'Required validation stages have not run. Correct the preceding issues and validate again.', 'studio.cff3cde96485c690'),
        # ui/structure_panel.py:127
        QCoreApplication.translate("CP2KStudio", 'PERIODIC · Keep CELL and POISSON consistent', 'studio.d08a29082f7ac8a5'),
        # ui/recommendation_dialog.py:56
        QCoreApplication.translate("CP2KStudio", 'Element Filter:', 'studio.d0cc3e65ececf2e6'),
        # ui/dft_panel.py:22
        QCoreApplication.translate("CP2KStudio", 'QCheckBox {{ min-height:{p0}px; }}', 'studio.d0e2e59c838b2e4e'),
        # ui/main_window.py:779
        QCoreApplication.translate("CP2KStudio", '\n\nExport a calculation package when moving to another computing environment.', 'studio.d1526f82e8b99974'),
        # core/input_import.py:217
        QCoreApplication.translate("CP2KStudio", 'FIXED_ATOMS with extra selectors or RESTRAINT was not imported. Retain and check the original input.', 'studio.d15e886442533dd1'),
        # ui/kind_panel.py:29
        QCoreApplication.translate("CP2KStudio", '— Not selected; type to search —', 'studio.d1fc96246334d968'),
        # ui/export_panel.py:111
        QCoreApplication.translate("CP2KStudio", 'Save as Preset', 'studio.d2aa9ac606d79c4a'),
        # ui/kind_panel.py:197
        QCoreApplication.translate("CP2KStudio", 'Add Custom Basis Set…', 'studio.d3385bff4858c436'),
        # core/presets.py:195
        QCoreApplication.translate("CP2KStudio", 'This preset was saved as an incomplete draft. Validate the configuration after applying it.', 'studio.d341957c4dfe9dc2'),
        # ui/main_window.py:871
        QCoreApplication.translate("CP2KStudio", 'Wait for the current validation or export to finish before closing', 'studio.d3f26170bc076496'),
        # core/validator.py:101
        QCoreApplication.translate("CP2KStudio", 'DFT: configure at least one basis file', 'studio.d3f34013070ef297'),
        # ui/main_window.py:656
        QCoreApplication.translate("CP2KStudio", 'No personal presets; save one in step 08', 'studio.d460429579dafac9'),
        # ui/structure_panel.py:182
        QCoreApplication.translate("CP2KStudio", 'Fixed', 'studio.d4b3f49cd2e4254f'),
        # ui/main_window.py:461
        QCoreApplication.translate("CP2KStudio", 'Untitled Project', 'studio.d55e16c0a7d0ce8c'),
        # core/basis_database.py:70
        QCoreApplication.translate("CP2KStudio", '{p0}: excluded after strict format check: {p1}', 'studio.d56214239ca55912'),
        # core/kind_validator.py:24
        QCoreApplication.translate("CP2KStudio", 'KIND {p0}：{p1}', 'studio.d59e6e4c95e0240c'),
        # ui/dft_panel.py:30
        QCoreApplication.translate("CP2KStudio", 'Quickstep / GPW · Γ point; the calculation method is unchanged.', 'studio.d5d15bb7eb25d40a'),
        # core/project_io.py:100
        QCoreApplication.translate("CP2KStudio", 'Project file exceeds the 100 MB limit', 'studio.d6a7040604825764'),
        # core/comprehensive_check.py:55
        QCoreApplication.translate("CP2KStudio", '✓ Passed', 'studio.d6c446460683f728'),
        # ui/export_panel.py:132
        QCoreApplication.translate("CP2KStudio", 'Configuration checked · {p0} warnings · See the validation report', 'studio.d6d9ef96ac44a283'),
        # core/validator.py:90
        QCoreApplication.translate("CP2KStudio", 'DFT: enable UKS when MULTIPLICITY is greater than 1', 'studio.d6e30a303277592e'),
        # core/validator.py:67
        QCoreApplication.translate("CP2KStudio", 'POISSON: ANALYTIC supports only 0D, 1D, and 2D systems', 'studio.d7699e3602889b44'),
        # ui/main_window.py:653
        QCoreApplication.translate("CP2KStudio", 'Not certified by CP2K syntax validation', 'studio.d8cd1b51d67a610b'),
        # core/presets.py:177
        QCoreApplication.translate("CP2KStudio", 'No atomic structure is present. Preset KINDs were retained; verify element configurations after importing a structure.', 'studio.d8dc82764a17f88e'),
        # ui/main_window.py:499
        QCoreApplication.translate("CP2KStudio", 'Configuration or dependencies changed during validation. Please run it again.', 'studio.d90fe896b4f7ea59'),
        # ui/coordinate_range_dialog.py:35
        QCoreApplication.translate("CP2KStudio", 'Select Atoms', 'studio.d91b106122b3fea9'),
        # ui/scf_panel.py:72
        QCoreApplication.translate("CP2KStudio", 'DIAGONALIZATION Settings', 'studio.d96d3c8878c314fd'),
        # core/input_import.py:60
        QCoreApplication.translate("CP2KStudio", 'This smearing method is not supported', 'studio.d994994e975db661'),
        # ui/main_window.py:778
        QCoreApplication.translate("CP2KStudio", 'Coordinates are embedded in the INP. These dependency files must remain accessible:\n', 'studio.d996dcb969ea459d'),
        # ui/main_window.py:625
        QCoreApplication.translate("CP2KStudio", 'Cannot Read Preset', 'studio.d9cf91ba5e91c8e8'),
        # ui/structure_view.py:106
        QCoreApplication.translate("CP2KStudio", 'View along the actual cell {p0} vector', 'studio.da5ba79f2319a28d'),
        # core/models.py:417
        QCoreApplication.translate("CP2KStudio", 'KIND {p0} requires an explicit ELEMENT', 'studio.da7d29a23b2baf91'),
        # ui/database_dialog.py:50
        QCoreApplication.translate("CP2KStudio", 'Rescan', 'studio.daf5103f90cc7d3a'),
        # ui/scf_panel.py:59
        QCoreApplication.translate("CP2KStudio", 'OT Settings', 'studio.db98905d1e735c49'),
        # ui/recommendation_dialog.py:244
        QCoreApplication.translate("CP2KStudio", 'Applied to KIND {p0}', 'studio.dbcdf7e62cdb8a56'),
        # ui/main_window.py:552
        QCoreApplication.translate("CP2KStudio", 'Runtime settings were migrated from an older format. Review the report and step 07.', 'studio.dc29063153e16021'),
        # ui/main_window.py:604
        QCoreApplication.translate("CP2KStudio", 'Structure Import Failed', 'studio.dc367c4e73066bd0'),
        # core/potential_database.py:57
        QCoreApplication.translate("CP2KStudio", 'Invalid nonlocal channel count', 'studio.dc52ede281f9a5b8'),
        # core/basis_database.py:40
        QCoreApplication.translate("CP2KStudio", 'Negative contracted shell count', 'studio.dcd43afee5c13b0c'),
        # core/input_export.py:29
        QCoreApplication.translate("CP2KStudio", 'Input file already exists: {p0}', 'studio.dd30262c49175ad0'),
        # ui/main_window.py:306
        QCoreApplication.translate("CP2KStudio", 'INP · Live Preview', 'studio.dd4f801cad97027e'),
        # core/run_config.py:68
        QCoreApplication.translate("CP2KStudio", 'Converted legacy total_cpu_cores / omp_threads to MPI processes; verify runtime settings.', 'studio.dda2f26a5f277437'),
        # ui/kind_panel.py:174
        QCoreApplication.translate("CP2KStudio", 'Basis & Pseudopotential per KIND', 'studio.de04bcb2a5a35926'),
        # core/bundle_checks.py:81
        QCoreApplication.translate("CP2KStudio", 'RUN_ENVIRONMENT: run.sh does not use input.inp as its input filename. Regenerate the script.', 'studio.de517a7757ed9d74'),
        # core/database_manager.py:165
        QCoreApplication.translate("CP2KStudio", 'Official User Cache', 'studio.df517971e5841e83'),
        # core/potential_database.py:61
        QCoreApplication.translate("CP2KStudio", 'Missing nonlocal term', 'studio.df6de87b16e8fdba'),
        # ui/main_window.py:619
        QCoreApplication.translate("CP2KStudio", 'Preset applied: {p0}', 'studio.dfb8a1454043632b'),
        # ui/kind_panel.py:149
        QCoreApplication.translate("CP2KStudio", 'Basis Set & Pseudopotential Configuration', 'studio.e0011b948d8d6541'),
        # core/validator.py:132
        QCoreApplication.translate("CP2KStudio", 'SCF: OT does not support smearing or ADDED_MOS; switch to DIAGONALIZATION', 'studio.e03a01b138e8e14e'),
        # ui/structure_panel.py:400
        QCoreApplication.translate("CP2KStudio", 'Invalid atom ID', 'studio.e05cd1577b16fa42'),
        # ui/database_dialog.py:32
        QCoreApplication.translate("CP2KStudio", 'Database Manager · CP2K 2026.1', 'studio.e09840682cd491bd'),
        # ui/main_window.py:766
        QCoreApplication.translate("CP2KStudio", 'Overwrite Input File', 'studio.e1657b1e62de9d29'),
        # core/basis_database.py:35
        QCoreApplication.translate("CP2KStudio", 'Invalid basis shell range', 'studio.e16caf839d6e84be'),
        # ui/recommendation_dialog.py:68
        QCoreApplication.translate("CP2KStudio", 'Pseudopotential', 'studio.e2a0fff9b04a6077'),
        # ui/main_window.py:839
        QCoreApplication.translate("CP2KStudio", 'Validating and exporting calculation package…', 'studio.e44a9dcdd2b3bab0'),
        # ui/main_window.py:504
        QCoreApplication.translate("CP2KStudio", 'Validation failed to run: {p0}. Check the files and configuration, then retry.', 'studio.e475f6d0ee160ef8'),
        # ui/database_dialog.py:61
        QCoreApplication.translate("CP2KStudio", 'Advanced: explicitly add custom files (user-declared version)', 'studio.e527613ccf080158'),
        # ui/kind_panel.py:194
        QCoreApplication.translate("CP2KStudio", 'Pseudopotential Files (One per Line)', 'studio.e692e36d4768e8d7'),
        # ui/database_dialog.py:83
        QCoreApplication.translate("CP2KStudio", 'Choose CP2K Data Folder', 'studio.e6d3b78d75637d43'),
        # ui/main_window.py:662
        QCoreApplication.translate("CP2KStudio", 'Manage Presets…', 'studio.e728dcf9078295a9'),
        # ui/kind_panel.py:186
        QCoreApplication.translate("CP2KStudio", 'Advanced: manual files / custom data', 'studio.e73cb710f632a630'),
        # ui/database_dialog.py:42
        QCoreApplication.translate("CP2KStudio", 'Browse Folder…', 'studio.e7f468a900163753'),
        # ui/structure_view.py:57
        QCoreApplication.translate("CP2KStudio", 'Show / hide all element labels', 'studio.e808c1fd40c65985'),
        # core/input_import.py:89
        QCoreApplication.translate("CP2KStudio", 'Invalid coordinate row', 'studio.e827569b6e802ec3'),
        # ui/export_panel.py:32
        QCoreApplication.translate("CP2KStudio", '07 Runtime Settings', 'studio.e913fb5c6113b608'),
        # ui/main_window.py:202
        QCoreApplication.translate("CP2KStudio", '01  Structure & Cell', 'studio.ea618ebc5acdddab'),
        # core/database_manager.py:163
        QCoreApplication.translate("CP2KStudio", 'Local Installation Discovery', 'studio.eb0c895aec1fe268'),
        # core/validator.py:99
        QCoreApplication.translate("CP2KStudio", 'Pseudopotential source', 'studio.ebb4ca9179d67a26'),
        # core/presets.py:92
        QCoreApplication.translate("CP2KStudio", 'No structure is available to save cell or coordinate settings', 'studio.ebf896674bae4bbe'),
        # ui/database_dialog.py:98
        QCoreApplication.translate("CP2KStudio", 'No same-element, same-name entries with conflicting contents were found.', 'studio.ec3edaec6058e8d9'),
        # ui/main_window.py:774
        QCoreApplication.translate("CP2KStudio", 'INP Export Failed', 'studio.ecac498859c2e71e'),
        # core/comprehensive_check.py:165
        QCoreApplication.translate("CP2KStudio", 'MPI: {p0} · OpenMP: {p1} · Required logical cores: {p2}', 'studio.ecaf21917207b4ae'),
        # core/kind_validator.py:124
        QCoreApplication.translate("CP2KStudio", 'The recorded version {p1} for {p0} does not match the target', 'studio.ecc1d42b3538a37c'),
        # core/database_manager.py:129
        QCoreApplication.translate("CP2KStudio", 'File fingerprint mismatch; loading refused', 'studio.ecf90746096e9e3b'),
        # core/validator.py:92
        QCoreApplication.translate("CP2KStudio", 'XC: select a functional', 'studio.ed6e78e4381c9d67'),
        # ui/main_window.py:716
        QCoreApplication.translate("CP2KStudio", 'XML schema updated; subsequent validation will use the selected file', 'studio.edf2d947adf78e23'),
        # ui/recommendation_dialog.py:20
        QCoreApplication.translate("CP2KStudio", 'KIND {p0}', 'studio.ee89f5a3a4a98787'),
        # ui/recommendation_dialog.py:49
        QCoreApplication.translate("CP2KStudio", 'Recommend Basis Sets & Pseudopotentials', 'studio.eec62d383b87d4cd'),
        # ui/main_window.py:830
        QCoreApplication.translate("CP2KStudio", 'New folder name (must not already exist):', 'studio.efe40b2a65426a0f'),
        # core/kind_validator.py:153
        QCoreApplication.translate("CP2KStudio", 'The basis is not explicitly tagged GTH; suitability for GPW/GTH cannot be confirmed automatically', 'studio.f064f75b7d13f10c'),
        # ui/xml_dialog.py:47
        QCoreApplication.translate("CP2KStudio", 'Restore Default XML', 'studio.f08618fa6f089d26'),
        # core/atom_constraints.py:16
        QCoreApplication.translate("CP2KStudio", 'Minimum and maximum must be valid numbers (scientific notation is supported)', 'studio.f0902162e8a7f393'),
        # ui/run_environment_panel.py:73
        QCoreApplication.translate("CP2KStudio", 'Windows / WSL2: run bash run.sh in the WSL2 Linux terminal; Bash commands do not run directly in native PowerShell.', 'studio.f0bf6628232e46da'),
        # ui/validation_state.py:18
        QCoreApplication.translate("CP2KStudio", 'Checking parameters', 'studio.f10d1173404b37af'),
        # core/database_manager.py:135
        QCoreApplication.translate("CP2KStudio", 'Version is {p0}; target is {p1}. Provide version information.', 'studio.f1909a23bc366d1c'),
        # core/schema.py:17
        QCoreApplication.translate("CP2KStudio", 'Unknown version', 'studio.f1e7bec171ae3b9e'),
        # ui/kind_panel.py:378
        QCoreApplication.translate("CP2KStudio", '× Fix required', 'studio.f1f14e53c154f562'),
        # ui/xml_dialog.py:97
        QCoreApplication.translate("CP2KStudio", 'Custom File', 'studio.f20216fd37e725fc'),
        # core/validator.py:103
        QCoreApplication.translate("CP2KStudio", 'DFT: configure at least one accessible pseudopotential file', 'studio.f273a1b0557d9cbe'),
        # ui/kind_panel.py:157
        QCoreApplication.translate("CP2KStudio", 'Current XC', 'studio.f2be0d642eeb4969'),
        # ui/preset_dialogs.py:147
        QCoreApplication.translate("CP2KStudio", ' · Complete / Not Certified', 'studio.f3501a1d2d983a3d'),
        # ui/run_environment_panel.py:38
        QCoreApplication.translate("CP2KStudio", 'MPI × OpenMP; this is not the physical core count and does not allocate resources.', 'studio.f37272c3d72c4a4a'),
        # core/database_manager.py:174
        QCoreApplication.translate("CP2KStudio", 'Official User', 'studio.f5a0cfe232dd30b2'),
        # core/kind_recommender.py:26
        QCoreApplication.translate("CP2KStudio", 'Higher-quality candidate', 'studio.f65e68836452626e'),
        # ui/database_dialog.py:35
        QCoreApplication.translate("CP2KStudio", 'Priority: specified folder → local installation → verified official cache. Unknown or different versions are never mixed silently.\nThe bundled cache is from official v2026.1; startup does not access the network. A user-declared version is not official certification.', 'studio.f66b15184e610044'),
        # ui/run_environment_panel.py:44
        QCoreApplication.translate("CP2KStudio", 'Execution Mode', 'studio.f6c67c56f2637ff4'),
        # ui/main_window.py:667
        QCoreApplication.translate("CP2KStudio", 'Correct the invalid fields first:\n', 'studio.f7dfcbf254ddad12'),
        # core/models.py:415
        QCoreApplication.translate("CP2KStudio", 'Invalid KIND label format', 'studio.f7f0fb9407a14124'),
        # core/kind_validator.py:112
        QCoreApplication.translate("CP2KStudio", 'ELEMENT {p0} differs from the actual structure element {p1}', 'studio.f99304f78a38574e'),
        # ui/dft_panel.py:34
        QCoreApplication.translate("CP2KStudio", 'MGRID / Plane-Wave Grid', 'studio.f9a657e9dc6c9f9e'),
        # ui/structure_panel.py:156
        QCoreApplication.translate("CP2KStudio", 'Unfix Selected', 'studio.fa7dd269ce190eb7'),
        # ui/help_dialog.py:46
        QCoreApplication.translate("CP2KStudio", 'OK', 'studio.fac2a67ad87807c4'),
        # core/presets.py:109
        QCoreApplication.translate("CP2KStudio", 'Only workflow settings are applied; missing chemistry is not filled in.', 'studio.fb99d1d00258e087'),
        # core/comprehensive_check.py:112
        QCoreApplication.translate("CP2KStudio", 'XML schema unavailable: {p0}: {p1}. Select a valid 2026.1 file in XML Schema and retry.', 'studio.fc79ea0f09f3df0b'),
        # core/kind_validator.py:142
        QCoreApplication.translate("CP2KStudio", 'Basis q{p0} differs from pseudopotential q{p1}', 'studio.fe1a31a6ced795a1'),
        # core/comprehensive_check.py:122
        QCoreApplication.translate("CP2KStudio", 'Cannot prepare a complete package and final INP.', 'studio.ff2bb8484d57f177'),
        # ui/main_window.py:492
        QCoreApplication.translate("CP2KStudio", 'CP2K Studio · Comprehensive Validation\nChecking configuration, XML, dependencies, and calculation package…', 'studio.ff478f9da21b1017'),
        # core/presets.py:187
        QCoreApplication.translate("CP2KStudio", 'Database Settings', 'studio.ff513eba23a1b94e'),
        # core/comprehensive_check.py:58
        QCoreApplication.translate("CP2KStudio", 'Info · ', 'validation.info_prefix'),
        # ui/vibrational_panel.py:79
        QCoreApplication.translate("CP2KStudio", 'Thermochemistry is optional and only applies to isolated gas-phase molecules. Temperature is in K and pressure in Pa. Molden and Hessian files are produced by CP2K after running; the Hessian file is binary.', 'vib.advanced_help'),
        # ui/vibrational_panel.py:78
        QCoreApplication.translate("CP2KStudio", 'Thermochemistry & Output', 'vib.advanced_title'),
        # ui/vibrational_panel.py:26
        QCoreApplication.translate("CP2KStudio", '✓ Frequencies & Normal Modes', 'vib.always_frequencies'),
        # ui/vibrational_panel.py:30
        QCoreApplication.translate("CP2KStudio", 'Always included', 'vib.always_included'),
        # core/vibrational.py:130
        QCoreApplication.translate("CP2KStudio", 'VIBRATIONAL_ANALYSIS: at least two atoms are required by this molecular/full-mode workflow.', 'vib.atom_count_error'),
        # ui/vibrational_panel.py:48
        QCoreApplication.translate("CP2KStudio", 'DX is in bohr. NPROC_REP is the number of MPI ranks per replica, not the number of replicas; it must divide the MPI total in step 07. FULLY_PERIODIC retains rotations and is never enabled automatically.', 'vib.basic_help'),
        # ui/vibrational_panel.py:47
        QCoreApplication.translate("CP2KStudio", 'Finite Differences & Replicas', 'vib.basic_title'),
        # core/vibrational.py:120
        QCoreApplication.translate("CP2KStudio", 'VIBRATIONAL_ANALYSIS / IR: MOMENTS uses the Berry-phase dipole operator with MAX_MOMENT 1. Polarization is defined modulo a lattice-dependent quantum; inspect branch continuity across finite displacements and test DX, SCF and grid convergence.', 'vib.berry_branch_info'),
        # ui/vibrational_panel.py:198
        QCoreApplication.translate("CP2KStudio", 'IR + Raman: dipole moments and polarizabilities use one Hessian workflow. Raman requires closed-shell OT without smearing/ADDED_MOS; response and intensity convergence require a CP2K run.', 'vib.combined_note'),
        # ui/export_panel.py:30
        QCoreApplication.translate("CP2KStudio", '06 Vibrational Analysis', 'vib.error_page'),
        # core/export_notes_generator.py:10
        QCoreApplication.translate("CP2KStudio", '7. VIBRATIONAL ANALYSIS\nMode: {mode}\nDX: {dx} bohr; NPROC_REP: {ranks} MPI ranks per replica (not replica count).\nMOLDEN_VIB: {molden}; HESSIAN: {hessian}.\nAfter a successful CP2K calculation, output.out contains frequencies and, when requested, IR/Raman intensities. MOLDEN_VIB writes normal modes for Molden; HESSIAN writes a CP2K binary .hess file. Actual filenames follow CP2K project/print conventions. No spectrum image or broadened spectrum is generated by Studio.\nNo results are included: CP2K has not run. Use a tightly optimized stationary structure and test SCF, grid, displacement and response convergence. Saved GEO_OPT fixed atoms are ignored; all atoms enter the full Hessian. IR/Raman response has not been numerically verified by Studio. XML validity does not establish a successful intensity calculation.\n', 'vib.export_notes'),
        # core/vibrational.py:132
        QCoreApplication.translate("CP2KStudio", 'VIBRATIONAL_ANALYSIS: saved GEO_OPT fixed-atom constraints are not applied. A full Hessian of all atoms will be computed; partial/constrained vibrational analysis is not implemented.', 'vib.fixed_warning'),
        # ui/vibrational_panel.py:201
        QCoreApplication.translate("CP2KStudio", 'Use tightly optimized coordinates. Frequencies and normal modes do not certify an energy minimum; check imaginary modes and convergence.', 'vib.frequencies_note'),
        # ui/vibrational_panel.py:77
        QCoreApplication.translate("CP2KStudio", 'FULLY_PERIODIC prevents removal of rotational modes from the Hessian. It is usually appropriate for a 3D periodic crystal, but does not set CELL/PERIODIC or select a dipole operator. Review it explicitly; Studio never changes this option automatically.', 'vib.fully_periodic_help'),
        # ui/vibrational_panel.py:86
        QCoreApplication.translate("CP2KStudio", 'Write Binary Hessian', 'vib.hessian'),
        # core/input_import.py:202
        QCoreApplication.translate("CP2KStudio", 'VIBRATIONAL_ANALYSIS import requires at least one enabled IR or Raman property workflow when INTENSITIES is enabled. Required properties cannot be omitted.', 'vib.import_intensities'),
        # core/input_import.py:183
        QCoreApplication.translate("CP2KStudio", 'VIBRATIONAL_ANALYSIS import supports only the full Hessian; MODE_SELECTIVE cannot be represented by this workflow.', 'vib.import_selective'),
        # ui/vibrational_panel.py:33
        QCoreApplication.translate("CP2KStudio", 'IR Intensities', 'vib.ir'),
        # ui/vibrational_panel.py:200
        QCoreApplication.translate("CP2KStudio", 'IR: isolated molecules use the nonperiodic dipole operator; XYZ uses Berry-phase dipole moments. Partial periodicity is not supported for intensities.', 'vib.ir_note'),
        # core/vibrational.py:63
        QCoreApplication.translate("CP2KStudio", 'VIBRATIONAL_ANALYSIS: periodic spectra currently support only the implicit Gamma-point Quickstep/GPW supercell workflow. Explicit KPOINTS with Berry-phase moments or LINRES have not been validated and cannot be imported or exported by Studio.', 'vib.kpoints_error'),
        # core/models.py:312
        QCoreApplication.translate("CP2KStudio", 'VIBRATIONAL_ANALYSIS: unknown legacy mode {mode}; the IR/Raman switches cannot be migrated safely.', 'vib.legacy_mode_error'),
        # core/models.py:289
        QCoreApplication.translate("CP2KStudio", 'VIBRATIONAL_ANALYSIS / LINRES / ENERGY_GAP: enter a finite positive real number in Ha.', 'vib.linres_energy_gap_error'),
        # ui/vibrational_panel.py:122
        QCoreApplication.translate("CP2KStudio", 'LINRES / ENERGY_GAP\n\nEstimated electronic gap used by the linear-response preconditioner, in Hartree (Ha). This parameter is independent of SCF/OT ENERGY_GAP.\n\n• CP2K default: 0.2 Ha.\n• With FULL_ALL, ENERGY_GAP should underestimate the actual HOMO–LUMO gap.\n• Smaller values such as 0.001–0.01 Ha may be tested for insulating systems.\n• An excessively large estimate may reduce preconditioning efficiency or destabilize convergence.\n• The optimal value depends on the electronic structure; smaller values are not guaranteed to converge faster.\n\nWhen PRECONDITIONER is NONE, ENERGY_GAP does not provide a preconditioning effect.', 'vib.linres_energy_gap_help'),
        # core/vibrational.py:102
        QCoreApplication.translate("CP2KStudio", 'VIBRATIONAL_ANALYSIS / LINRES / FULL_ALL: ENERGY_GAP should underestimate the actual HOMO–LUMO gap. This estimate is independent of SCF/OT ENERGY_GAP; test response convergence. Preconditioning does not guarantee convergence or verify periodic Raman runtime support.', 'vib.linres_full_all_info'),
        # core/models.py:278
        QCoreApplication.translate("CP2KStudio", 'VIBRATIONAL_ANALYSIS / LINRES / PRECONDITIONER: select NONE, FULL_ALL, FULL_SINGLE_INVERSE, FULL_SINGLE, FULL_KINETIC or FULL_S_INVERSE.', 'vib.linres_preconditioner_error'),
        # ui/vibrational_panel.py:110
        QCoreApplication.translate("CP2KStudio", 'LINRES / PRECONDITIONER\n\nControls preconditioning for Raman linear-response calculations. This setting is independent of the SCF/OT preconditioner.\n\n• NONE: No preconditioning; CP2K default.\n• FULL_ALL: Often effective, but relatively expensive to construct.\n• FULL_SINGLE_INVERSE: Useful for larger systems.\n• FULL_SINGLE: Diagonalization-based preconditioning.\n• FULL_KINETIC: Fast construction and useful for large systems.\n• FULL_S_INVERSE: Overlap-matrix-based preconditioning.\n\nFor unstable periodic Raman response calculations, FULL_ALL may be tested together with a suitable ENERGY_GAP. Convergence is not guaranteed.', 'vib.linres_preconditioner_help'),
        # ui/vibrational_panel.py:104
        QCoreApplication.translate("CP2KStudio", 'Raman Linear Response', 'vib.linres_title'),
        # core/vibrational.py:106
        QCoreApplication.translate("CP2KStudio", 'VIBRATIONAL_ANALYSIS / Raman: LINRES EPS is looser than 1e-7; test polarizability-response convergence.', 'vib.linres_warning'),
        # ui/vibrational_panel.py:22
        QCoreApplication.translate("CP2KStudio", 'Frequencies and normal modes are always computed. IR dipole moments and Raman linear-response polarizabilities can be enabled independently or together in one Hessian workflow. NONE uses molecular operators; XYZ uses Berry-phase operators for insulating Gamma-point supercells. Partial-periodic spectra are not supported. Use a stationary structure and converged forces.', 'vib.mode_help'),
        # ui/vibrational_panel.py:21
        QCoreApplication.translate("CP2KStudio", 'Calculation Mode', 'vib.mode_title'),
        # ui/vibrational_panel.py:85
        QCoreApplication.translate("CP2KStudio", 'Write Molden Vibrations', 'vib.molden'),
        # core/presets.py:184
        QCoreApplication.translate("CP2KStudio", 'Vibrational Analysis', 'vib.name'),
        # ui/main_window.py:336
        QCoreApplication.translate("CP2KStudio", '06  Vibrational Analysis', 'vib.nav'),
        # ui/vibrational_panel.py:54
        QCoreApplication.translate("CP2KStudio", 'NPROC_REP · MPI Parallel Settings\n\nNPROC_REP is the number of MPI processes per vibrational replica, not the total MPI process count.\n\nNumber of replicas = total MPI processes ÷ NPROC_REP\n\nFor a total of 16 MPI processes:\n• NPROC_REP = 4: 4 replicas, each using 4 MPI processes.\n• NPROC_REP = 8: 2 replicas, each using 8 MPI processes.\n• NPROC_REP = 16: 1 replica using 16 MPI processes.\n\nRecommendations:\nNPROC_REP must be a positive integer and should normally divide the total MPI process count exactly.\n\nRunning multiple replicas concurrently may increase total memory use. If an out-of-memory (OOM) error occurs, reduce the total MPI process count, or increase NPROC_REP to reduce the number of concurrent replicas.', 'vib.nproc_help'),
        # core/vibrational.py:117
        QCoreApplication.translate("CP2KStudio", 'VIBRATIONAL_ANALYSIS: the implemented periodic Berry-phase intensity workflow requires integer, fully occupied orbitals, without smearing or ADDED_MOS. Metallic or fractionally occupied configurations are not supported; settings have not been changed.', 'vib.occupations_error'),
        # ui/vibrational_panel.py:18
        QCoreApplication.translate("CP2KStudio", '06 · Vibrational Analysis', 'vib.page_title'),
        # core/vibrational.py:114
        QCoreApplication.translate("CP2KStudio", 'VIBRATIONAL_ANALYSIS: {mode} with partial periodicity {periodic} is not supported by Studio. Intensity workflows support NONE (molecular operators) or XYZ (Berry-phase operators); boundary conditions have not been changed.', 'vib.partial_spectra_error'),
        # ui/vibrational_panel.py:187
        QCoreApplication.translate("CP2KStudio", 'Periodic IR + Raman: Berry-phase dipole moments and periodic polarizability response share one vibrational analysis.', 'vib.periodic_combined_hint'),
        # core/vibrational.py:118
        QCoreApplication.translate("CP2KStudio", 'VIBRATIONAL_ANALYSIS: periodic {mode} is experimental support for insulating, gapped 3D Quickstep/GPW Gamma-point supercells. Static configuration cannot establish an electronic gap or CP2K build support. XML validity is not a successful numerical intensity calculation; this workflow has not been numerically verified by Studio.', 'vib.periodic_experimental_info'),
        # core/export_notes_generator.py:13
        QCoreApplication.translate("CP2KStudio", 'Periodic intensity path: {mode}, CELL/PERIODIC XYZ, Quickstep/GPW with implicit Gamma-point sampling. IR uses MOMENTS/PERIODIC T and MAX_MOMENT 1; Raman uses LINRES/POLAR/PERIODIC_DIPOLE_OPERATOR T. IR and Raman are independent options; when both are selected, both property sections share one vibrational Hessian workflow.\nUse an insulating, gapped structure with integer occupations. Inspect Berry-phase polarization branch continuity for IR. FULLY_PERIODIC controls Hessian rotations and is retained as explicitly configured, not enabled automatically. Periodic Raman support is experimental; verify CP2K build capabilities and numerical response/intensity convergence. No numerical intensity calculation has been performed by Studio.\n', 'vib.periodic_export_notes'),
        # core/vibrational.py:126
        QCoreApplication.translate("CP2KStudio", 'VIBRATIONAL_ANALYSIS: A periodic cell is used with FULLY_PERIODIC F. CP2K will handle rotational modes accordingly. Consider whether FULLY_PERIODIC T is appropriate for the system.', 'vib.periodic_info'),
        # ui/vibrational_panel.py:189
        QCoreApplication.translate("CP2KStudio", 'Periodic IR: Intensities are computed using Berry-phase dipole moments.', 'vib.periodic_ir_hint'),
        # ui/vibrational_panel.py:197
        QCoreApplication.translate("CP2KStudio", 'Experimental periodic intensities require an insulating Gamma-point supercell. Verify the electronic gap, response convergence and CP2K runtime support; XML validity alone does not establish a successful spectrum calculation.', 'vib.periodic_note'),
        # ui/vibrational_panel.py:44
        QCoreApplication.translate("CP2KStudio", 'This feature depends on CP2K periodic linear response. Start with an insulating Gamma-point supercell and verify polarizability-response and intensity convergence. Support is experimental: XML syntax checks do not verify runtime success or the capabilities of the selected CP2K build.', 'vib.periodic_raman_help'),
        # ui/vibrational_panel.py:191
        QCoreApplication.translate("CP2KStudio", 'Periodic Raman: Polarizability response uses the periodic Berry-phase dipole operator.', 'vib.periodic_raman_hint'),
        # ui/vibrational_panel.py:84
        QCoreApplication.translate("CP2KStudio", 'TC_PRESSURE', 'vib.pressure_label'),
        # core/vibrational.py:85
        QCoreApplication.translate("CP2KStudio", 'VIBRATIONAL_ANALYSIS: the final INP does not match the selected {mode} / PERIODIC {periodic} workflow. Check INTENSITIES, FULLY_PERIODIC, Quickstep/GPW, boundary settings and the required molecular or Berry-phase property operator.', 'vib.property_path_error'),
        # ui/vibrational_panel.py:34
        QCoreApplication.translate("CP2KStudio", 'Raman Intensities', 'vib.raman'),
        # ui/vibrational_panel.py:199
        QCoreApplication.translate("CP2KStudio", 'Raman: isolated closed-shell molecules with OT and no smearing/ADDED_MOS. POLAR and DO_RAMAN are activated; response convergence still requires a CP2K run.', 'vib.raman_note'),
        # core/vibrational.py:104
        QCoreApplication.translate("CP2KStudio", 'VIBRATIONAL_ANALYSIS / Raman: the implemented workflow requires closed-shell OT, no smearing and no ADDED_MOS. Other linear-response configurations are not supported by Studio.', 'vib.raman_solver_error'),
        # core/vibrational.py:107
        QCoreApplication.translate("CP2KStudio", 'VIBRATIONAL_ANALYSIS / Raman: POLAR and DO_RAMAN are enabled. XML checks cannot certify response convergence or a successful Raman calculation; no numerical CP2K run has been performed.', 'vib.raman_unverified'),
        # core/vibrational.py:96
        QCoreApplication.translate("CP2KStudio", 'VIBRATIONAL_ANALYSIS / NPROC_REP: ranks per replica ({rep}) must not exceed MPI processes ({mpi}) and must divide that total exactly; OpenMP threads do not count as MPI ranks.', 'vib.replica_error'),
        # core/vibrational.py:128
        QCoreApplication.translate("CP2KStudio", 'VIBRATIONAL_ANALYSIS: FULLY_PERIODIC T retains rotations even for this nonperiodic molecule; review the intended mode analysis.', 'vib.rotations_warning'),
        # core/vibrational.py:98
        QCoreApplication.translate("CP2KStudio", 'VIBRATIONAL_ANALYSIS: EPS_SCF is greater than 1E-7. Consider tightening SCF convergence and test DX and grid convergence for reliable finite-difference frequencies.', 'vib.scf_warning'),
        # core/vibrational.py:99
        QCoreApplication.translate("CP2KStudio", 'VIBRATIONAL_ANALYSIS: Ensure the structure is sufficiently optimized, and check residual forces and imaginary frequencies.', 'vib.stationary_info'),
        # ui/vibrational_panel.py:83
        QCoreApplication.translate("CP2KStudio", 'TC_TEMPERATURE', 'vib.temperature_label'),
        # core/vibrational.py:122
        QCoreApplication.translate("CP2KStudio", 'VIBRATIONAL_ANALYSIS / THERMOCHEMISTRY: only an isolated gas-phase molecule with FULLY_PERIODIC F is supported.', 'vib.thermo_error'),
        # ui/vibrational_panel.py:82
        QCoreApplication.translate("CP2KStudio", 'THERMOCHEMISTRY', 'vib.thermo_label'),
        # core/vibrational.py:124
        QCoreApplication.translate("CP2KStudio", 'VIBRATIONAL_ANALYSIS / THERMOCHEMISTRY: confirm the isolated gas-phase harmonic approximation is appropriate; the application cannot infer this from the coordinates.', 'vib.thermo_warning'),
        # ui/windows_local_run_dialog.py:43
        QCoreApplication.translate("CP2KStudio", 'Browse…', 'winrun.browse'),
        # ui/windows_local_run_dialog.py:90
        QCoreApplication.translate("CP2KStudio", 'Browse CP2K Executable…', 'winrun.browse_executable'),
        # ui/windows_local_run_dialog.py:116
        QCoreApplication.translate("CP2KStudio", 'Checking CP2K --version and runtime DLL loading…', 'winrun.checking'),
        # ui/windows_local_run_dialog.py:61
        QCoreApplication.translate("CP2KStudio", 'Choose CP2K. Start Calculation checks --version and its runtime DLLs before launching.', 'winrun.choose_exe'),
        # core/windows_local_run.py:205
        QCoreApplication.translate("CP2KStudio", 'Validate the executable and confirm Start Calculation first.', 'winrun.confirm_first'),
        # core/windows_local_run.py:228
        QCoreApplication.translate("CP2KStudio", 'This native calculation launch was cancelled or superseded before execution. CP2K was not started.', 'winrun.console_cancelled'),
        # core/windows_local_run.py:222
        QCoreApplication.translate("CP2KStudio", '\nCP2K exit code: {exit_code}. Inspect output.out; exit status does not prove convergence.', 'winrun.console_exit'),
        # core/windows_local_run.py:223
        QCoreApplication.translate("CP2KStudio", 'Could not start native CP2K: {error}', 'winrun.console_failed'),
        # core/windows_local_run.py:227
        QCoreApplication.translate("CP2KStudio", 'Ctrl+C received; waiting for the native CP2K process to exit.', 'winrun.console_interrupted'),
        # core/windows_local_run.py:224
        QCoreApplication.translate("CP2KStudio", 'Existing output.out may contain a previous run. Showing its last lines is not a success indication; CP2K may overwrite this log.', 'winrun.console_old_log'),
        # core/windows_local_run.py:221
        QCoreApplication.translate("CP2KStudio", 'Calculation directory: {directory}\nWindows Native: one CP2K process, OpenMP threads {threads}\n{executable} -i input.inp -o output.out', 'winrun.console_running'),
        # core/windows_local_run.py:60
        QCoreApplication.translate("CP2KStudio", 'Cannot resolve an input dependency: {path}', 'winrun.dependency_error'),
        # core/windows_local_run.py:44
        QCoreApplication.translate("CP2KStudio", 'Select an extracted calculation folder containing input.inp.', 'winrun.directory_error'),
        # ui/windows_local_run_dialog.py:46
        QCoreApplication.translate("CP2KStudio", 'Runtime DLL Directory', 'winrun.dll_directory'),
        # core/windows_local_run.py:80
        QCoreApplication.translate("CP2KStudio", 'Runtime DLL Directory does not exist: {path}', 'winrun.dll_error'),
        # core/windows_local_run.py:211
        QCoreApplication.translate("CP2KStudio", 'CP2K EXE changed after validation. Reopen Local Run and check it again.', 'winrun.exe_changed'),
        # core/windows_local_run.py:78
        QCoreApplication.translate("CP2KStudio", 'Choose an existing native Windows CP2K .exe file.', 'winrun.exe_error'),
        # ui/windows_local_run_dialog.py:91
        QCoreApplication.translate("CP2KStudio", 'Windows Executable (*.exe)', 'winrun.exe_filter'),
        # ui/windows_local_run_dialog.py:45
        QCoreApplication.translate("CP2KStudio", 'CP2K Executable', 'winrun.executable'),
        # ui/windows_local_run_dialog.py:52
        QCoreApplication.translate("CP2KStudio", 'Execution Mode', 'winrun.execution_mode'),
        # core/windows_local_run.py:254
        QCoreApplication.translate("CP2KStudio", 'Native CP2K failed to start (exit {exit_code}). Check the calculation terminal. {detail}', 'winrun.failed_start'),
        # ui/windows_local_run_dialog.py:39
        QCoreApplication.translate("CP2KStudio", 'Calculation Folder', 'winrun.folder'),
        # core/windows_local_run.py:171
        QCoreApplication.translate("CP2KStudio", 'The Windows Local Run helper is missing. Restore the complete Portable folder.', 'winrun.helper_missing'),
        # core/windows_local_run.py:69
        QCoreApplication.translate("CP2KStudio", 'Cannot read input.inp or a referenced structure/database/restart file: {error}', 'winrun.input_error'),
        # core/windows_local_run.py:47
        QCoreApplication.translate("CP2KStudio", 'Missing input.inp in the calculation folder.', 'winrun.input_missing'),
        # core/windows_local_run.py:208
        QCoreApplication.translate("CP2KStudio", 'output.out appeared while configuring this run. CP2K may overwrite it. Click Start Calculation again to confirm, or Cancel.', 'winrun.log_appeared'),
        # ui/windows_local_run_dialog.py:86
        QCoreApplication.translate("CP2KStudio", 'Windows Native / Serial or OpenMP', 'winrun.mode'),
        # core/windows_local_run.py:89
        QCoreApplication.translate("CP2KStudio", 'Windows Native currently requires a verified Serial/OpenMP build, normally cp2k.sopt.exe or cp2k.ssmp.exe. MPI/WSL launch is not configured.', 'winrun.mode_error'),
        # ui/windows_local_run_dialog.py:83
        QCoreApplication.translate("CP2KStudio", 'Windows Native / {mode}', 'winrun.native_mode'),
        # core/windows_local_run.py:122
        QCoreApplication.translate("CP2KStudio", 'PowerShell was not found. Install or enable PowerShell to open independent Windows consoles.', 'winrun.no_terminal'),
        # ui/windows_local_run_dialog.py:66
        QCoreApplication.translate("CP2KStudio", 'Existing output.out may be overwritten by CP2K; other restart/trajectory outputs may also be written by the selected input. Studio does not delete or back up results. Check any previous terminals before starting. Cancel to preserve the folder.', 'winrun.old_output'),
        # ui/windows_local_run_dialog.py:56
        QCoreApplication.translate("CP2KStudio", 'Output File', 'winrun.output'),
        # ui/local_run_dialog.py:165
        QCoreApplication.translate("CP2KStudio", 'The calculation terminal opened, but the monitor could not be opened: {error}. Check the existing calculation terminal; do not repeat the calculation to reopen its monitor.', 'winrun.partial'),
        # core/windows_local_run.py:226
        QCoreApplication.translate("CP2KStudio", 'CP2K started, but local preferences could not be saved: {error}', 'winrun.preferences_error'),
        # core/windows_local_run.py:57
        QCoreApplication.translate("CP2KStudio", 'Preprocessed INP files cannot be checked reliably here. Select a self-contained exported package; input.inp was not changed.', 'winrun.preprocessor'),
        # core/windows_local_run.py:86
        QCoreApplication.translate("CP2KStudio", 'CP2K --version could not start successfully ({status}). Check Runtime DLL Directory, including libgfortran-5.dll for MSYS2 UCRT64. EXE existence alone does not verify its runtime.\n{detail}', 'winrun.probe_error'),
        # ui/windows_local_run_dialog.py:96
        QCoreApplication.translate("CP2KStudio", 'Start Calculation will verify this EXE and its runtime before launching.', 'winrun.recheck_exe'),
        # ui/windows_local_run_dialog.py:63
        QCoreApplication.translate("CP2KStudio", 'This run uses one native CP2K process and the threads shown above. Exported MPI/run.sh settings are not used or changed. Serial builds require 1 thread. Only run packages you trust.', 'winrun.run_scope'),
        # core/windows_local_run.py:91
        QCoreApplication.translate("CP2KStudio", 'The selected CP2K build is Serial. Set OpenMP Threads to 1, or choose cp2k.ssmp.exe.', 'winrun.serial_threads'),
        # ui/windows_local_run_dialog.py:70
        QCoreApplication.translate("CP2KStudio", 'Start Calculation', 'winrun.start'),
        # ui/local_run_dialog.py:167
        QCoreApplication.translate("CP2KStudio", 'Native CP2K started. A separate terminal follows output.out. Check the real CP2K exit code and output; startup does not prove convergence. Closing Studio or the monitor does not stop the calculation.', 'winrun.started'),
        # core/windows_local_run.py:201
        QCoreApplication.translate("CP2KStudio", 'Cannot open a Windows terminal: {error}', 'winrun.terminal_error'),
        # ui/windows_local_run_dialog.py:55
        QCoreApplication.translate("CP2KStudio", 'OpenMP Threads', 'winrun.threads'),
        # core/windows_local_run.py:75
        QCoreApplication.translate("CP2KStudio", 'OpenMP Threads must be a positive integer.', 'winrun.threads_error'),
        # ui/local_run_dialog.py:169
        QCoreApplication.translate("CP2KStudio", 'Windows terminal requests were sent, but CP2K startup is not confirmed. Inspect both terminals before retrying.', 'winrun.unconfirmed'),
        # ui/windows_local_run_dialog.py:60
        QCoreApplication.translate("CP2KStudio", 'Verified CP2K {version} · {mode}', 'winrun.verified'),
        # ui/structure_panel.py:121
        QCoreApplication.translate("CP2KStudio", 'Generate Simulation Box…', 'xsd.box_button'),
        # core/structure.py:70
        QCoreApplication.translate("CP2KStudio", 'A simulation box can only be generated for a nonempty nonperiodic structure.', 'xsd.box_structure'),
        # ui/simulation_box_dialog.py:18
        QCoreApplication.translate("CP2KStudio", 'Generate Simulation Box', 'xsd.box_title'),
        # core/xsd_import.py:138
        QCoreApplication.translate("CP2KStudio", 'XSD periodic cell is missing or degenerate; no cell will be invented.', 'xsd.cell'),
        # core/xsd_import.py:49
        QCoreApplication.translate("CP2KStudio", 'XSD contains no readable atoms.', 'xsd.empty'),
        # core/xsd_import.py:180
        QCoreApplication.translate("CP2KStudio", 'Expanded source XSD symmetry with ASE: {sites} asymmetric sites → {atoms} unit-cell atoms. Display images were excluded; the original cell vectors are unchanged.', 'xsd.expanded'),
        # core/xsd_import.py:198
        QCoreApplication.translate("CP2KStudio", 'Cannot import Materials Studio XSD: {detail}', 'xsd.failed'),
        # core/xsd_import.py:29
        QCoreApplication.translate("CP2KStudio", 'XSD coordinates, cell vectors and symmetry operators must contain the expected number of finite values.', 'xsd.finite'),
        # core/xsd_import.py:193
        QCoreApplication.translate("CP2KStudio", 'ASE XSD output does not match the validated elements, coordinate order or cell; import was cancelled.', 'xsd.mismatch'),
        # ui/structure_panel.py:370
        QCoreApplication.translate("CP2KStudio", '\nEnter a simulation box manually or generate one using the button below.', 'xsd.missing_box'),
        # ui/structure_panel.py:367
        QCoreApplication.translate("CP2KStudio", 'Non-periodic Molecule. Check vacuum and Poisson boundaries.', 'xsd.molecule_hint'),
        # ui/structure_panel.py:360
        QCoreApplication.translate("CP2KStudio", 'Periodic Structure · Confirm Periodicity: current PERIODIC {periodic}. ASE cannot reliably infer slab/wire boundaries from XSD; review the selector below. Vacuum size does not change PBC automatically.', 'xsd.periodic_hint'),
        # core/xsd_import.py:194
        QCoreApplication.translate("CP2KStudio", 'XSD imports elements, coordinates, cell and readable PBC only. Force fields, bond orders, formal charges, source constraints and display settings are not imported.', 'xsd.properties'),
        # core/xsd_import.py:77
        QCoreApplication.translate("CP2KStudio", 'XSD symmetry operators are incomplete or duplicated for the declared space group; expansion was refused.', 'xsd.symmetry_count'),
        # core/xsd_import.py:20
        QCoreApplication.translate("CP2KStudio", 'Unsupported XSD layout: expected one Molecule or SymmetrySystem with explicit Atom3d elements and one cell. Modified symmetry images, mixed occupancies and nested systems are not supported.', 'xsd.unsupported'),
    ]
