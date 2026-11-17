"""Navigation states derived from the same local report as step 08."""
from i18n.messages import i18n_msg, i18n_join
from dataclasses import dataclass, field
from PySide6.QtCore import Qt
from ui.export_panel import error_page
from ui.widgets.status_badge import STATUS_ROLE


@dataclass
class StepState:
    state: str = 'ready'
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def description(self):
        label = {'ready': i18n_msg('Required settings are complete; no known blocking errors', code='studio.afabec563bb0bd23'), 'warning': i18n_msg('Nonblocking warnings are present', code='studio.69a081b6e4703570'),
                 'error': i18n_msg('Configuration is incomplete or invalid', code='studio.9fb5ee285638ac47'), 'na': i18n_msg('ENERGY does not require geometry optimization', code='studio.5b89963a22120553'),
                 'unchecked': i18n_msg('Checking parameters', code='studio.f10d1173404b37af')}[self.state]
        return i18n_join('\n', [label, *self.errors, *self.warnings,
                          i18n_msg('Configuration status does not certify numerical accuracy, physical applicability, or convergence.', code='studio.11860e89fffe2870')])


def step_states(project, result, *, run_type=None, checked=False):
    states = [StepState() for _ in range(8)]
    for severity, messages in [('errors', result.errors), ('warnings', result.warnings)]:
        for message in messages:
            index = error_page(message)[0]
            if index >= 0:
                getattr(states[index], severity).append(message)
            getattr(states[7], severity).append(message)
    for status in states:
        status.state = 'error' if status.errors else 'warning' if status.warnings else 'ready'
    if (run_type or project.global_settings.run_type) == 'ENERGY':
        states[5] = StepState('na')
    if not checked:
        states[7].state = 'unchecked'
    return states


def show_step_states(nav, states):
    for index, status in enumerate(states):
        item = nav.item(index)
        item.setData(STATUS_ROLE, status.state)
        item.setToolTip('')
        item.setStatusTip('')
        description = item.text() + '\n' + status.description()
        if index == 7 and status.state == 'unchecked':
            description = (item.text() + i18n_msg('\nNot validated yet, or configuration changed. Click “Validate Configuration” in step 08.\n', code='studio.73decc9a48e4a1b5')
                           + i18n_join('\n', [*status.errors, *status.warnings,
                               i18n_msg('Configuration status does not certify numerical accuracy, physical applicability, or convergence.', code='studio.11860e89fffe2870')]))
        item.setData(Qt.ItemDataRole.AccessibleDescriptionRole, description)
    nav.viewport().update()
