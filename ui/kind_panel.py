"""Element-aware selectors backed exclusively by parsed, versioned data."""
from i18n.messages import i18n_msg, i18n_str, i18n_join
from copy import deepcopy
from pathlib import Path
from PySide6.QtCore import Qt, Signal
from i18n.qt import (QLabel,QTableWidget,QTableWidgetItem,QHeaderView,QPushButton,QFileDialog,
    QHBoxLayout,QVBoxLayout,QWidget,QCheckBox,QComboBox,QCompleter,QLineEdit,QDialog,QFrame,
    QScrollArea,QSizePolicy)
from ui.forms import FormPanel
from ui.widgets.section_card import SectionCard, AdaptiveGrid
from ui.widgets.status_badge import StatusBadgeDelegate, STATUS_ROLE
from core.models import Project, DatabaseSettings, Kind
from core.kind_validator import project_catalog,resource_paths,validate_kinds,configured_kind_labels
from ui.database_dialog import DatabaseDialog
from ui.theme import COLORS


class SearchCombo(QComboBox):
    selected = Signal(object)

    def __init__(self,entries,current_name='',reference=None,parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setMinimumWidth(90)
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(10)
        self.setMaxVisibleItems(18)
        self.addItem(i18n_msg('— Not selected; type to search —', code='studio.d1fc96246334d968'),None)
        selected_index=0
        for entry in entries:
            # A single row includes all aliases, so searching an alias never
            # creates a second, unrelated basis/potential record.
            label=entry.name+' · '+Path(entry.path).name
            if entry.aliases:
                label += ' · alias: '+i18n_join(', ', entry.aliases)
            self.addItem(label,entry)
            index=self.count()-1
            self.setItemData(index,entry.description+'\n'+entry.path+'\nSHA256 '+entry.file_sha256,Qt.ItemDataRole.ToolTipRole)
            if current_name in entry.names and (not reference or entry.path==i18n_str(Path(reference['path']).expanduser().resolve())):
                selected_index=index
        if current_name and not selected_index:
            self.addItem(current_name+i18n_msg(' · Original entry not loaded / filtered out (preserved)', code='studio.9b9cb33eea4144d3'),None)
            selected_index=self.count()-1
        self.setCurrentIndex(selected_index)
        self._display_name=current_name
        self.restore_selection_text()
        self.view().setMinimumWidth(650)
        completer=QCompleter(self.model(),self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.setCompleter(completer)
        self.activated.connect(self.choose)
        completer.activated[str].connect(self.complete)
        self.lineEdit().editingFinished.connect(self.restore_selection_text)

    def restore_selection_text(self):
        # Search text is not a parameter value until an actual option is chosen.
        entry=self.currentData()
        self.setEditText(self._display_name if self.currentIndex()>0 else '')
        self.lineEdit().setPlaceholderText(i18n_msg('Not selected · Type to search', code='studio.b3c03a0a71860d95'))
        self.lineEdit().setCursorPosition(0)

    def choose(self,index):
        entry=self.itemData(index)
        self._display_name=entry.name if entry else ''
        self.restore_selection_text()
        self.selected.emit(self.itemData(index))

    def complete(self,text):
        index=self.findText(text)
        if index>=0:
            self.setCurrentIndex(index)
            self.choose(index)


class KindTable(QTableWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # One header policy handles splitter/viewport changes, including the
        # appearance of scrollbars. Data refreshes never reset these widths.
        header = self.horizontalHeader()
        header.setSectionsMovable(False)
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(40)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 70)
        header.resizeSection(3, 160)


class CandidateFilterGrid(QScrollArea):
    """Keep four filters on one row; only this row scrolls in narrow pages."""
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.row = AdaptiveGrid(columns=4, threshold=0)
        self.row.grid.setHorizontalSpacing(8)
        self.setWidget(self.row)

    def add_field(self, label, control):
        container = self.row.add_field(label, control)
        for column in range(4):
            self.row.grid.setColumnStretch(column, 1 if column < 3 else 0)
        self._fit_contents()
        return container

    def _fit_contents(self):
        self.row.setMinimumWidth(self.row.grid.minimumSize().width())
        height = self.row.sizeHint().height()
        if self.contentsRect().width() < self.row.minimumWidth():
            height += self.horizontalScrollBar().sizeHint().height()
        if self.height() != height:
            self.setFixedHeight(height)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_contents()


class KindPanel(FormPanel):
    configuration_updated = Signal(object)

    def __init__(self):
        super().__init__(i18n_msg('05 · Basis Sets & Pseudopotentials', code='studio.b5ea402fe0d220b2'))
        self.layout.removeItem(self.form)
        self._records={}
        self._elements={}
        self._data=Project().model_dump()
        self.current_project=Project()
        self.settings=DatabaseSettings()
        self.catalog=project_catalog(Project())
        self._xc=None
        self._building=False
        self.database_card=SectionCard(i18n_msg('Database Files', code='studio.48f7454669e02185'), help_text=self.database_summary())
        row=QHBoxLayout()
        manage=QPushButton(i18n_msg('Database Manager…', code='studio.cd1ec226a7396f90'));manage.clicked.connect(self.manage_databases)
        suggest=QPushButton(i18n_msg('Recommend…', code='studio.495427d709e4ee6a'));suggest.clicked.connect(self.show_recommendations)
        row.addWidget(suggest,1);row.addWidget(manage,1)
        self.database_card.content.addLayout(row)
        self.layout.addWidget(self.database_card)
        self.configuration_card=SectionCard(i18n_msg('Basis Set & Pseudopotential Configuration', code='studio.e0011b948d8d6541'))
        content=self.configuration_card.content
        self.filters=CandidateFilterGrid()
        filters=self.filters
        self.quality=QComboBox();self.quality.addItems([i18n_msg('All Qualities', code='studio.65b0f156dcafd4b4'),'SZV','DZVP','TZVP','TZV2P','QZVPP']);filters.add_field(i18n_msg('Quality', code='studio.55847d2e5bed2ac5'),self.quality)
        self.source_filter=QComboBox();self.source_filter.addItem(i18n_msg('All Sources', code='studio.9f357adb6100face'));filters.add_field(i18n_msg('Source', code='studio.a488e93d69cc1296'),self.source_filter)
        self.xc_filter=QComboBox()
        for text, key in [(i18n_msg('All XC', code='studio.7d86678c5d4dfa0d'), 'all'),
                          (i18n_msg('Current XC', code='studio.f2be0d642eeb4969'), 'current'),
                          ('PBE','PBE'), ('BLYP','BLYP'), ('PADE','PADE')]:
            self.xc_filter.addItem(text, key)
        filters.add_field('XC',self.xc_filter)
        self.q_filter=QLineEdit();self.q_filter.setPlaceholderText(i18n_msg('e.g. 6', code='studio.c9566523da347bed'));self.q_filter.setMinimumWidth(60);self.q_filter.setMaximumWidth(75);filters.add_field(i18n_msg('Valence q', code='studio.b163663a997add3d'),self.q_filter)
        for combo in [self.quality,self.source_filter,self.xc_filter]:
            combo.setMinimumContentsLength(6)
            combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        content.addWidget(filters)
        self.filter_note=QLabel()
        self.filter_note.setWordWrap(True)
        self.filter_note.setObjectName('muted')
        self.filter_note.hide()
        content.addWidget(self.filter_note)
        separator=QFrame();separator.setFrameShape(QFrame.Shape.HLine);separator.setFixedHeight(1)
        separator.setStyleSheet(i18n_msg('background:{p0}; border:0;', p0=COLORS["border"]))
        content.addWidget(separator)
        kind_title=QLabel(i18n_msg('Basis & Pseudopotential per KIND', code='studio.de04bcb2a5a35926'));kind_title.setObjectName('fieldLabel')
        content.addWidget(kind_title)
        for widget in [self.quality,self.source_filter,self.xc_filter]:
            widget.currentIndexChanged.connect(lambda *_:self.rebuild())
        self.q_filter.textChanged.connect(lambda *_:self.rebuild())
        self.table=KindTable(0,4)
        self.table.setItemDelegateForColumn(3,StatusBadgeDelegate(self.table))
        self.table.setHorizontalHeaderLabels(['KIND','BASIS_SET','POTENTIAL',i18n_msg('Status', code='studio.6320b4a8722a851f')])
        self.table.horizontalHeaderItem(0).setToolTip(i18n_msg('KIND label / actual ELEMENT', code='studio.9f1912c6ee43ee3e'))
        self.table.setMinimumHeight(110)
        content.addWidget(self.table)
        self.layout.addWidget(self.configuration_card)
        self.advanced_toggle=QCheckBox(i18n_msg('Advanced: manual files / custom data', code='studio.e73cb710f632a630'))
        self.database_card.content.addWidget(self.advanced_toggle)
        self.advanced=QWidget();advanced_layout=QVBoxLayout(self.advanced)
        # Keep the original file configuration available, now hidden by default.
        before=self.form
        from i18n.qt import QFormLayout
        self.form=QFormLayout();advanced_layout.addLayout(self.form)
        self.basis=self.add('dft.basis_files',i18n_msg('Basis Files (One per Line)', code='studio.b8c50ec53b4af5b4'),'lines')
        self.potential=self.add('dft.potential_files',i18n_msg('Pseudopotential Files (One per Line)', code='studio.e692e36d4768e8d7'),'lines')
        self.form=before
        buttons=QHBoxLayout()
        for category,label in [('basis',i18n_msg('Add Custom Basis Set…', code='studio.d3385bff4858c436')),('potential',i18n_msg('Add Custom Pseudopotential…', code='studio.7c9068cfbaf9b93c'))]:
            button=QPushButton(label);button.clicked.connect(lambda checked=False,c=category:self.add_custom(c));buttons.addWidget(button)
        advanced_layout.addLayout(buttons)
        self.database_card.content.addWidget(self.advanced)
        self.advanced.setVisible(False);self.advanced_toggle.toggled.connect(self.advanced.setVisible)
        self.advanced_toggle.toggled.connect(lambda *_:self.changed.emit())
        self.layout.addStretch()
        self.update_summary()

    def database_summary(self):
        loaded=[s for s in self.catalog.statuses if s.entries]
        versions=i18n_join('、', dict.fromkeys(s.version for s in loaded if s.version)) or self.current_project.cp2k_version
        return (i18n_msg('Loaded: ', code='studio.83948700a8b72d85')+ i18n_join('、', dict.fromkeys(Path(s.path).name for s in loaded)) +
                i18n_msg('\nCP2K {p0} · ', p0=versions)+i18n_str(sum(s.entries for s in loaded))+i18n_msg(' records; open Database Manager for paths, fingerprints, and excluded records.', code='studio.4895fbbdbf0865a7'))

    def update_summary(self):
        loaded=[s for s in self.catalog.statuses if s.entries]
        self.database_card.help_icon.set_help_text(self.database_summary())
        current=self.source_filter.currentText()
        self.source_filter.blockSignals(True);self.source_filter.clear();self.source_filter.addItem(i18n_msg('All Sources', code='studio.9f357adb6100face'))
        self.source_filter.addItems(sorted({Path(s.path).name for s in loaded}))
        self.source_filter.setCurrentText(current if self.source_filter.findText(current)>=0 else i18n_msg('All Sources', code='studio.9f357adb6100face'))
        self.source_filter.blockSignals(False)
        quality=self.quality.currentText()
        self.quality.blockSignals(True);self.quality.clear();self.quality.addItem(i18n_msg('All Qualities', code='studio.65b0f156dcafd4b4'))
        self.quality.addItems(sorted({e.quality for e in self.catalog.entries if e.category=='basis' and e.quality}))
        self.quality.setCurrentText(quality if self.quality.findText(quality)>=0 else i18n_msg('All Qualities', code='studio.65b0f156dcafd4b4'))
        self.quality.blockSignals(False)

    def _match_legacy(self,data):
        p=Project.model_validate(data)
        basis,potential=resource_paths(p,self.catalog)
        for label,element in self._elements.items():
            record=self._records.setdefault(label,Kind(element=element).model_dump())
            record['element']=record.get('element') or element
            for category,field,paths in [('basis','basis_set',basis),('potential','potential',potential)]:
                ref_name='basis_ref' if category=='basis' else 'potential_ref'
                if not record.get(ref_name) and record.get(field):
                    matches=[e for path in paths for e in self.catalog.find(category,element,record[field],path)]
                    if matches:
                        record[ref_name]=matches[0].reference()

    def load(self,data):
        self._data=deepcopy(data)
        self.settings=DatabaseSettings.model_validate(data['databases'])
        self._records=deepcopy(data['kinds'])
        self._elements=dict(zip(data['structure'].get('kind_labels') or data['structure']['symbols'],data['structure']['symbols'])) if data['structure'] else {}
        self.catalog=project_catalog(Project.model_validate(data))
        self._xc=data['dft']['xc_functional']
        self._match_legacy(data)
        shown=deepcopy(data)
        shown['dft']['potential_files']=shown['dft']['potential_files'] or ([shown['dft']['potential_file']] if shown['dft']['potential_file'] else [])
        super().load(shown)
        self.update_summary();self.rebuild()

    def set_elements(self,elements,kinds):
        # Compatibility entry point; caller may pass element list or label->element.
        self._records=deepcopy(kinds)
        self._elements=dict(elements) if isinstance(elements,dict) else {s:s for s in elements}
        for label,element in self._elements.items():
            self._records.setdefault(label,Kind(element=element).model_dump())
        self.rebuild()

    def sync_structure(self,structure):
        mapping=structure.kind_elements if structure else {}
        if mapping!=self._elements:
            self._elements=mapping
            for label,element in mapping.items():
                self._records.setdefault(label,Kind(element=element).model_dump())
            self.rebuild()

    def set_xc(self,xc):
        if xc!=self._xc:
            self._xc=xc
            self.rebuild()

    def candidates(self,category,element):
        xc=self.xc_filter.currentData()
        xc=self._xc if xc=='current' else '' if xc=='all' else xc
        text=self.q_filter.text().strip()
        if text and not text.isdigit():
            return []
        return self.catalog.query(category,element,
            quality=self.quality.currentText() if category=='basis' and self.quality.currentIndex()>0 else '',
            source=self.source_filter.currentText() if self.source_filter.currentIndex()>0 else '',
            xc=xc or '',q=int(text) if text else None)

    def rebuild(self):
        if self._building:
            return
        self._building=True
        self.table.setRowCount(len(self._elements))
        self.table.setFixedHeight(max(110,min(360,34+44*len(self._elements))))
        pinned_count=0
        for row,(label,element) in enumerate(sorted(self._elements.items())):
            record=self._records.get(label,Kind(element=element).model_dump())
            item=QTableWidgetItem(label if label==element else i18n_msg('{p0} / {p1}', p0=label, p1=element))
            item.setToolTip(i18n_msg('KIND {p0}\nELEMENT {p1}', p0=label, p1=element))
            item.setData(Qt.ItemDataRole.UserRole,label)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row,0,item)
            for column,category,field,ref in [(1,'basis','basis_set','basis_ref'),(2,'potential','potential','potential_ref')]:
                entries=self.candidates(category,element)
                reference=record.get(ref)
                pinned=False
                if reference:
                    actual=self.catalog.find(category,element,record.get(field,''),reference['path'])
                    if actual and not any(e.key==actual[0].key for e in entries):
                        # Pin the actual saved source even if equivalent copies
                        # were de-duplicated or the current filter hides it.
                        entries=[actual[0],*entries]
                        active_filter = (self.quality.currentIndex()>0
                            or self.source_filter.currentIndex()>0 or self.xc_filter.currentIndex()>0
                            or self.q_filter.text().strip())
                        equivalent = any(e.name==actual[0].name and e.content_sha256==actual[0].content_sha256 for e in entries[1:])
                        source_hidden = self.source_filter.currentIndex()>0 and Path(actual[0].path).name!=self.source_filter.currentText()
                        pinned=bool(active_filter and (not equivalent or source_hidden))
                        pinned_count+=int(pinned)
                combo=SearchCombo(entries,record.get(field,''),record.get(ref),self.table)
                # The cell owns its geometry; a narrow splitter must not let
                # the editor's minimum width overlap its neighbouring column.
                combo.setMinimumWidth(0)
                if pinned:
                    combo.setProperty('pinned',True)
                    combo.setToolTip(i18n_msg('The current selection does not match these filters and has been preserved. Filtering never changes the configuration.\n', code='studio.8d52f428a7b4d0d5')+record.get(field,'')+'\n'+reference['path'])
                else:
                    combo.setToolTip(record.get(field,'')+'\n'+(reference['path'] if reference else i18n_msg('Select an actual database entry', code='studio.9ca0f694480bfc6e')))
                combo.selected.connect(lambda entry,l=label,c=category:self.choose(l,c,entry))
                self.table.setCellWidget(row,column,combo)
            self.table.setRowHeight(row,42)
        self._building=False
        self.filter_note.setText(i18n_msg('{p0} selected entries do not match the current filters and remain selected.', code='studio.b7d12343f4ff282c', p0=pinned_count) if pinned_count else '')
        self.filter_note.setVisible(bool(pinned_count))
        self.update_status()

    def choose(self,label,category,entry):
        record=self._records.setdefault(label,Kind(element=self._elements[label]).model_dump())
        field='basis_set' if category=='basis' else 'potential'
        ref='basis_ref' if category=='basis' else 'potential_ref'
        record[field]=entry.name if entry else ''
        record[ref]=entry.reference() if entry else None
        record['element']=self._elements[label]
        self.update_status();self.changed.emit()

    def collect(self,data,paths=None):
        errors=super().collect(data)
        data['kinds']=deepcopy(self._records)
        data['databases']=self.settings.model_dump()
        # Once actual selections are present, normal mode records precisely
        # the needed files without requiring manual path editing.
        if not self.advanced_toggle.isChecked():
            for ref,field in [('basis_ref','basis_files'),('potential_ref','potential_files')]:
                chosen=[self._records[l].get(ref) for l in self._elements if l in self._records]
                paths=[r['path'] for r in chosen if r]
                if paths:
                    data['dft'][field]=list(dict.fromkeys(paths))
            for widget,field in [(self.basis,'basis_files'),(self.potential,'potential_files')]:
                text=i18n_join('\n', data['dft'][field])
                if widget.toPlainText()!=text:
                    widget.blockSignals(True);widget.setPlainText(text);widget.blockSignals(False)
        data['dft']['potential_file']=next(iter(data['dft']['potential_files']),'')
        self._data=deepcopy(data)
        return errors

    def update_status(self,project=None):
        committed = project is not None
        try:
            if project is None:
                data=deepcopy(self._data);data['kinds']=deepcopy(self._records)
                data['dft']['xc_functional']=self._xc
                project=Project.model_validate(data)
            result=validate_kinds(project,self.catalog)
            self.last_validation=result
            for row in range(self.table.rowCount()):
                label=self.table.item(row,0).data(Qt.ItemDataRole.UserRole)
                issues=[i for i in result.issues if i.label==label]
                severity=next((s for s in ['Error','Warning','Info'] if any(i.severity==s for i in issues)),'Info')
                selected=result.selected.get(label,{})
                basis,potential=selected.get('basis'),selected.get('potential')
                q=basis.q if basis and potential and basis.q is not None and basis.q==potential.q else None
                state='error' if severity=='Error' else 'warning' if severity=='Warning' else 'ready' if q is not None else 'unchecked'
                text=i18n_msg('× Fix required', code='studio.f1f14e53c154f562') if state=='error' else i18n_msg('! Review', code='studio.2c9b3c21bcd90fdd') if state=='warning' else i18n_msg('✓ q={p0} matched', code='studio.5d391c3fa733b5fd', p0=q) if state=='ready' else i18n_msg('○ Info', code='studio.38401e4efcf55c16')
                item=QTableWidgetItem(text)
                item.setData(STATUS_ROLE,state)
                item.setToolTip(i18n_join('\n', (i.severity+' · '+i.message for i in issues))+i18n_msg('\nA q match is a specific consistency check, not a guarantee of physical applicability, accuracy, or convergence.', code='studio.0e8291844148fd26'))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row,3,item)
        except ValueError:
            pass
        if committed:
            self.current_project = project
            self.configuration_updated.emit(project)

    def manage_databases(self):
        dialog=DatabaseDialog(self.settings,self)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            self.settings=dialog.settings
            self.catalog=dialog.catalog
            # Project references are included again to retain copied/custom files.
            data=deepcopy(self._data);data['databases']=self.settings.model_dump();data['kinds']=deepcopy(self._records)
            self.catalog=project_catalog(Project.model_validate(data))
            self.update_summary();self.rebuild();self.changed.emit()

    def add_custom(self,category):
        from core.models import CustomDatabase
        paths,_=QFileDialog.getOpenFileNames(self,i18n_msg('Explicitly Add CP2K 2026.1 Data (User-Declared Version)', code='studio.8ad5f0067f16f480'))
        if paths:
            self.settings.custom_files += [CustomDatabase(path=p,category=category,version='2026.1') for p in paths]
            data=deepcopy(self._data);data['databases']=self.settings.model_dump();data['kinds']=deepcopy(self._records)
            self.catalog=project_catalog(Project.model_validate(data))
            self.update_summary();self.rebuild();self.changed.emit()

    def show_recommendations(self):
        from ui.recommendation_dialog import RecommendationDialog
        dialog = RecommendationDialog(self)
        try:
            dialog.exec()
        finally:
            from shiboken6 import isValid
            if isValid(dialog):
                dialog.deleteLater()

    def apply_recommendation(self,label,option):
        if label not in self._elements:
            raise ValueError(i18n_msg('KIND {p0} is no longer in the current structure', code='studio.093c56cd9eb20622', p0=label))
        record = deepcopy(self._records.get(label, Kind(element=self._elements[label]).model_dump()))
        record.update(element=self._elements[label], basis_set=option.basis.name, potential=option.potential.name,
                      basis_ref=option.basis.reference(), potential_ref=option.potential.reference(),
                      recommendation={'used':True,'basis_set':option.basis.name,'potential':option.potential.name,'note':option.note})
        trial = self.current_project.model_copy(deep=True)
        trial.kinds[label] = Kind.model_validate(record)
        # Match normal-mode file collection before validating the proposed pair.
        if not self.advanced_toggle.isChecked():
            records = {**self._records, label: record}
            for ref, field in [('basis_ref', 'basis_files'), ('potential_ref', 'potential_files')]:
                paths = [records[key][ref]['path'] for key in self._elements
                         if records.get(key, {}).get(ref)]
                if paths:
                    setattr(trial.dft, field, list(dict.fromkeys(paths)))
            trial.dft.potential_file = next(iter(trial.dft.potential_files), '')
        if label not in configured_kind_labels(trial, self.catalog):
            errors = [issue.message for issue in validate_kinds(trial, self.catalog).issues
                      if issue.label == label and issue.severity == 'Error']
            raise ValueError(i18n_join('；', errors) or i18n_msg('A recommended source file is missing, changed, or has an invalid version. Reload the database.', code='studio.50ba1a15709f090b'))
        previous = self._records
        self._records = {**previous, label: record}
        try:
            self.rebuild()
        except Exception:
            self._records = previous
            self.rebuild()
            raise
        self.changed.emit()
        if self.current_project.kinds.get(label) != trial.kinds[label]:
            # An invalid numeric draft can prevent the main window committing
            # the model. Do not report a successful Apply or retain half a draft.
            self._records = previous
            self.rebuild()
            self.changed.emit()
            raise ValueError(i18n_msg('The current project has invalid draft parameters; the recommendation was not committed. Correct them and retry.', code='studio.58c28c6010cc6251'))
