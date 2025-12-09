from PySide6.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QCheckBox, QComboBox, QSpinBox, QGroupBox,
    QDialog, QDialogButtonBox, QInputDialog, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt
import time
import json
import re

from data_models import APIConfig, DynamicData
from executor import run_apis
from pdf_generator import generate_pdf
from config_manager import load_config_json, save_config_json


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cliente REST JSON Productivo")
        self.setMinimumSize(1100, 700)

        self.config_data = load_config_json()
        self.dynamic_data = []
        self.results = []
        self.editing_row = None

        # Tabs
        self.tabs = QTabWidget()
        self.tab_apis = QWidget()
        self.tab_dynamic = QWidget()
        self.tab_summary = QWidget()
        self.tabs.addTab(self.tab_apis, "APIs")
        self.tabs.addTab(self.tab_dynamic, "Datos Dinámicos")
        self.tabs.addTab(self.tab_summary, "Resumen")

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

        # Setup tabs
        self.setup_tab_apis()
        self.setup_tab_dynamic()
        self.setup_tab_summary()
        self.load_config()

    def setup_tab_apis(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Token global (top row) + subtle theme toggle
        token_layout = QHBoxLayout()
        token_layout.addWidget(QLabel("Token Global:"))
        self.global_token_input = QLineEdit()
        token_layout.addWidget(self.global_token_input)
        token_layout.addStretch()
        # subtle, minimal theme toggle at top (text only)
        self.theme_toggle_btn = QPushButton("THEME")
        self.theme_toggle_btn.setCheckable(True)
        self.theme_toggle_btn.setFixedSize(140, 30)
        try:
            self.theme_toggle_btn.setStyleSheet("background: transparent; border: 1px solid rgba(0,0,0,0.08); border-radius: 6px; padding: 4px;")
        except Exception:
            pass
        self.theme_toggle_btn.clicked.connect(self.toggle_theme)
        token_layout.addWidget(self.theme_toggle_btn)
        main_layout.addLayout(token_layout)

        # Quick dynamic selector
        quick_dyn_layout = QHBoxLayout()
        quick_dyn_layout.addWidget(QLabel("Variable dinámica rápida:"))
        self.quick_dynamic_selector = QComboBox()
        self.quick_dynamic_selector.setFixedWidth(260)
        quick_dyn_layout.addWidget(self.quick_dynamic_selector)
        quick_dyn_layout.addStretch()
        main_layout.addLayout(quick_dyn_layout)

        # Quick preview
        quick_preview = QWidget()
        qp_layout = QVBoxLayout(quick_preview)
        qp_layout.setContentsMargins(0, 0, 0, 0)
        qp_layout.setSpacing(6)

        top_row = QWidget()
        top_h = QHBoxLayout(top_row)
        top_h.setContentsMargins(0, 0, 0, 0)
        top_h.setSpacing(6)
        top_h.addWidget(QLabel("Colección:"))
        self.quick_coll_selector = QComboBox()
        self.quick_coll_selector.setFixedWidth(220)
        top_h.addWidget(self.quick_coll_selector)
        top_h.addWidget(QLabel("Items:"))
        self.quick_coll_count = QLabel("0")
        top_h.addWidget(self.quick_coll_count)
        coll_quick_btn = QPushButton("Colecciones")
        coll_quick_btn.setFixedWidth(110)
        top_h.addWidget(coll_quick_btn)
        # (removed quick 'Editar' and 'Eliminar' buttons from main quick preview per user request)
        top_h.addStretch()
        self.cycle_quick_btn = QPushButton("⟳")
        self.cycle_quick_btn.setFixedSize(26, 22)
        # make it non-default so Enter key doesn't accidentally trigger it
        try:
            self.cycle_quick_btn.setAutoDefault(False)
        except Exception:
            pass

        

        
        self.cycle_quick_btn.setEnabled(True)
        self.cycle_quick_btn.setToolTip('Ciclar la colección rápida')
        top_h.addWidget(self.cycle_quick_btn)

        qp_layout.addWidget(top_row)

        self.quick_preview_text = QTextEdit()
        # editable by default as requested
        self.quick_preview_text.setReadOnly(False)
        self.quick_preview_text.setFixedHeight(140)
        qp_layout.addWidget(self.quick_preview_text)

        main_layout.addWidget(quick_preview)

        # API table and edit panel
        principal_layout = QHBoxLayout()
        principal_layout.setSpacing(20)

        self.api_table = QTableWidget(0, 5)
        self.api_table.setHorizontalHeaderLabels(["#", "✓", "Nombre", "URL", "Método"])
        header = self.api_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.api_table.verticalHeader().setVisible(False)
        self.api_table.setAlternatingRowColors(True)
        self.api_table.cellClicked.connect(self.api_row_clicked)
        principal_layout.addWidget(self.api_table, 2)

        # edit panel
        self.edit_panel = QGroupBox("Editar API")
        edit_layout = QVBoxLayout()
        self.name_input = QLineEdit()
        self.url_input = QLineEdit()
        self.method_input = QComboBox()
        self.method_input.addItems(["GET", "POST", "PUT", "DELETE"]) 
        self.token_input = QLineEdit()
        for label_text, widget in [("Nombre:", self.name_input), ("URL:", self.url_input), ("Método:", self.method_input), ("Token (opcional):", self.token_input)]:
            edit_layout.addWidget(QLabel(label_text))
        edit_layout.addWidget(QLabel("Body (JSON o template):"))
        self.body_editor = QTextEdit()
        edit_layout.addWidget(self.body_editor)
        edit_layout.addWidget(QLabel("Headers (JSON):"))
        self.headers_editor = QTextEdit()
        edit_layout.addWidget(self.headers_editor)
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Guardar cambios")
        add_api_btn = QPushButton("Agregar nueva API")
        save_btn.clicked.connect(self.save_api_edits)
        add_api_btn.clicked.connect(self.add_new_api)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(add_api_btn)
        edit_layout.addLayout(btn_layout)
        self.edit_panel.setLayout(edit_layout)
        principal_layout.addWidget(self.edit_panel, 1)

        main_layout.addLayout(principal_layout)

        footer = QHBoxLayout()
        footer.addStretch()
        # config load/save buttons
        self.load_cfg_btn = QPushButton("Cargar Config")
        self.load_cfg_btn.setFixedSize(120, 34)
        self.load_cfg_btn.clicked.connect(self._on_load_config_clicked)
        footer.addWidget(self.load_cfg_btn)

        self.save_cfg_btn = QPushButton("Guardar Config")
        self.save_cfg_btn.setFixedSize(120, 34)
        self.save_cfg_btn.clicked.connect(self._on_save_config_clicked)
        footer.addWidget(self.save_cfg_btn)
        # single toggle button to select/deselect all APIs
        self.toggle_select_btn = QPushButton("Seleccionar todo")
        self.toggle_select_btn.setCheckable(True)
        self.toggle_select_btn.setFixedSize(160, 34)
        self.toggle_select_btn.clicked.connect(self.toggle_select_all)
        footer.addWidget(self.toggle_select_btn)

        self.run_tests_btn = QPushButton("Ejecutar Pruebas")
        self.run_tests_btn.setFixedSize(160, 44)
        self.run_tests_btn.clicked.connect(self.execute_requests)
        footer.addWidget(self.run_tests_btn)

    # footer continues (run/config buttons kept minimal)

        main_layout.addLayout(footer)

        self.tab_apis.setLayout(main_layout)

        # connect quick controls
        self.quick_dynamic_selector.currentIndexChanged.connect(self._on_quick_dynamic_changed)
        self.quick_coll_selector.currentIndexChanged.connect(self._on_quick_coll_changed) 
        # connect only to clicked and debounce in the handler to avoid double-firing
        try:
            self.cycle_quick_btn.clicked.connect(self._cycle_quick_collection)
        except Exception:
            pass
        coll_quick_btn.clicked.connect(lambda: self._perform_action_on_quick('Colecciones'))

    def setup_tab_dynamic(self):
        layout = QVBoxLayout()
        self.dynamic_table = QTableWidget(0, 4)
        self.dynamic_table.setHorizontalHeaderLabels(["Key", "Count", "Preview", "Acciones"])
        h = self.dynamic_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.Stretch)
        h.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.dynamic_table.verticalHeader().setVisible(False)
        # Give rows a reasonable default height so preview widgets aren't compressed
        try:
            self.dynamic_table.verticalHeader().setDefaultSectionSize(160)
        except Exception:
            pass
        layout.addWidget(self.dynamic_table)

        btns = QHBoxLayout()
        add_btn = QPushButton("Agregar variable")
        add_btn.clicked.connect(self._add_dynamic_variable)
        btns.addWidget(add_btn)
        layout.addLayout(btns)
        self.tab_dynamic.setLayout(layout)

    def setup_tab_summary(self):
        l = QVBoxLayout()
        l.addWidget(QLabel("Resumen de ejecución"))
        # table for results: #, API, Status, Mapping, Response (snippet)
        self.summary_table = QTableWidget(0, 5)
        self.summary_table.setHorizontalHeaderLabels(["#", "API", "Status", "Mapping", "Response"])
        h = self.summary_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.Stretch)
        h.setSectionResizeMode(4, QHeaderView.Stretch)
        self.summary_table.verticalHeader().setVisible(False)
        self.summary_table.setAlternatingRowColors(True)
        l.addWidget(self.summary_table)
        self.tab_summary.setLayout(l)

    def update_summary(self, results: list):
        # results: list of dicts as returned by executor.run_apis
        try:
            self.summary_table.setRowCount(0)
            for i, r in enumerate(results):
                row = self.summary_table.rowCount()
                self.summary_table.insertRow(row)
                # index
                self.summary_table.setItem(row, 0, QTableWidgetItem(str(i+1)))
                # api name
                self.summary_table.setItem(row, 1, QTableWidgetItem(r.get('api_name', '<unnamed>')))
                # status
                status_text = str(r.get('status')) if r.get('status') is not None else 'ERR'
                self.summary_table.setItem(row, 2, QTableWidgetItem(status_text))
                # mapping compact
                try:
                    mapping_json = json.dumps(r.get('mapping', {}), ensure_ascii=False)
                except Exception:
                    mapping_json = str(r.get('mapping', {}))
                self.summary_table.setItem(row, 3, QTableWidgetItem(mapping_json))
                # response snippet
                text_snip = (r.get('text') or '')
                if isinstance(text_snip, str):
                    snippet = text_snip[:300]
                else:
                    try:
                        snippet = json.dumps(text_snip, ensure_ascii=False)[:300]
                    except Exception:
                        snippet = str(text_snip)[:300]
                self.summary_table.setItem(row, 4, QTableWidgetItem(snippet))
        except Exception:
            pass

    # ---------- config load/save ----------
    def load_config(self):
        cfg = self.config_data or {}
        # populate apis
        self.api_table.setRowCount(0)
        for i, a in enumerate(cfg.get('apis', [])):
            self.api_table.insertRow(i)
            self.api_table.setItem(i, 0, QTableWidgetItem(str(i+1)))
            # active checkbox
            cbw = QWidget()
            cb_layout = QHBoxLayout(cbw)
            cb_layout.setContentsMargins(0,0,0,0)
            cb = QCheckBox()
            cb.setChecked(a.get('active', True))
            cb_layout.addWidget(cb)
            cbw.setLayout(cb_layout)
            self.api_table.setCellWidget(i, 1, cbw)
            self.api_table.setItem(i, 2, QTableWidgetItem(a.get('name','')))
            self.api_table.setItem(i, 3, QTableWidgetItem(a.get('url','')))
            method_cb = QComboBox()
            method_cb.addItems(["GET","POST","PUT","DELETE"])
            try:
                method_cb.setCurrentText(a.get('method','GET'))
            except Exception:
                pass
            self.api_table.setCellWidget(i, 4, method_cb)
        # populate dynamics
        self.dynamic_table.setRowCount(0)
        for i, d in enumerate(cfg.get('dynamic', [])):
            key = d.get('key','')
            collections = d.get('collections', []) or [{"name":"default","values":d.get('values',[])}]
            # prefer an explicit last-used selection stored in meta if present
            meta = cfg.get('meta', {}) or {}
            last_used = meta.get('last_used_dynamic', {})
            selected = None
            if key and key in last_used:
                selected = last_used.get(key)
            if not selected:
                selected = d.get('selected') or (collections[0]['name'] if collections else 'default')
            self.add_dynamic_row(key, collections, selected)
        # populate quick selector
        self._populate_quick_dynamic_selector()
        # restore global token and quick selector last choice (if any)
        try:
            gtok = cfg.get('meta', {}).get('global_token', '')
            self.global_token_input.setText(gtok or '')
        except Exception:
            pass
        try:
            meta = cfg.get('meta', {}) or {}
            last_quick = meta.get('last_quick_dynamic')
            last_used_map = meta.get('last_used_dynamic', {}) or {}
            if last_quick:
                # only set if it exists in the combo
                idx = self.quick_dynamic_selector.findText(last_quick)
                if idx >= 0:
                    # set the quick dynamic (this triggers the handler which populates collections)
                    self.quick_dynamic_selector.setCurrentIndex(idx)
                    # ensure the quick collection selection matches meta.last_used_dynamic for this key
                    try:
                        wanted = last_used_map.get(last_quick)
                        if wanted:
                            # if the collection exists in the quick_coll_selector, set it
                            qidx = self.quick_coll_selector.findText(wanted)
                            if qidx >= 0:
                                self.quick_coll_selector.setCurrentIndex(qidx)
                            else:
                                # otherwise, try to fallback to the first available collection
                                if self.quick_coll_selector.count() > 0:
                                    # pick first available and persist that choice
                                    first_name = self.quick_coll_selector.itemText(0)
                                    try:
                                        self.quick_coll_selector.setCurrentIndex(0)
                                    except Exception:
                                        pass
                                    try:
                                        meta['last_used_dynamic'] = last_used_map
                                        # record that we fell back to first_name
                                        last_used_map[last_quick] = first_name
                                        meta['last_used_dynamic'][last_quick] = first_name
                                        self.config_data['meta'] = meta
                                        save_config_json(self.config_data)
                                    except Exception:
                                        pass
                                else:
                                    # as last resort, set preview property directly
                                    row, preview = self._find_dynamic_row_by_key(last_quick)
                                    if preview is not None:
                                        preview.setProperty('selected', wanted)
                    except Exception:
                        pass
        except Exception:
            pass

    def save_config(self):
        # persist api table and dynamic table
        apis = []
        for r in range(self.api_table.rowCount()):
            cbw = self.api_table.cellWidget(r,1)
            active = False
            if cbw is not None and cbw.layout() and cbw.layout().count()>0:
                active = cbw.layout().itemAt(0).widget().isChecked()
            name = self.api_table.item(r,2).text() if self.api_table.item(r,2) else ''
            url = self.api_table.item(r,3).text() if self.api_table.item(r,3) else ''
            method = self.api_table.cellWidget(r,4).currentText() if self.api_table.cellWidget(r,4) else 'GET'
            # preserve any existing body/body_raw/headers saved previously in config_data
            existing_apis = self.config_data.get('apis', []) if self.config_data else []
            existing_entry = existing_apis[r] if r < len(existing_apis) else {}
            # prefer structured body if present, otherwise preserve raw body text
            body = existing_entry.get('body') if 'body' in existing_entry else None
            body_raw = existing_entry.get('body_raw') if 'body_raw' in existing_entry else None
            headers = existing_entry.get('headers', {}) if existing_entry else {}
            api_entry = {"active": active, "name": name, "url": url, "method": method}
            if body is not None:
                api_entry['body'] = body
            elif body_raw is not None:
                api_entry['body_raw'] = body_raw
            else:
                api_entry['body'] = {}
            api_entry['headers'] = headers or {}
            apis.append(api_entry)
        self.config_data['apis'] = apis
        # dynamic
        dyn = []
        for r in range(self.dynamic_table.rowCount()):
            keyw = self.dynamic_table.cellWidget(r,0)
            key = ''
            if keyw is not None and hasattr(keyw, 'layout'):
                for i in range(keyw.layout().count()):
                    w = keyw.layout().itemAt(i).widget()
                    if hasattr(w, 'text'):
                        key = w.text()
                        break
            else:
                it = self.dynamic_table.item(r,0)
                key = it.text() if it else ''
            preview = self.dynamic_table.cellWidget(r,2)
            collections = preview.property('collections') if preview is not None else []
            selected = preview.property('selected') if preview is not None else None
            values = preview.property('values') if preview is not None else []
            if not collections:
                collections = [{"name":"default","values": values or []}]
                selected = 'default'
            dyn.append({"key":key, "collections":collections, "selected":selected})
        self.config_data['dynamic'] = dyn
        # update meta information
        try:
            meta = self.config_data.get('meta', {}) or {}
            meta['version'] = meta.get('version', '1.1')
            from datetime import datetime
            meta['last_saved'] = datetime.utcnow().isoformat() + 'Z'
            # global token from UI
            meta['global_token'] = self.global_token_input.text() if hasattr(self, 'global_token_input') else meta.get('global_token','')
            # last quick dynamic: only set if not already present (don't overwrite a value
            # that was intentionally set by row-level changes)
            try:
                if not meta.get('last_quick_dynamic'):
                    meta['last_quick_dynamic'] = self.quick_dynamic_selector.currentText()
            except Exception:
                pass
            # last used collection per dynamic key
            last_used = meta.get('last_used_dynamic', {}) or {}
            for r in range(self.dynamic_table.rowCount()):
                # key
                key = ''
                keyw = self.dynamic_table.cellWidget(r,0)
                if keyw is not None and hasattr(keyw, 'layout'):
                    for i in range(keyw.layout().count()):
                        w = keyw.layout().itemAt(i).widget()
                        if hasattr(w, 'text'):
                            key = w.text()
                            break
                else:
                    it = self.dynamic_table.item(r,0)
                    key = it.text() if it else ''
                pv = self.dynamic_table.cellWidget(r,2)
                sel = None
                try:
                    sel = pv.property('selected') if pv is not None else None
                except Exception:
                    sel = None
                if key:
                    last_used[key] = sel or last_used.get(key)
            meta['last_used_dynamic'] = last_used
            # persist theme preference if UI exposes it
            try:
                if hasattr(self, 'theme_toggle_btn'):
                    meta['theme'] = 'dark' if self.theme_toggle_btn.isChecked() else 'light'
                else:
                    meta['theme'] = meta.get('theme', 'light')
            except Exception:
                meta['theme'] = meta.get('theme', 'light')
            self.config_data['meta'] = meta
        except Exception:
            pass
        save_config_json(self.config_data)

    def _on_save_config_clicked(self):
        """Handler for the 'Guardar Config' button: persist current in-memory config to disk."""
        try:
            self.save_config()
            QMessageBox.information(self, 'Configuración', 'Configuración guardada correctamente.')
        except Exception as e:
            QMessageBox.warning(self, 'Error', f'No se pudo guardar la configuración: {e}')

    def _on_load_config_clicked(self):
        """Handler for the 'Cargar Config' button: reload config from disk and refresh UI."""
        try:
            self.config_data = load_config_json() or {}
            self.load_config()
            QMessageBox.information(self, 'Configuración', 'Configuración cargada desde disco.')
        except Exception as e:
            QMessageBox.warning(self, 'Error', f'No se pudo cargar la configuración: {e}')

        # after loading config, try to restore theme if present
        try:
            meta = self.config_data.get('meta', {}) or {}
            theme = meta.get('theme', 'light')
            try:
                is_dark = True if theme == 'dark' else False
                if hasattr(self, 'theme_toggle_btn'):
                    self.theme_toggle_btn.setChecked(is_dark)
                self.apply_theme(theme)
            except Exception:
                pass
        except Exception:
            pass

    # ---------- theme helpers ----------
    def toggle_theme(self, checked: bool | None = None):
        """Toggle between light and dark theme and persist choice in config."""
        try:
            if checked is None and hasattr(self, 'theme_toggle_btn'):
                checked = self.theme_toggle_btn.isChecked()
            theme = 'dark' if checked else 'light'
            # apply
            self.apply_theme(theme)
            # update UI button symbol
            try:
                if hasattr(self, 'theme_toggle_btn'):
                    self.theme_toggle_btn.setChecked(bool(checked))
            except Exception:
                pass
            # persist in config meta
            try:
                meta = self.config_data.get('meta', {}) or {}
                meta['theme'] = theme
                self.config_data['meta'] = meta
                save_config_json(self.config_data)
            except Exception:
                pass
        except Exception:
            pass

    def apply_theme(self, theme: str):
        """Apply a minimal theme stylesheet to the main window.

        theme: 'light' or 'dark'
        """
        try:
            if theme == 'dark':
                qss = """
                QWidget { background: #222; color: #eaeaea; }
                QLineEdit, QTextEdit, QPlainTextEdit { background: #2b2b2b; color: #eaeaea; border: 1px solid #3a3a3a; }
                QTableWidget { background: #252525; color: #eaeaea; gridline-color: #3a3a3a; }
                QHeaderView::section { background: #2b2b2b; color: #eaeaea; }
                QPushButton { background: transparent; color: #eaeaea; border: 1px solid rgba(255,255,255,0.03); padding: 4px; }
                QPushButton:checked { background: rgba(255,255,255,0.04); }
                QComboBox { background: #2b2b2b; color: #eaeaea; }
                """
            else:
                qss = """
                QWidget { background: #ffffff; color: #111; }
                QLineEdit, QTextEdit, QPlainTextEdit { background: #fff; color: #111; border: 1px solid #dcdcdc; }
                QTableWidget { background: #fff; color: #111; gridline-color: #eaeaea; }
                QHeaderView::section { background: #f3f3f3; color: #111; }
                QPushButton { background: transparent; color: #111; border: 1px solid rgba(0,0,0,0.03); padding: 4px; }
                QPushButton:checked { background: rgba(0,0,0,0.02); }
                QComboBox { background: #fff; color: #111; }
                """
            try:
                self.setStyleSheet(qss)
            except Exception:
                pass
        except Exception:
            pass

    def toggle_theme(self, checked: bool | None = None):
        """Toggle between light and dark theme. If checked is provided, use it; otherwise toggle current."""
        try:
            if checked is None:
                # toggle state
                if hasattr(self, 'theme_toggle_btn'):
                    new_state = not self.theme_toggle_btn.isChecked()
                else:
                    new_state = True
            else:
                new_state = bool(checked)
            if hasattr(self, 'theme_toggle_btn'):
                self.theme_toggle_btn.setChecked(new_state)
                self.theme_toggle_btn.setText('Dark' if new_state else 'Light')
            self.apply_theme('dark' if new_state else 'light')
            # persist immediately
            try:
                if not self.config_data:
                    self.config_data = {}
                meta = self.config_data.get('meta', {}) or {}
                meta['theme'] = 'dark' if new_state else 'light'
                self.config_data['meta'] = meta
                save_config_json(self.config_data)
            except Exception:
                pass
        except Exception:
            pass

    def apply_theme(self, theme: str):
        """Apply a minimal light/dark stylesheet to the application."""
        try:
            app = QApplication.instance()
            if app is None:
                return
            if theme == 'dark':
                dark_qss = """
                QWidget { background: #2b2b2b; color: #e6e6e6; }
                QLineEdit, QTextEdit, QPlainTextEdit { background: #3c3f41; color: #e6e6e6; }
                QTableWidget { background: #2b2b2b; color: #e6e6e6; gridline-color: #444; }
                QPushButton { background: #3c3f41; color: #e6e6e6; border: 1px solid #555; padding: 4px; }
                QPushButton:checked { background: #5a5f63; }
                QHeaderView::section { background: #3c3f41; color: #e6e6e6; }
                """
                app.setStyleSheet(dark_qss)
            else:
                app.setStyleSheet("")
        except Exception:
            pass

    # ---------- dynamic rows ----------
    def add_dynamic_row(self, key: str = "", collections: list | None = None, selected: str | None = None):
        if collections is None or not collections:
            collections = [{"name":"default","values":[]}]
        if selected is None:
            selected = collections[0]["name"]
        row = self.dynamic_table.rowCount()
        self.dynamic_table.insertRow(row)
        # key cell
        key_container = QWidget()
        kl = QHBoxLayout(key_container)
        kl.setContentsMargins(0,0,0,0)
        key_edit = QLineEdit()
        key_edit.setText(key)
        kl.addWidget(key_edit)
        key_container.setLayout(kl)
        self.dynamic_table.setCellWidget(row,0,key_container)
        # count
        sel_idx = 0
        for i,c in enumerate(collections):
            if c.get('name') == selected:
                sel_idx = i
                break
        current_values = collections[sel_idx].get('values', [])
        count_item = QTableWidgetItem(str(len(current_values)))
        count_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.dynamic_table.setItem(row,1,count_item)
        # preview container
        preview_container = QWidget()
        pv = QVBoxLayout(preview_container)
        pv.setContentsMargins(4,4,4,4)
        inner_top = QWidget()
        th = QHBoxLayout(inner_top)
        th.setContentsMargins(0,0,0,0)
        coll_selector = QComboBox()
        coll_selector.setFixedWidth(180)
        for coll in collections:
            coll_selector.addItem(coll.get('name'))
        try:
            coll_selector.setCurrentText(selected)
        except Exception:
            pass
        th.addWidget(coll_selector)
        th.addStretch()
        cycle_btn = QPushButton('⟳')
        cycle_btn.setFixedSize(26,22)
        th.addWidget(cycle_btn)
        pv.addWidget(inner_top)
        preview_text = QTextEdit()
        preview_text.setPlainText('\n'.join(current_values))
        preview_text.setReadOnly(False)  # editable by default
        preview_text.setFixedHeight(120)
        pv.addWidget(preview_text)
        preview_container.setProperty('collections', collections)
        preview_container.setProperty('selected', selected)
        preview_container.setProperty('values', current_values)
        preview_container.setStyleSheet('border-bottom: 1px solid rgba(0,0,0,0.06);')
        self.dynamic_table.setCellWidget(row,2,preview_container)
        # Ensure the row has enough height to show the preview text editor
        try:
            # prefer explicit fixed height if available
            h = preview_text.height() if hasattr(preview_text, 'height') else preview_text.sizeHint().height()
            # add some padding for controls above the preview
            self.dynamic_table.setRowHeight(row, h + 48)
        except Exception:
            try:
                # fallback to a reasonable fixed height
                self.dynamic_table.setRowHeight(row, 160)
            except Exception:
                pass
        # actions
        actions_w = QWidget()
        al = QVBoxLayout(actions_w)
        # small margins and moderate spacing; center vertically in the cell
        al.setContentsMargins(4,4,4,4)
        al.setSpacing(6)
        al.setAlignment(Qt.AlignVCenter)
        # vertical stacked buttons (Editar, Colecciones, Eliminar) with reduced spacing
        edit_btn = QPushButton('Editar')
        coll_btn = QPushButton('Colecciones')
        del_btn = QPushButton('Eliminar')
        # make buttons consistent and a bit narrower so they appear compact
        for b in (edit_btn, coll_btn, del_btn):
            # standard comfortable size
            b.setFixedHeight(28)
            b.setFixedWidth(130)
            b.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            # small padding so buttons are not visually cramped
            b.setStyleSheet("margin:0px; padding:4px 6px;")
        # ensure no extra spacing between stacked buttons
        al.setSpacing(0)
        al.addWidget(edit_btn)
        al.addWidget(coll_btn)
        al.addWidget(del_btn)
        # connect signals
        edit_btn.clicked.connect(lambda _, b=edit_btn: self._edit_dynamic_button_clicked(b))
        coll_btn.clicked.connect(lambda _, b=coll_btn: self._manage_collections_button_clicked(b))
        del_btn.clicked.connect(lambda _, b=del_btn: self._delete_dynamic_button_clicked(b))
        actions_w.setMaximumWidth(180)
        self.dynamic_table.setCellWidget(row,3,actions_w)
        # connect inner selector change to update preview
        def on_coll_changed(idx, row=row):
            try:
                pv_container = self.dynamic_table.cellWidget(row,2)
                inner_comb = None
                top_widget = pv_container.layout().itemAt(0).widget()
                if isinstance(top_widget, QComboBox):
                    inner_comb = top_widget
                elif hasattr(top_widget, 'layout'):
                    for i in range(top_widget.layout().count()):
                        w = top_widget.layout().itemAt(i).widget()
                        if isinstance(w, QComboBox):
                            inner_comb = w
                            break
                sel_name = coll_selector.currentText()
                sel_vals = []
                for c in preview_container.property('collections'):
                    if c.get('name') == sel_name:
                        sel_vals = c.get('values', [])
                        break
                preview_text.setPlainText('\n'.join(sel_vals))
                preview_container.setProperty('values', sel_vals)
                preview_container.setProperty('selected', sel_name)
                # update count
                try:
                    self.dynamic_table.item(row,1).setText(str(len(sel_vals)))
                except Exception:
                    pass
                # update runtime meta: last used collection for this key
                try:
                    k = key_edit.text() if key_edit is not None else None
                    if k:
                        meta = self.config_data.get('meta', {}) or {}
                        last_used = meta.get('last_used_dynamic', {}) or {}
                        last_used[k] = sel_name
                        # also record this key as the last quick dynamic so it is restored on startup
                        try:
                            meta['last_quick_dynamic'] = k
                        except Exception:
                            pass
                        meta['last_used_dynamic'] = last_used
                        self.config_data['meta'] = meta
                        # persist immediately so app restarts restore this choice
                        try:
                            save_config_json(self.config_data)
                        except Exception:
                            pass
                except Exception:
                    pass
            except Exception:
                pass
        coll_selector.currentIndexChanged.connect(on_coll_changed)
        def on_cycle(_checked=None, row=row):
            try:
                cnt = coll_selector.count()
                if cnt<=0: return
                coll_selector.setCurrentIndex((coll_selector.currentIndex()+1)%cnt)
            except Exception:
                pass
        cycle_btn.clicked.connect(on_cycle)

    # ---------- helpers for quick preview ----------
    def _populate_quick_dynamic_selector(self):
        self.quick_dynamic_selector.blockSignals(True)
        self.quick_dynamic_selector.clear()
        keys = []
        for r in range(self.dynamic_table.rowCount()):
            w = self.dynamic_table.cellWidget(r,0)
            key = ''
            if w is not None and hasattr(w, 'layout'):
                for i in range(w.layout().count()):
                    child = w.layout().itemAt(i).widget()
                    if hasattr(child, 'text'):
                        key = child.text()
                        break
            else:
                it = self.dynamic_table.item(r,0)
                key = it.text() if it else ''
            if key:
                keys.append(key)
        self.quick_dynamic_selector.addItems(keys)
        self.quick_dynamic_selector.blockSignals(False)

    def _on_quick_dynamic_changed(self, idx):
        key = self.quick_dynamic_selector.currentText()
        try:
            print(f"[ui] _on_quick_dynamic_changed key={key} idx={idx}")
        except Exception:
            pass
        row, preview = self._find_dynamic_row_by_key(key)
        collections = []
        # prefer the collections that exist in the live preview widget; if not present
        # fall back to the raw config_data (this handles cases where the UI rows
        # didn't populate exactly or the user edited the config.json externally).
        if preview is not None:
            try:
                collections = preview.property('collections') or []
            except Exception:
                collections = []
        if not collections:
            try:
                for d in (self.config_data.get('dynamic') or []):
                    if d.get('key') == key:
                        collections = d.get('collections', []) or []
                        # if config has an explicit selected, ensure preview reflects it
                        try:
                            sel = d.get('selected')
                            if preview is not None and sel:
                                preview.setProperty('selected', sel)
                                preview.setProperty('values', next((c.get('values',[]) for c in collections if c.get('name')==sel), []))
                        except Exception:
                            pass
                        break
            except Exception:
                collections = []
        if not collections:
            # nothing to show
            self.quick_coll_selector.clear()
            self.quick_preview_text.setPlainText('')
            self.quick_coll_count.setText('0')
            return
        self.quick_coll_selector.blockSignals(True)
        self.quick_coll_selector.clear()
        for c in collections:
            self.quick_coll_selector.addItem(c.get('name'))
        try:
            sel = preview.property('selected')
            if sel:
                try:
                    print(f"[ui] setting quick_coll_selector to stored preview.selected={sel}")
                except Exception:
                    pass
                self.quick_coll_selector.setCurrentText(sel)
        except Exception:
            pass
        self.quick_coll_selector.blockSignals(False)
        # update preview text
        sel_name = self.quick_coll_selector.currentText()
        vals = []
        for c in collections:
            if c.get('name')==sel_name:
                vals = c.get('values', [])
                break
        self.quick_preview_text.setPlainText('\n'.join(vals))
        self.quick_coll_count.setText(str(len(vals)))
        # update runtime meta: last quick dynamic selection
        try:
            meta = self.config_data.get('meta', {}) or {}
            meta['last_quick_dynamic'] = key
            self.config_data['meta'] = meta
            # persist immediately so app restarts restore this choice
            try:
                save_config_json(self.config_data)
            except Exception:
                pass
        except Exception:
            pass

    def _on_quick_coll_changed(self, idx):
        # Only update the preview/count when the quick collection selection changes.
        # Previously this called _on_quick_dynamic_changed which repopulated the
        # collection combo and immediately reset the selection, preventing cycling.
        try:
            key = self.quick_dynamic_selector.currentText()
            row, preview = self._find_dynamic_row_by_key(key)
            if preview is None:
                self.quick_preview_text.setPlainText('')
                self.quick_coll_count.setText('0')
                return
            collections = preview.property('collections') or []
            sel_name = self.quick_coll_selector.currentText()
            vals = []
            for c in collections:
                if c.get('name') == sel_name:
                    vals = c.get('values', [])
                    break
            self.quick_preview_text.setPlainText('\n'.join(vals))
            self.quick_coll_count.setText(str(len(vals)))
            # reflect this selection back into the dynamic row's preview container
            try:
                if preview is not None:
                    preview.setProperty('selected', sel_name)
                    preview.setProperty('values', vals)
                    # also update the preview text inside the dynamic table row
                    try:
                        pv_text = preview.layout().itemAt(1).widget()
                        if pv_text is not None and hasattr(pv_text, 'setPlainText'):
                            pv_text.setPlainText('\n'.join(vals))
                    except Exception:
                        pass
                    # update the count cell in the dynamic table for that row
                    try:
                        # find row index
                        for r in range(self.dynamic_table.rowCount()):
                            keyw = self.dynamic_table.cellWidget(r,0)
                            ktmp = ''
                            if keyw is not None and hasattr(keyw, 'layout'):
                                for i in range(keyw.layout().count()):
                                    w = keyw.layout().itemAt(i).widget()
                                    if hasattr(w, 'text'):
                                        ktmp = w.text()
                                        break
                            else:
                                it = self.dynamic_table.item(r,0)
                                ktmp = it.text() if it else ''
                            if ktmp == key:
                                try:
                                    self.dynamic_table.item(r,1).setText(str(len(vals)))
                                except Exception:
                                    pass
                                break
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                print(f"[ui] _on_quick_coll_changed key={key} sel={sel_name} values={len(vals)}")
            except Exception:
                pass
            # update runtime meta: record last used collection for this key
            try:
                meta = self.config_data.get('meta', {}) or {}
                last_used = meta.get('last_used_dynamic', {}) or {}
                if key:
                    last_used[key] = sel_name
                    meta['last_used_dynamic'] = last_used
                    self.config_data['meta'] = meta
                    # persist immediately so app restarts restore this choice
                    try:
                        save_config_json(self.config_data)
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            # swallow to avoid breaking UI
            pass

    def _cycle_quick_collection(self):
        # debounce to avoid multiple signal deliveries (pressed/released/clicked)
        try:
            now = time.time()
            if hasattr(self, '_last_cycle_ts') and (now - self._last_cycle_ts) < 0.18:
                return
            self._last_cycle_ts = now
        except Exception:
            pass
        try:
            if not hasattr(self, 'quick_coll_selector') or self.quick_coll_selector is None:
                return
            cnt = self.quick_coll_selector.count()
            if cnt <= 0:
                return
            cur = self.quick_coll_selector.currentIndex()
            if cur < 0:
                cur = 0
            self.quick_coll_selector.setCurrentIndex((cur + 1) % cnt)
        except Exception:
            pass

    def _edit_quick_collection(self):
        """Handle the quick 'Editar' button: locate the dynamic row for the
        selected quick key and open the same editor used for dynamic rows.
        After editing, refresh the quick preview."""
        try:
            key = self.quick_dynamic_selector.currentText()
            if not key:
                return
            row, preview = self._find_dynamic_row_by_key(key)
            if row is None:
                return
            # Reuse the existing edit dialog for dynamic rows
            self.edit_dynamic_row(row)
            # Refresh quick preview in case values changed
            try:
                self._on_quick_dynamic_changed(self.quick_dynamic_selector.currentIndex())
            except Exception:
                pass
        except Exception:
            # swallow any unexpected errors to avoid breaking UI wiring
            pass

    def _find_dynamic_row_by_key(self, key_name):
        for r in range(self.dynamic_table.rowCount()):
            w = self.dynamic_table.cellWidget(r,0)
            key = ''
            if w is not None and hasattr(w, 'layout'):
                for i in range(w.layout().count()):
                    child = w.layout().itemAt(i).widget()
                    if hasattr(child, 'text'):
                        key = child.text()
                        break
            else:
                it = self.dynamic_table.item(r,0)
                key = it.text() if it else ''
            if key == key_name:
                return r, self.dynamic_table.cellWidget(r,2)
        return None, None

    def _perform_action_on_quick(self, action_label):
        key = self.quick_dynamic_selector.currentText()
        row, preview = self._find_dynamic_row_by_key(key)
        if row is None:
            return
        # find the button in actions column and click
        w = self.dynamic_table.cellWidget(row,3)
        if w is None: return
        for i in range(w.layout().count()):
            child = w.layout().itemAt(i).widget()
            if isinstance(child, QPushButton) and child.text() == action_label:
                child.click()
                return

    # ---------- edit/manage/delete handlers ----------
    def _find_row_for_button(self, button: QPushButton):
        for r in range(self.dynamic_table.rowCount()):
            w = self.dynamic_table.cellWidget(r,3)
            if not w: continue
            for i in range(w.layout().count()):
                if w.layout().itemAt(i).widget() is button:
                    return r
        return -1

    def _edit_dynamic_button_clicked(self, button: QPushButton):
        row = self._find_row_for_button(button)
        if row>=0:
            self.edit_dynamic_row(row)

    def _manage_collections_button_clicked(self, button: QPushButton):
        row = self._find_row_for_button(button)
        if row<0: return
        preview_widget = self.dynamic_table.cellWidget(row,2)
        if preview_widget is None: return
        collections = preview_widget.property('collections') or []
        selected = preview_widget.property('selected') or (collections[0]['name'] if collections else 'default')
        dlg = QDialog(self)
        dlg.setWindowTitle('Gestionar colecciones')
        dlg.setMinimumWidth(800)
        dlg.setMinimumHeight(520)
        layout = QVBoxLayout(dlg)
        coll_selector = QComboBox()
        for c in collections:
            coll_selector.addItem(c.get('name','default'))
        try:
            coll_selector.setCurrentText(selected)
        except Exception:
            pass
        layout.addWidget(QLabel('Colecciones:'))
        layout.addWidget(coll_selector)
        btns = QHBoxLayout()
        add_btn = QPushButton('Agregar')
        rename_btn = QPushButton('Renombrar')
        delete_btn = QPushButton('Eliminar')
        btns.addWidget(add_btn)
        btns.addWidget(rename_btn)
        btns.addWidget(delete_btn)
        layout.addLayout(btns)
        layout.addWidget(QLabel('Valores (una por línea):'))
        values_editor = QTextEdit()
        # populate
        if collections:
            cur = coll_selector.currentText()
            for c in collections:
                if c.get('name')==cur:
                    values_editor.setPlainText('\n'.join(c.get('values',[])))
                    break
        layout.addWidget(values_editor)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        def on_add():
            name, ok = QInputDialog.getText(self, 'Nombre colección', 'Ingrese el nombre de la nueva colección:')
            if ok and name:
                if any(c.get('name')==name for c in collections):
                    QMessageBox.warning(self, 'Error', 'Ya existe una colección con ese nombre')
                    return
                collections.append({'name':name,'values':[]})
                coll_selector.addItem(name)
                coll_selector.setCurrentText(name)
                values_editor.setPlainText('')
        def on_rename():
            cur = coll_selector.currentText()
            if not cur: return
            name, ok = QInputDialog.getText(self, 'Renombrar colección', 'Nuevo nombre:', text=cur)
            if ok and name:
                if any(c.get('name')==name and c.get('name')!=cur for c in collections):
                    QMessageBox.warning(self, 'Error', 'Ya existe una colección con ese nombre')
                    return
                for c in collections:
                    if c.get('name')==cur:
                        c['name']=name
                        break
                coll_selector.setItemText(coll_selector.currentIndex(), name)
        def on_delete():
            cur = coll_selector.currentText()
            if not cur: return
            if QMessageBox.question(self,'Confirmar', f"Eliminar colección '{cur}'?") != QMessageBox.Yes:
                return
            for i,c in enumerate(collections):
                if c.get('name')==cur:
                    collections.pop(i)
                    coll_selector.removeItem(i)
                    break
            if collections:
                new = collections[0]
                coll_selector.setCurrentIndex(0)
                values_editor.setPlainText('\n'.join(new.get('values',[])))
            else:
                values_editor.setPlainText('')
        def on_coll_changed(i):
            name = coll_selector.currentText()
            for c in collections:
                if c.get('name')==name:
                    values_editor.setPlainText('\n'.join(c.get('values',[])))
                    break
        add_btn.clicked.connect(on_add)
        rename_btn.clicked.connect(on_rename)
        delete_btn.clicked.connect(on_delete)
        coll_selector.currentIndexChanged.connect(on_coll_changed)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        if dlg.exec() == QDialog.Accepted:
            cur = coll_selector.currentText()
            new_vals = [line.strip() for line in values_editor.toPlainText().splitlines() if line.strip()]
            for c in collections:
                if c.get('name')==cur:
                    c['values']=new_vals
                    break
            preview_container = self.dynamic_table.cellWidget(row,2)
            if preview_container is not None:
                preview_container.setProperty('collections', collections)
                preview_container.setProperty('selected', cur)
                preview_container.setProperty('values', new_vals)
                try:
                    pv_text = preview_container.layout().itemAt(1).widget()
                    if pv_text is not None and hasattr(pv_text,'setPlainText'):
                        pv_text.setPlainText('\n'.join(new_vals))
                except Exception:
                    pass
            try:
                # update actions combobox
                aw = self.dynamic_table.cellWidget(row,3)
                if aw is not None and hasattr(aw,'layout'):
                    for i in range(aw.layout().count()):
                        ch = aw.layout().itemAt(i).widget()
                        if isinstance(ch, QComboBox):
                            ch.clear()
                            for c in collections:
                                ch.addItem(c.get('name'))
                            try:
                                ch.setCurrentText(cur)
                            except Exception:
                                pass
                            break
            except Exception:
                pass
            # update count
            try:
                self.dynamic_table.item(row,1).setText(str(len(new_vals)))
            except Exception:
                pass

    def edit_dynamic_row(self, row: int):
        # open dialog to edit values for the selected collection
        preview_widget = self.dynamic_table.cellWidget(row,2)
        collections = preview_widget.property('collections') or []
        selected = preview_widget.property('selected') or (collections[0]['name'] if collections else 'default')
        key_text = ''
        try:
            keyw = self.dynamic_table.cellWidget(row,0)
            for i in range(keyw.layout().count()):
                w = keyw.layout().itemAt(i).widget()
                if hasattr(w,'text'):
                    key_text = w.text()
                    break
        except Exception:
            key_item = self.dynamic_table.item(row,0)
            key_text = key_item.text() if key_item else ''
        coll_obj = None
        for c in collections:
            if c.get('name')==selected:
                coll_obj = c
                break
        if coll_obj is None:
            coll_obj = collections[0] if collections else {'name':'default','values':[]}
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Editar valores - {key_text} :: {coll_obj.get('name')}")
        dialog.setMinimumWidth(800)
        dialog.setMinimumHeight(520)
        dlg_layout = QVBoxLayout(dialog)
        te = QTextEdit()
        te.setPlainText('\n'.join(coll_obj.get('values',[])))
        dlg_layout.addWidget(te)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        dlg_layout.addWidget(buttons)
        if dialog.exec() == QDialog.Accepted:
            new_text = te.toPlainText()
            new_values = [line.strip() for line in new_text.splitlines() if line.strip()]
            coll_obj['values'] = new_values
            preview_container = self.dynamic_table.cellWidget(row,2)
            if preview_container is not None:
                preview_container.setProperty('collections', collections)
                preview_container.setProperty('selected', coll_obj.get('name'))
                preview_container.setProperty('values', new_values)
                try:
                    pv_text = preview_container.layout().itemAt(1).widget()
                    if pv_text is not None and hasattr(pv_text,'setPlainText'):
                        pv_text.setPlainText('\n'.join(new_values))
                except Exception:
                    pass
            try:
                self.dynamic_table.item(row,1).setText(str(len(new_values)))
            except Exception:
                pass

    def _delete_dynamic_button_clicked(self, button: QPushButton):
        row = self._find_row_for_button(button)
        if row>=0:
            self.dynamic_table.removeRow(row)

    # ---------- execution ----------
    def execute_requests(self):
        # validate placeholders
        placeholder_re = re.compile(r"\{+([A-Za-z0-9_]+)\}+")
        # gather defined keys
        defined_keys = set()
        dynamic_lists = {}
        for r in range(self.dynamic_table.rowCount()):
            key = ''
            w = self.dynamic_table.cellWidget(r,0)
            if w is not None and hasattr(w,'layout'):
                for i in range(w.layout().count()):
                    child = w.layout().itemAt(i).widget()
                    if hasattr(child,'text'):
                        key = child.text()
                        break
            else:
                it = self.dynamic_table.item(r,0)
                key = it.text() if it else ''
            if not key: continue
            defined_keys.add(key)
            pv = self.dynamic_table.cellWidget(r,2)
            cols = pv.property('collections') or []
            sel = pv.property('selected') or (cols[0]['name'] if cols else 'default')
            vals = []
            for c in cols:
                if c.get('name')==sel:
                    vals = c.get('values', [])
                    break
            dynamic_lists[key] = vals
        # collect api objects
        apis = []
        for r in range(self.api_table.rowCount()):
            # only active
            cbw = self.api_table.cellWidget(r,1)
            active = True
            if cbw is not None and cbw.layout() and cbw.layout().count()>0:
                active = cbw.layout().itemAt(0).widget().isChecked()
            if not active: continue
            name = self.api_table.item(r,2).text() if self.api_table.item(r,2) else ''
            url = self.api_table.item(r,3).text() if self.api_table.item(r,3) else ''
            method = self.api_table.cellWidget(r,4).currentText() if self.api_table.cellWidget(r,4) else 'GET'
            # prefer persisted api info in config_data (includes body/body_raw/headers)
            existing_apis = self.config_data.get('apis', []) if self.config_data else []
            existing = existing_apis[r] if r < len(existing_apis) else {}
            headers = existing.get('headers', {}) if existing is not None else {}
            # token: prefer API-specific token, then editor value if editing this row, then global token
            token = existing.get('token') if existing is not None else None
            # body can be structured (dict) or raw text stored as body_raw
            api_body = None
            api_body_raw = ''
            if 'body' in existing and existing.get('body') is not None:
                api_body = existing.get('body')
            elif 'body_raw' in existing and existing.get('body_raw'):
                api_body_raw = existing.get('body_raw')
            else:
                # fallback: if the user has this row selected in the edit panel, use editors
                if self.editing_row == r:
                    try:
                        btxt = self.body_editor.toPlainText()
                        api_body = json.loads(btxt)
                    except Exception:
                        api_body_raw = self.body_editor.toPlainText()
                    try:
                        headers = json.loads(self.headers_editor.toPlainText())
                    except Exception:
                        headers = {}
            # if user is editing this row and provided token in the edit panel, prefer it
            if not token and self.editing_row == r:
                try:
                    t = self.token_input.text().strip()
                    if t:
                        token = t
                except Exception:
                    pass
            # fallback to global token if still empty
            if not token:
                try:
                    gt = self.global_token_input.text().strip()
                    if gt:
                        token = gt
                except Exception:
                    pass

            api_entry = {'name': name, 'url': url, 'method': method, 'headers': headers, 'token': token, 'body': api_body, 'body_raw': api_body_raw}
            apis.append(api_entry)
        # validate placeholders across apis
        missing = set()
        empty_vals = set()
        for api in apis:
            s = json.dumps(api)
            for k in placeholder_re.findall(s):
                if k not in defined_keys:
                    missing.add(k)
        for k,v in dynamic_lists.items():
            if not v:
                empty_vals.add(k)
        if missing or empty_vals:
            msg = ''
            if missing:
                msg += 'Placeholders sin variable definida: ' + ','.join(missing) + '\n'
            if empty_vals:
                msg += 'Variables definidas sin valores: ' + ','.join(empty_vals) + '\n'
            QMessageBox.warning(self, 'Errores en placeholders', msg)
            return
        # run executor
        print('[ui] launching executor...')
        results, run_dir = run_apis(apis, dynamic_lists)
        print('[ui] executed, got', len(results), 'results')
        # store and display results in summary tab
        try:
            self.results = results
            try:
                self.update_summary(results)
            except Exception:
                pass
        except Exception:
            pass
        # inform user where results were saved (if available)
        try:
            if run_dir:
                QMessageBox.information(self, 'Ejecución completa', f'Resultados: {len(results)}\nGuardados en: {run_dir}')
            else:
                QMessageBox.information(self, 'Ejecución completa', f'Resultados: {len(results)}')
        except Exception:
            QMessageBox.information(self, 'Ejecución completa', f'Resultados: {len(results)}')

    # ---------- API table edit handlers ----------
    def api_row_clicked(self, row, col):
        self.editing_row = row
        api = self.config_data.get('apis', [])[row] if self.config_data.get('apis') and row < len(self.config_data.get('apis')) else None
        if not api: return
        self.name_input.setText(api.get('name',''))
        self.url_input.setText(api.get('url',''))
        try:
            self.method_input.setCurrentText(api.get('method','GET'))
        except Exception:
            pass
        self.token_input.setText(api.get('token',''))
        if api.get('body_raw'):
            self.body_editor.setText(api.get('body_raw'))
        else:
            try:
                self.body_editor.setText(json.dumps(api.get('body',{}), indent=2))
            except Exception:
                self.body_editor.setText(str(api.get('body',{})))
        try:
            self.headers_editor.setText(json.dumps(api.get('headers',{}), indent=2))
        except Exception:
            self.headers_editor.setText(str(api.get('headers',{})))

    def save_api_edits(self):
        if self.editing_row is None: return
        r = self.editing_row
        self.api_table.item(r,2).setText(self.name_input.text())
        self.api_table.item(r,3).setText(self.url_input.text())
        try:
            self.api_table.cellWidget(r,4).setCurrentText(self.method_input.currentText())
        except Exception:
            pass
        # update config_data
        if 'apis' not in self.config_data:
            self.config_data['apis'] = []
        while len(self.config_data['apis']) <= r:
            self.config_data['apis'].append({})
        entry = self.config_data['apis'][r]
        entry['name'] = self.name_input.text()
        entry['url'] = self.url_input.text()
        entry['method'] = self.method_input.currentText()
        entry['token'] = self.token_input.text()
        # body
        btxt = self.body_editor.toPlainText()
        try:
            entry['body'] = json.loads(btxt)
            # ensure we don't keep stale raw text when structured body is present
            entry.pop('body_raw', None)
        except Exception:
            # preserve the raw text when it isn't valid JSON
            entry['body_raw'] = btxt
            entry.pop('body', None)
        try:
            entry['headers'] = json.loads(self.headers_editor.toPlainText())
        except Exception:
            entry['headers'] = {}
        # persist immediately so edits are not lost and other save paths don't overwrite body
        try:
            save_config_json(self.config_data)
        except Exception:
            pass

    def add_new_api(self):
        idx = self.api_table.rowCount()
        self.api_table.insertRow(idx)
        self.api_table.setItem(idx,0,QTableWidgetItem(str(idx+1)))
        cbw = QWidget()
        l = QHBoxLayout(cbw)
        l.setContentsMargins(0,0,0,0)
        cb = QCheckBox()
        cb.setChecked(True)
        l.addWidget(cb)
        cbw.setLayout(l)
        self.api_table.setCellWidget(idx,1,cbw)
        self.api_table.setItem(idx,2,QTableWidgetItem('Nueva API'))
        self.api_table.setItem(idx,3,QTableWidgetItem('https://'))
        mc = QComboBox()
        mc.addItems(["GET","POST","PUT","DELETE"])
        self.api_table.setCellWidget(idx,4,mc)

    def _add_dynamic_variable(self):
        idx = self.dynamic_table.rowCount()
        self.add_dynamic_row('new_key', [{'name':'default','values':[] }], 'default')
        self._populate_quick_dynamic_selector()

    def toggle_select_all(self, checked: bool):
        """Toggle all API active checkboxes on or off.

        This replaces the previous separate select/deselect and "choose" dialog UI.
        The toggle button will pass the checked state here.
        """
        try:
            for r in range(self.api_table.rowCount()):
                cbw = self.api_table.cellWidget(r, 1)
                if cbw is not None and cbw.layout() and cbw.layout().count() > 0:
                    try:
                        cbw.layout().itemAt(0).widget().setChecked(bool(checked))
                    except Exception:
                        pass
            # update the toggle button label to reflect action
            if hasattr(self, 'toggle_select_btn') and self.toggle_select_btn is not None:
                self.toggle_select_btn.setText("Quitar todo" if checked else "Seleccionar todo")
        except Exception:
            pass

# end class