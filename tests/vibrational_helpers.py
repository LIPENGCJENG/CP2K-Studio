"""Test case labels are conveniences; production state uses only switches."""
FLAGS = {'FREQUENCIES': (False, False), 'IR': (True, False),
         'RAMAN': (False, True), 'IR+RAMAN': (True, True)}


def set_model_spectra(config, label):
    config.ir_enabled, config.raman_enabled = FLAGS[label]


def set_ui_spectra(panel, label):
    ir, raman = FLAGS[label]
    panel.ir_enabled.setChecked(ir)
    panel.raman_enabled.setChecked(raman)
