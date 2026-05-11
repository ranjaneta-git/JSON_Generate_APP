"""Page 8 — Network Configuration (NTC)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLabel, QGroupBox,
    QLineEdit, QHeaderView, QAbstractItemView,
)
from PySide6.QtCore import Qt

from .base_page import BasePage
from ...engine.models import NetworkConfig


class NetworkPage(BasePage):
    def __init__(self, main_window):
        super().__init__(
            main_window,
            "Step 8: Network / MQTT",
            "Configure the MQTT broker connection and device identity. "
            "These settings tell the gateway where to send telemetry data.",
        )
        self._updating = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        for w in self._make_header():
            layout.addWidget(w)

        # MQTT broker
        broker_grp = QGroupBox("MQTT Broker")
        broker_form = QFormLayout(broker_grp)
        broker_form.setSpacing(8)
        broker_form.setContentsMargins(12, 14, 12, 12)

        self.ip_edit = QLineEdit()
        self.ip_edit.setPlaceholderText("18.191.222.62")
        self.ip_edit.textChanged.connect(self._on_changed)
        broker_form.addRow("Broker IP:", self.ip_edit)

        self.port_edit = QLineEdit()
        self.port_edit.setPlaceholderText("1883")
        self.port_edit.textChanged.connect(self._on_changed)
        broker_form.addRow("Broker Port:", self.port_edit)

        self.ci_edit = QLineEdit()
        self.ci_edit.setPlaceholderText("Lucas")
        self.ci_edit.textChanged.connect(self._on_changed)
        broker_form.addRow("Client ID (CI):", self.ci_edit)

        self.di_edit = QLineEdit()
        self.di_edit.setPlaceholderText("GW01")
        self.di_edit.textChanged.connect(self._on_changed)
        broker_form.addRow("Device ID (DI):", self.di_edit)

        layout.addWidget(broker_grp)

        # Machine arrays
        arr_grp = QGroupBox("Machine Identity Arrays  (one row per device group)")
        arr_layout = QVBoxLayout(arr_grp)

        arr_layout.addWidget(QLabel(
            "Each row: Slave Number  |  Machine ID  |  Machine Type\n"
            "(All three columns must have the same number of rows)"
        ))

        self.arr_table = QTableWidget(0, 3)
        self.arr_table.setHorizontalHeaderLabels(["Slave Number (SN)", "Machine ID (MI)", "Machine Type (MT)"])
        hdr = self.arr_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.arr_table.setAlternatingRowColors(True)
        self.arr_table.itemChanged.connect(self._on_arr_changed)
        arr_layout.addWidget(self.arr_table)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Add Row")
        add_btn.setObjectName("btn_primary")
        add_btn.clicked.connect(self._add_arr_row)
        del_btn = QPushButton("Delete Row")
        del_btn.setObjectName("btn_danger")
        del_btn.clicked.connect(self._del_arr_row)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        arr_layout.addLayout(btn_row)

        layout.addWidget(arr_grp)

        layout.addWidget(self._make_info_box(
            "The Config_File.json on the ESP32 can override IP and Port at runtime.\n"
            "The values here are stored in ParamMap_Config.json as defaults.\n\n"
            "Machine Identity rows: one per device group. Slave Number is the Modbus ID, "
            "Machine ID is a unique label, Machine Type categorizes the equipment."
        ))

        # Next step
        bottom = QHBoxLayout()
        bottom.addStretch()
        bottom.addWidget(self._make_next_button("Next: Generate JSON  →", 8))
        layout.addLayout(bottom)

    # ------------------------------------------------------------------

    def _ensure_network(self):
        if self.project.network is None:
            self.project.network = NetworkConfig()

    def refresh(self):
        self._updating = True
        self._ensure_network()
        net = self.project.network
        self.ip_edit.setText(net.ip)
        self.port_edit.setText(net.port)
        self.ci_edit.setText(net.client_id)
        self.di_edit.setText(net.device_id)

        self.arr_table.blockSignals(True)
        self.arr_table.setRowCount(0)
        max_len = max(len(net.slave_numbers), len(net.machine_ids), len(net.machine_types), 0)
        for i in range(max_len):
            row = self.arr_table.rowCount()
            self.arr_table.insertRow(row)
            sn = str(net.slave_numbers[i]) if i < len(net.slave_numbers) else ""
            mi = net.machine_ids[i] if i < len(net.machine_ids) else ""
            mt = net.machine_types[i] if i < len(net.machine_types) else ""
            self.arr_table.setItem(row, 0, QTableWidgetItem(sn))
            self.arr_table.setItem(row, 1, QTableWidgetItem(mi))
            self.arr_table.setItem(row, 2, QTableWidgetItem(mt))
        self.arr_table.blockSignals(False)

        self._updating = False

    def _on_changed(self):
        if self._updating:
            return
        self._ensure_network()
        net = self.project.network
        net.ip = self.ip_edit.text().strip()
        net.port = self.port_edit.text().strip()
        net.client_id = self.ci_edit.text().strip()
        net.device_id = self.di_edit.text().strip()
        self.mark_changed()

    def _on_arr_changed(self, item: QTableWidgetItem):
        if self._updating:
            return
        self._sync_arrays()
        self.mark_changed()

    def _sync_arrays(self):
        self._ensure_network()
        net = self.project.network
        sn_list, mi_list, mt_list = [], [], []
        for row in range(self.arr_table.rowCount()):
            sn_item = self.arr_table.item(row, 0)
            mi_item = self.arr_table.item(row, 1)
            mt_item = self.arr_table.item(row, 2)
            try:
                sn_list.append(int(sn_item.text()) if sn_item else 0)
            except ValueError:
                sn_list.append(0)
            mi_list.append(mi_item.text() if mi_item else "")
            mt_list.append(mt_item.text() if mt_item else "")
        net.slave_numbers = sn_list
        net.machine_ids = mi_list
        net.machine_types = mt_list

    def _add_arr_row(self):
        self._updating = True
        row = self.arr_table.rowCount()
        self.arr_table.insertRow(row)
        self.arr_table.setItem(row, 0, QTableWidgetItem("1"))
        self.arr_table.setItem(row, 1, QTableWidgetItem("GWAY01"))
        self.arr_table.setItem(row, 2, QTableWidgetItem("GWAY"))
        self._updating = False
        self._sync_arrays()
        self.mark_changed()

    def _del_arr_row(self):
        rows = sorted(
            {idx.row() for idx in self.arr_table.selectedIndexes()}, reverse=True
        )
        for row in rows:
            self.arr_table.removeRow(row)
        self._sync_arrays()
        self.mark_changed()
