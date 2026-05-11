"""Page 1 — Project Setup."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QGroupBox, QLabel, QPushButton,
)

from .base_page import BasePage
from ...engine.constants import VALID_BAUD_RATES, VALID_DATA_FORMATS

BAUD_LIST = sorted(VALID_BAUD_RATES)
DF_LIST = sorted(VALID_DATA_FORMATS)


class ProjectPage(BasePage):
    def __init__(self, main_window):
        super().__init__(
            main_window,
            "Step 1: Project Setup",
            "Start here — give your project a name and set the RS-485 serial communication "
            "parameters. These must match your physical Modbus devices.",
        )
        self._updating = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        for w in self._make_header():
            layout.addWidget(w)

        # Quick start info box
        layout.addWidget(self._make_info_box(
            "Getting Started:  Follow steps 1 through 9 in the sidebar. "
            "Each step builds on the previous one. Green checkmarks (✓) appear "
            "when a step is complete.\n\n"
            "Already have config files?  Use File → Import Existing JSON to load them."
        ))

        grp = QGroupBox("Project Information")
        form = QFormLayout(grp)
        form.setSpacing(10)
        form.setContentsMargins(12, 16, 12, 12)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g.  HeatPump_HP  or  Chiller_Plant_1")
        self.name_edit.setToolTip("A short name for this configuration (used as filename).")
        self.name_edit.textChanged.connect(self._on_changed)
        form.addRow("Project Name:", self.name_edit)

        layout.addWidget(grp)

        grp2 = QGroupBox("Serial Communication (RS-485 / Modbus RTU)")
        form2 = QFormLayout(grp2)
        form2.setSpacing(10)
        form2.setContentsMargins(12, 16, 12, 12)

        self.baud_combo = QComboBox()
        for b in BAUD_LIST:
            self.baud_combo.addItem(str(b), b)
        self.baud_combo.setToolTip(
            "Select the baud rate that matches your Modbus slave devices. "
            "9600 is the most common default."
        )
        self.baud_combo.currentIndexChanged.connect(self._on_changed)
        form2.addRow("Baud Rate:", self.baud_combo)

        self.df_combo = QComboBox()
        df_desc = {
            "8N1": "8N1  —  8 data, No parity, 1 stop  (most common)",
            "8E1": "8E1  —  8 data, Even parity, 1 stop",
            "8O1": "8O1  —  8 data, Odd parity, 1 stop",
            "8N2": "8N2  —  8 data, No parity, 2 stop",
        }
        for df in DF_LIST:
            self.df_combo.addItem(df_desc.get(df, df), df)
        self.df_combo.setToolTip(
            "Data format = data bits + parity + stop bits. "
            "Must match your devices. 8N1 is by far the most common."
        )
        self.df_combo.currentIndexChanged.connect(self._on_changed)
        form2.addRow("Data Format:", self.df_combo)

        self.profile_combo = QComboBox()
        self.profile_combo.addItem("0  —  Standard operational profile", 0)
        self.profile_combo.setToolTip("Firmware operation profile. Use 0 for normal operation.")
        self.profile_combo.currentIndexChanged.connect(self._on_changed)
        form2.addRow("Firmware Profile:", self.profile_combo)

        layout.addWidget(grp2)

        # Example
        layout.addWidget(self._make_info_box(
            "Example:  A typical VFD (Variable Frequency Drive) uses Baud 9600, Data Format 8N1.\n"
            "A heat pump might use Baud 19200 with 8E1. Check the device manual for exact settings."
        ))

        layout.addStretch()

        # Next step button
        bottom = QHBoxLayout()
        bottom.addStretch()
        bottom.addWidget(self._make_next_button("Next: Add Devices & Slaves  →", 1))
        layout.addLayout(bottom)

    def refresh(self):
        self._updating = True
        p = self.project
        self.name_edit.setText(p.name)
        idx = BAUD_LIST.index(p.baud_rate) if p.baud_rate in BAUD_LIST else 0
        self.baud_combo.setCurrentIndex(idx)
        df_idx = DF_LIST.index(p.data_format) if p.data_format in DF_LIST else 0
        self.df_combo.setCurrentIndex(df_idx)
        self.profile_combo.setCurrentIndex(0)
        self._updating = False

    def _on_changed(self):
        if self._updating:
            return
        p = self.project
        p.name = self.name_edit.text().strip() or "Untitled"
        p.baud_rate = self.baud_combo.currentData()
        p.data_format = self.df_combo.currentData()
        p.profile = self.profile_combo.currentData()
        self.mark_changed()
