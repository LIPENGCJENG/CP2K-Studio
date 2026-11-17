"""Drive the actual shared box dialog without a blocking modal event loop."""
from ui.simulation_box_dialog import SimulationBoxDialog
from i18n.qt import QDialog


def mock_box_dialog(monkeypatch, *, margin=None, mode='VACUUM_PADDING', lengths=None,
                    accepted=True, on_open=None):
    def execute(dialog):
        if on_open:
            on_open(dialog)
        dialog.mode.setCurrentIndex(dialog.mode.findData(mode))
        if margin is not None:
            (dialog.cubic_padding if mode == 'CUBIC' else dialog.padding).setValue(margin)
        if lengths is not None:
            for spin, value in zip(dialog.lengths, lengths):
                spin.setValue(value)
        if accepted:
            dialog.accept()
            if dialog.generated_structure is not None:
                return QDialog.DialogCode.Accepted
        dialog.reject()
        return QDialog.DialogCode.Rejected
    monkeypatch.setattr(SimulationBoxDialog, 'exec', execute)
