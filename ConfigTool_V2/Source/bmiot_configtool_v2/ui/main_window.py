"""Main application window."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStackedWidget, QStatusBar,
    QMessageBox, QFileDialog, QFrame,
)
from PySide6.QtCore import Qt

from ..engine.models import Project
from ..engine.importer import import_json
from .project_io import save_project, load_project
from .pages.page_project import ProjectPage
from .pages.page_devices import DevicesPage
from .pages.page_registers import RegistersPage
from .pages.page_link_b import LinkBPage
from .pages.page_lbi import LbiPage
from .pages.page_cloud_groups import CloudGroupsPage
from .pages.page_nvs import NvsPage
from .pages.page_network import NetworkPage
from .pages.page_generate import GeneratePage


NAV_LABELS = [
    ("1  Project Setup",       "Set project name, baud rate, data format"),
    ("2  Devices & Slaves",    "Add your Modbus devices and slave addresses"),
    ("3  Registers",           "Define which registers to read/write"),
    ("4  Link B (Feedback)",   "Pair write registers with feedback reads"),
    ("5  LBI Slots",           "Choose which registers Lua can access"),
    ("6  Cloud Groups",        "Map registers to MQTT telemetry topics"),
    ("7  NVS Setpoints",       "Define cloud-writable persistent values"),
    ("8  Network / MQTT",      "Set MQTT broker IP, port, device IDs"),
    ("9  Generate JSON",       "Validate and generate config files"),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BMIoT ConfigTool")
        self.resize(1200, 780)

        self._project: Project = Project(name="Untitled")
        self._current_file: Optional[Path] = None
        self._unsaved: bool = False

        self._setup_ui()
        self._build_menu()
        self._switch_page(0)
        self._update_title()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ────────────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(0)

        # App title area
        title_area = QWidget()
        title_area.setObjectName("sidebar_title_area")
        ta_layout = QVBoxLayout(title_area)
        ta_layout.setContentsMargins(14, 16, 14, 12)
        ta_layout.setSpacing(2)
        app_lbl = QLabel("BMIoT ConfigTool")
        app_lbl.setObjectName("sidebar_app_title")
        ver_lbl = QLabel("v2.0  —  Thermelgy Gateway")
        ver_lbl.setObjectName("sidebar_version")
        ta_layout.addWidget(app_lbl)
        ta_layout.addWidget(ver_lbl)
        sl.addWidget(title_area)

        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet("color: #3d566e;")
        sl.addWidget(sep1)

        # Steps label
        steps_lbl = QLabel("  WORKFLOW STEPS")
        steps_lbl.setStyleSheet("color: #5d7a96; font-size: 9px; font-weight: bold; padding: 8px 14px 4px 14px;")
        sl.addWidget(steps_lbl)

        # Nav buttons with step badges
        self._nav_btns: list[QPushButton] = []
        self._nav_badges: list[QLabel] = []
        for idx, (label, _tip) in enumerate(NAV_LABELS):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(0)

            btn = QPushButton(label)
            btn.setObjectName("nav_btn")
            btn.setCheckable(True)
            btn.setToolTip(_tip)
            btn.clicked.connect(lambda checked, i=idx: self._switch_page(i))
            row.addWidget(btn, 1)

            badge = QLabel("")
            badge.setObjectName("step_badge_pending")
            badge.setFixedWidth(22)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet("background: transparent;")
            row.addWidget(badge)

            container = QWidget()
            container.setLayout(row)
            container.setStyleSheet("background: transparent;")
            sl.addWidget(container)
            self._nav_btns.append(btn)
            self._nav_badges.append(badge)

        sl.addStretch()

        # Separator before file actions
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("color: #3d566e;")
        sl.addWidget(sep2)

        file_lbl = QLabel("  FILE")
        file_lbl.setStyleSheet("color: #5d7a96; font-size: 9px; font-weight: bold; padding: 6px 14px 2px 14px;")
        sl.addWidget(file_lbl)

        for text, slot in [("New Project", self._file_new),
                           ("Open Project...", self._file_open),
                           ("Save Project", self._file_save),
                           ("Import Existing JSON...", self._file_import_json)]:
            btn = QPushButton(text)
            btn.setObjectName("sidebar_file_btn")
            btn.clicked.connect(slot)
            sl.addWidget(btn)

        root.addWidget(sidebar)

        # ── Page stack ─────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._pages: list = []
        for PageClass in [
            ProjectPage, DevicesPage, RegistersPage, LinkBPage,
            LbiPage, CloudGroupsPage, NvsPage, NetworkPage, GeneratePage,
        ]:
            page = PageClass(self)
            self._pages.append(page)
            self._stack.addWidget(page)

        root.addWidget(self._stack, 1)

        # Status bar
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready  —  Start by setting your project name and serial settings on Step 1")

    def _build_menu(self):
        mb = self.menuBar()

        file_menu = mb.addMenu("&File")
        file_menu.addAction("&New Project", self._file_new, "Ctrl+N")
        file_menu.addAction("&Open Project…", self._file_open, "Ctrl+O")
        file_menu.addAction("&Save", self._file_save, "Ctrl+S")
        file_menu.addAction("Save &As…", self._file_save_as, "Ctrl+Shift+S")
        file_menu.addSeparator()
        file_menu.addAction("&Import Existing JSON…", self._file_import_json, "Ctrl+I")
        file_menu.addSeparator()
        file_menu.addAction("E&xit", self.close, "Ctrl+Q")

        help_menu = mb.addMenu("&Help")
        help_menu.addAction("&About", self._show_about)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _switch_page(self, idx: int):
        for i, btn in enumerate(self._nav_btns):
            btn.setChecked(i == idx)
        self._stack.setCurrentIndex(idx)
        self._pages[idx].refresh()
        self._update_badges()

    # ------------------------------------------------------------------
    # Step badges — show checkmarks for completed steps
    # ------------------------------------------------------------------

    def _update_badges(self):
        p = self._project
        regs = p.all_registers()
        writes = [r for r in regs if r.fc in (5, 6)]

        checks = [
            bool(p.name and p.name != "Untitled"),                 # 1: Project
            bool(p.devices and any(d.slaves for d in p.devices)),  # 2: Devices
            bool(regs),                                             # 3: Registers
            not writes or any(r.link_b_register for r in writes),  # 4: Link B
            True,                                                   # 5: LBI (always valid)
            bool(p.cloud_groups),                                   # 6: Cloud Groups
            True,                                                   # 7: NVS (optional)
            bool(p.network and p.network.ip != "0.0.0.0"),         # 8: Network
            False,                                                  # 9: Generate (never auto-check)
        ]
        for i, done in enumerate(checks):
            badge = self._nav_badges[i]
            if done:
                badge.setText("✓")
                badge.setObjectName("step_badge_done")
                badge.setStyleSheet("color: #27ae60; background: transparent; font-weight: bold;")
            else:
                badge.setText("")
                badge.setObjectName("step_badge_pending")
                badge.setStyleSheet("background: transparent;")

    # ------------------------------------------------------------------
    # Project property
    # ------------------------------------------------------------------

    @property
    def project(self) -> Project:
        return self._project

    @project.setter
    def project(self, p: Project):
        self._project = p

    def on_project_changed(self):
        """Called by pages via mark_changed()."""
        self._unsaved = True
        self._update_title()
        self._update_badges()

    def _update_title(self):
        name = self._current_file.name if self._current_file else "Untitled"
        star = " *" if self._unsaved else ""
        self.setWindowTitle(f"BMIoT ConfigTool — {name}{star}")

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def _confirm_discard(self) -> bool:
        if not self._unsaved:
            return True
        resp = QMessageBox.question(
            self, "Unsaved Changes",
            "You have unsaved changes. Discard them?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return resp == QMessageBox.StandardButton.Yes

    def _file_new(self):
        if not self._confirm_discard():
            return
        self._project = Project(name="Untitled")
        self._current_file = None
        self._unsaved = False
        self._update_title()
        self._switch_page(0)
        self.statusBar().showMessage("New project created. Start at Step 1.", 5000)

    def _file_open(self):
        if not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", str(Path.home()),
            "BMIoT Project (*.bmiot_project);;All Files (*)"
        )
        if not path:
            return
        try:
            self._project = load_project(Path(path))
            self._current_file = Path(path)
            self._unsaved = False
            self._update_title()
            self._switch_page(0)
            self.statusBar().showMessage(f"Opened: {Path(path).name}", 5000)
        except Exception as exc:
            QMessageBox.critical(self, "Open Failed", str(exc))

    def _file_save(self):
        if self._current_file is None:
            self._file_save_as()
            return
        try:
            save_project(self._project, self._current_file)
            self._unsaved = False
            self._update_title()
            self.statusBar().showMessage(f"Saved: {self._current_file.name}", 4000)
        except Exception as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))

    def _file_save_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Project As",
            str(Path.home() / (self._project.name + ".bmiot_project")),
            "BMIoT Project (*.bmiot_project);;All Files (*)"
        )
        if not path:
            return
        self._current_file = Path(path)
        self._file_save()

    def _file_import_json(self):
        """Import existing Modbus_Config.json + ParamMap_Config.json pair."""
        if not self._confirm_discard():
            return
        mb_path, _ = QFileDialog.getOpenFileName(
            self, "Select Modbus_Config.json", str(Path.home()),
            "JSON Files (*.json);;All Files (*)"
        )
        if not mb_path:
            return
        pm_path, _ = QFileDialog.getOpenFileName(
            self, "Select ParamMap_Config.json",
            str(Path(mb_path).parent),
            "JSON Files (*.json);;All Files (*)"
        )
        if not pm_path:
            return
        try:
            self._project = import_json(Path(mb_path), Path(pm_path))
            self._current_file = None
            self._unsaved = True
            self._update_title()
            self._switch_page(0)
            self.statusBar().showMessage(
                f"Imported from {Path(mb_path).name} + {Path(pm_path).name}. "
                "Review all steps and save when ready.",
                8000,
            )
            QMessageBox.information(
                self, "Import Successful",
                f"Imported {len(self._project.all_registers())} registers, "
                f"{len(self._project.devices)} device(s), "
                f"{len(self._project.cloud_groups)} cloud group(s).\n\n"
                "Please review all steps to verify correctness before generating."
            )
        except Exception as exc:
            QMessageBox.critical(self, "Import Failed", str(exc))

    # ------------------------------------------------------------------
    # Help
    # ------------------------------------------------------------------

    def _show_about(self):
        QMessageBox.about(
            self,
            "About BMIoT ConfigTool",
            "<b>BMIoT ConfigTool v2.0</b><br><br>"
            "GUI tool for generating <tt>Modbus_Config.json</tt> and "
            "<tt>ParamMap_Config.json</tt> for the Thermelgy BMIoT "
            "ESP32 gateway firmware.<br><br>"
            "<b>Workflow:</b> Follow steps 1–9 in order. Green checkmarks "
            "appear on completed steps.<br><br>"
            "Firmware: Modbus RTU → MQTT bridge with Lua scripting.",
        )

    def closeEvent(self, event):
        if not self._confirm_discard():
            event.ignore()
        else:
            event.accept()
