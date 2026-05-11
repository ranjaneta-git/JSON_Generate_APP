"""Qt stylesheet for BMIoT ConfigTool."""

APP_STYLE = """
QMainWindow, QDialog {
    background-color: #f0f0f0;
}

/* ── Sidebar ─────────────────────────────────────────────── */
QWidget#sidebar {
    background-color: #2c3e50;
    min-width: 220px;
    max-width: 220px;
}
QWidget#sidebar QLabel {
    color: #bdc3c7;
    background: transparent;
}
QLabel#sidebar_title, QLabel#sidebar_app_title {
    color: #ecf0f1;
    font-size: 14px;
    font-weight: bold;
    padding: 16px 14px 4px 14px;
    background-color: #1a252f;
}
QLabel#sidebar_subtitle, QLabel#sidebar_version {
    color: #7f8c8d;
    font-size: 10px;
    padding: 0px 14px 12px 14px;
    background-color: #1a252f;
}
QPushButton#nav_btn {
    color: #bdc3c7;
    background: transparent;
    border: none;
    border-left: 3px solid transparent;
    text-align: left;
    padding: 9px 14px;
    font-size: 12px;
    min-height: 34px;
}
QPushButton#nav_btn:hover {
    background-color: #34495e;
    color: #ecf0f1;
}
QPushButton#nav_btn:checked {
    background-color: #34495e;
    border-left: 3px solid #3498db;
    color: #ffffff;
    font-weight: bold;
}
QPushButton#sidebar_file_btn {
    color: #95a5a6;
    background: transparent;
    border: none;
    border-top: 1px solid #3d566e;
    text-align: left;
    padding: 7px 14px;
    font-size: 11px;
    min-height: 28px;
}
QPushButton#sidebar_file_btn:hover {
    background-color: #34495e;
    color: #ecf0f1;
}

/* ── Step badge ──────────────────────────────────────────── */
QLabel#step_badge_done {
    color: #27ae60;
    font-size: 11px;
    font-weight: bold;
}
QLabel#step_badge_pending {
    color: #7f8c8d;
    font-size: 11px;
}

/* ── Page titles ─────────────────────────────────────────── */
QLabel#page_title {
    font-size: 17px;
    font-weight: bold;
    color: #2c3e50;
    padding: 6px 0px 2px 0px;
}
QLabel#page_subtitle {
    font-size: 11px;
    color: #7f8c8d;
    padding: 0px 0px 6px 0px;
}

/* ── Generic content labels ──────────────────────────────── */
QLabel {
    color: #2c3e50;
}

/* ── Empty state ─────────────────────────────────────────── */
QLabel#empty_state {
    color: #95a5a6;
    font-size: 13px;
    font-style: italic;
    padding: 30px 20px;
}
QLabel#empty_state_title {
    color: #7f8c8d;
    font-size: 14px;
    font-weight: bold;
    padding: 10px 0px 4px 0px;
}
QLabel#empty_state_hint {
    color: #95a5a6;
    font-size: 12px;
    padding: 2px 0px;
}

/* ── Info box (light blue background) ────────────────────── */
QFrame#info_box {
    background-color: #eaf4fd;
    border: 1px solid #bcdff1;
    border-radius: 4px;
    padding: 8px 12px;
}
QLabel#info_text {
    color: #31708f;
    font-size: 11px;
}

/* ── Workflow hint (light yellow) ────────────────────────── */
QFrame#workflow_hint {
    background-color: #fef9e7;
    border: 1px solid #f9e79f;
    border-radius: 4px;
    padding: 8px 12px;
}
QLabel#workflow_hint_text {
    color: #7d6608;
    font-size: 11px;
}

/* ── Group boxes ─────────────────────────────────────────── */
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #dee2e6;
    border-radius: 4px;
    margin-top: 10px;
    padding-top: 14px;
    font-weight: bold;
    font-size: 11px;
    color: #495057;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QGroupBox QLabel {
    color: #2c3e50;
    font-weight: normal;
    font-size: 12px;
}
QGroupBox QLabel#page_subtitle {
    color: #7f8c8d;
    font-size: 11px;
}

/* ── Buttons ─────────────────────────────────────────────── */
QPushButton {
    padding: 5px 12px;
    border-radius: 3px;
    font-size: 12px;
    border: 1px solid #ced4da;
    background-color: #f8f9fa;
    color: #343a40;
    min-height: 26px;
}
QPushButton:hover { background-color: #e9ecef; }
QPushButton:pressed { background-color: #dee2e6; }
QPushButton:disabled { color: #adb5bd; background-color: #f8f9fa; }

QPushButton#btn_primary {
    background-color: #3498db;
    color: white;
    border-color: #2980b9;
    font-weight: bold;
}
QPushButton#btn_primary:hover { background-color: #2980b9; }

QPushButton#btn_danger {
    background-color: #e74c3c;
    color: white;
    border-color: #c0392b;
}
QPushButton#btn_danger:hover { background-color: #c0392b; }

QPushButton#btn_success {
    background-color: #27ae60;
    color: white;
    border-color: #229954;
    font-size: 13px;
    font-weight: bold;
    min-height: 34px;
    padding: 8px 22px;
}
QPushButton#btn_success:hover { background-color: #229954; }

QPushButton#btn_next {
    background-color: #3498db;
    color: white;
    border-color: #2980b9;
    font-size: 12px;
    font-weight: bold;
    min-height: 30px;
    padding: 6px 18px;
}
QPushButton#btn_next:hover { background-color: #2980b9; }

/* ── Tables ──────────────────────────────────────────────── */
QTableWidget {
    border: 1px solid #dee2e6;
    background-color: white;
    color: #2c3e50;
    gridline-color: #e9ecef;
    selection-background-color: #3498db;
    selection-color: #ffffff;
    alternate-background-color: #f8f9fa;
    font-size: 12px;
}
QTableWidget::item {
    padding: 3px 6px;
    color: #2c3e50;
    background-color: transparent;
}
QTableWidget::item:alternate {
    background-color: #f8f9fa;
    color: #2c3e50;
}
QTableWidget::item:hover {
    background-color: #e8f4f8;
    color: #2c3e50;
}
QTableWidget::item:selected {
    background-color: #3498db;
    color: #ffffff;
}
QTableWidget::item:selected:!active {
    background-color: #cce5ff;
    color: #2c3e50;
}
QHeaderView::section {
    background-color: #f8f9fa;
    border: none;
    border-bottom: 1px solid #dee2e6;
    border-right: 1px solid #dee2e6;
    padding: 5px 8px;
    font-weight: bold;
    font-size: 11px;
    color: #495057;
}

/* ── Inputs ──────────────────────────────────────────────── */
QLineEdit {
    border: 1px solid #ced4da;
    border-radius: 3px;
    padding: 4px 8px;
    background: white;
    color: #2c3e50;
    font-size: 12px;
    min-height: 24px;
}
QLineEdit:focus {
    border-color: #3498db;
}
QLineEdit[text=""] {
    color: #95a5a6;
}
QSpinBox, QDoubleSpinBox {
    border: 1px solid #ced4da;
    border-radius: 3px;
    padding: 4px 22px 4px 8px;
    background: white;
    color: #2c3e50;
    font-size: 12px;
    min-height: 24px;
}
QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #3498db;
}

/* SpinBox up/down arrow buttons with explicit SVG arrows for visibility */
QSpinBox::up-button, QDoubleSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 20px;
    height: 14px;
    border-left: 1px solid #ced4da;
    border-bottom: 1px solid #ced4da;
    border-top-right-radius: 3px;
    background: #c8cfd7;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {
    background: #adb5bd;
}
QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed {
    background: #9aa4ab;
}
QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 20px;
    height: 14px;
    border-left: 1px solid #ced4da;
    border-top: 1px solid #ced4da;
    border-bottom-right-radius: 3px;
    background: #c8cfd7;
}
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background: #adb5bd;
}
QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {
    background: #9aa4ab;
}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
    image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%228%22%20height%3D%226%22%3E%3Cpolygon%20points%3D%224%2C0%200%2C6%208%2C6%22%20fill%3D%22%232c3e50%22%2F%3E%3C%2Fsvg%3E");
    width: 8px;
    height: 6px;
}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
    image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%228%22%20height%3D%226%22%3E%3Cpolygon%20points%3D%224%2C6%200%2C0%208%2C0%22%20fill%3D%22%232c3e50%22%2F%3E%3C%2Fsvg%3E");
    width: 8px;
    height: 6px;
}
QComboBox {
    border: 1px solid #ced4da;
    border-radius: 3px;
    padding: 3px 8px;
    background: white;
    color: #2c3e50;
    font-size: 12px;
    min-height: 24px;
}
QComboBox:focus { border-color: #3498db; }
QComboBox:disabled { color: #adb5bd; background-color: #f8f9fa; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: white;
    color: #2c3e50;
    selection-background-color: #3498db;
    selection-color: #ffffff;
    border: 1px solid #dee2e6;
    font-size: 12px;
}
QComboBox QAbstractItemView::item {
    color: #2c3e50;
    padding: 4px 8px;
    min-height: 22px;
}
QComboBox QAbstractItemView::item:hover {
    background-color: #e8f4f8;
    color: #2c3e50;
}
QComboBox QAbstractItemView::item:selected {
    background-color: #3498db;
    color: #ffffff;
}

/* ── List widgets ────────────────────────────────────────── */
QListWidget {
    border: 1px solid #dee2e6;
    background: white;
    color: #2c3e50;
    alternate-background-color: #f8f9fa;
    font-size: 12px;
}
QListWidget::item {
    padding: 6px 8px;
    color: #2c3e50;
    background-color: transparent;
}
QListWidget::item:alternate {
    background-color: #f8f9fa;
    color: #2c3e50;
}
QListWidget::item:hover {
    background-color: #e8f4f8;
    color: #2c3e50;
}
QListWidget::item:selected {
    background-color: #3498db;
    color: #ffffff;
}
QListWidget::item:selected:!active {
    background-color: #cce5ff;
    color: #2c3e50;
}

/* ── Tree ────────────────────────────────────────────────── */
QTreeWidget {
    border: 1px solid #dee2e6;
    background: white;
    color: #2c3e50;
    alternate-background-color: #f8f9fa;
    font-size: 12px;
}
QTreeWidget::item {
    padding: 4px 4px;
    color: #2c3e50;
    background-color: transparent;
}
QTreeWidget::item:alternate {
    background-color: #f8f9fa;
    color: #2c3e50;
}
QTreeWidget::item:hover {
    background-color: #e8f4f8;
    color: #2c3e50;
}
QTreeWidget::item:selected {
    background-color: #3498db;
    color: #ffffff;
}
QTreeWidget::item:selected:!active {
    background-color: #cce5ff;
    color: #2c3e50;
}
QTreeWidget QHeaderView::section {
    background-color: #f8f9fa;
    color: #495057;
    font-weight: bold;
    font-size: 11px;
    border: none;
    border-bottom: 1px solid #dee2e6;
    border-right: 1px solid #dee2e6;
    padding: 5px 8px;
}

/* ── Status bar ──────────────────────────────────────────── */
QStatusBar {
    background-color: #2c3e50;
    color: #ecf0f1;
    font-size: 11px;
    min-height: 22px;
}

/* ── Text edit (JSON preview) ────────────────────────────── */
QTextEdit#json_preview {
    font-family: Consolas, "Courier New", monospace;
    font-size: 11px;
    background-color: #1e1e1e;
    color: #d4d4d4;
    border: 1px solid #dee2e6;
}

/* ── Scroll area ─────────────────────────────────────────── */
QScrollArea { border: none; }

/* ── Separator ───────────────────────────────────────────── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {
    color: #dee2e6;
}

/* ── Tab widget ──────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #dee2e6;
    background: white;
}
QTabBar::tab {
    background: #f0f0f0;
    border: 1px solid #dee2e6;
    border-bottom: none;
    padding: 7px 18px;
    font-size: 12px;
    color: #495057;
    font-weight: normal;
    min-width: 160px;
}
QTabBar::tab:hover {
    background: #e2e6ea;
    color: #2c3e50;
}
QTabBar::tab:selected {
    background: white;
    color: #2c3e50;
    font-weight: bold;
    border-bottom-color: white;
}
QTabBar::tab:!selected {
    margin-top: 2px;
}

/* ── Checkbox ────────────────────────────────────────────── */
QCheckBox {
    color: #2c3e50;
    font-size: 12px;
    spacing: 6px;
}

/* ── Splitter ────────────────────────────────────────────── */
QSplitter::handle {
    background-color: #dee2e6;
    width: 2px;
}

/* ── Placeholder text ────────────────────────────────────── */
QLineEdit::placeholder {
    color: #95a5a6;
    font-style: italic;
}
"""
