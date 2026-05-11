"""Page 2 — Devices & Slaves."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget,
    QTreeWidgetItem, QLabel, QGroupBox, QFormLayout,
    QLineEdit, QSpinBox, QMessageBox, QInputDialog,
    QWidget, QFrame,
)
from PySide6.QtCore import Qt

from .base_page import BasePage
from ...engine.models import Device, Slave


class DevicesPage(BasePage):
    def __init__(self, main_window):
        super().__init__(
            main_window,
            "Step 2: Devices & Slaves",
            "Add your Modbus devices and their slave addresses. "
            "A 'Device' is a physical machine (e.g., Heat Pump, VFD). "
            "Each device has one or more 'Slaves' (Modbus addresses 1-247).",
        )
        self._updating = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        for w in self._make_header():
            layout.addWidget(w)

        layout.addWidget(self._make_info_box(
            "How to use:\n"
            "1. Click '+ Add Device' -- give it a name (e.g., VFD_1, HeatPump)\n"
            "2. The device appears in the tree. Click on it, then click '+ Add Slave' to assign its Modbus address\n"
            "3. Click a Slave node in the tree to edit its Modbus ID on the right\n"
            "4. Most devices have exactly one slave. Add more slaves only if one machine has multiple controllers."
        ))

        body = QHBoxLayout()
        body.setSpacing(10)

        # Left panel: tree + action buttons
        left_box = QGroupBox("Device / Slave Tree")
        left_layout = QVBoxLayout(left_box)
        left_layout.setSpacing(6)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name / Slave", "Modbus ID"])
        self.tree.setColumnWidth(0, 200)
        self.tree.setColumnWidth(1, 80)
        self.tree.setAlternatingRowColors(True)
        self.tree.setMinimumWidth(300)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self.tree)

        self.empty_label = QLabel(
            "No devices added yet.\n\n"
            "Click  '+ Add Device'  below to start.\n\n"
            "Example device names:\n"
            "  - HeatPump_1\n"
            "  - VFD_Compressor\n"
            "  - Chiller_Plant"
        )
        self.empty_label.setObjectName("empty_state")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setWordWrap(True)
        left_layout.addWidget(self.empty_label)

        btn_row = QHBoxLayout()
        self.add_dev_btn = QPushButton("+ Add Device")
        self.add_dev_btn.setObjectName("btn_primary")
        self.add_dev_btn.setToolTip("Add a new physical device")
        self.add_dev_btn.clicked.connect(self._add_device)

        self.add_slave_btn = QPushButton("+ Add Slave")
        self.add_slave_btn.setObjectName("btn_primary")
        self.add_slave_btn.setToolTip("Add a Modbus slave address under the selected device")
        self.add_slave_btn.clicked.connect(self._add_slave)
        self.add_slave_btn.setEnabled(False)

        btn_row.addWidget(self.add_dev_btn)
        btn_row.addWidget(self.add_slave_btn)
        left_layout.addLayout(btn_row)

        btn_row2 = QHBoxLayout()
        self.rename_btn = QPushButton("Rename Device")
        self.rename_btn.setToolTip("Rename the selected device")
        self.rename_btn.clicked.connect(self._rename_item)
        self.rename_btn.setEnabled(False)

        self.del_btn = QPushButton("Delete")
        self.del_btn.setObjectName("btn_danger")
        self.del_btn.setToolTip("Delete the selected device or slave")
        self.del_btn.clicked.connect(self._delete_item)
        self.del_btn.setEnabled(False)

        btn_row2.addWidget(self.rename_btn)
        btn_row2.addWidget(self.del_btn)
        left_layout.addLayout(btn_row2)

        body.addWidget(left_box, 3)

        # Right panel: properties
        right_box = QGroupBox("Selected Item Properties")
        right_layout = QVBoxLayout(right_box)
        right_layout.setSpacing(8)

        self.props_hint = QLabel(
            "Select a device or slave from the tree to edit it here."
        )
        self.props_hint.setObjectName("empty_state_hint")
        self.props_hint.setWordWrap(True)
        self.props_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.props_hint)

        self.props_form_widget = QWidget()
        form_vl = QVBoxLayout(self.props_form_widget)
        form_vl.setContentsMargins(0, 0, 0, 0)
        form_vl.setSpacing(8)

        self.type_label = QLabel()
        self.type_label.setObjectName("page_subtitle")
        form_vl.addWidget(self.type_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #bdc3c7;")
        form_vl.addWidget(sep)

        props_form = QFormLayout()
        props_form.setSpacing(10)
        props_form.setContentsMargins(4, 4, 4, 4)

        self.props_name_lbl = QLabel("Device Name:")
        self.props_name = QLineEdit()
        self.props_name.setReadOnly(True)
        self.props_name.setToolTip("Use 'Rename Device' button to change the name")
        props_form.addRow(self.props_name_lbl, self.props_name)

        self.props_modbus_lbl = QLabel("Modbus Slave ID:")
        self.props_modbus = QSpinBox()
        self.props_modbus.setRange(1, 247)
        self.props_modbus.setToolTip(
            "Modbus slave address (1-247).\n"
            "Must be unique across all slaves.\n"
            "Match this to the device DIP switch setting."
        )
        self.props_modbus.setEnabled(False)
        self.props_modbus.valueChanged.connect(self._on_modbus_id_changed)
        props_form.addRow(self.props_modbus_lbl, self.props_modbus)

        form_vl.addLayout(props_form)

        self.props_help = QLabel()
        self.props_help.setObjectName("page_subtitle")
        self.props_help.setWordWrap(True)
        form_vl.addWidget(self.props_help)

        right_layout.addWidget(self.props_form_widget)
        self.props_form_widget.setVisible(False)

        right_layout.addStretch()

        ref = QLabel(
            "Quick Reference:\n"
            "- Device = a physical machine (VFD, Heat Pump, etc.)\n"
            "- Slave = its Modbus address on the RS485 bus (1-247)\n"
            "- Slave IDs must be unique across all devices\n"
            "- Most devices have exactly one slave"
        )
        ref.setObjectName("page_subtitle")
        ref.setWordWrap(True)
        right_layout.addWidget(ref)

        body.addWidget(right_box, 2)
        layout.addLayout(body)

        bottom = QHBoxLayout()
        bottom.addStretch()
        bottom.addWidget(self._make_next_button("Next: Define Registers  ->", 2))
        layout.addLayout(bottom)

    # ------------------------------------------------------------------
    # Panel state helpers
    # ------------------------------------------------------------------

    def _show_nothing_selected(self):
        self.props_hint.setVisible(True)
        self.props_form_widget.setVisible(False)
        self.add_slave_btn.setEnabled(False)
        self.rename_btn.setEnabled(False)
        self.del_btn.setEnabled(False)

    def _show_device_selected(self, dev):
        self.props_hint.setVisible(False)
        self.props_form_widget.setVisible(True)

        self.type_label.setText("TYPE: Device")
        self.props_name_lbl.setVisible(True)
        self.props_name.setVisible(True)
        self.props_name.setText(dev.name)

        self.props_modbus_lbl.setVisible(False)
        self.props_modbus.setVisible(False)
        self.props_modbus.setEnabled(False)

        slave_count = len(dev.slaves)
        if slave_count == 0:
            self.props_help.setText(
                "No slaves yet.\n"
                "Click '+ Add Slave' to assign a Modbus address."
            )
        else:
            ids = ", ".join(str(s.modbus_id) for s in dev.slaves)
            self.props_help.setText(
                f"{slave_count} slave(s): Modbus ID {ids}\n"
                "Click a slave in the tree to edit its Modbus ID."
            )

        self.add_slave_btn.setEnabled(True)
        self.rename_btn.setEnabled(True)
        self.del_btn.setEnabled(True)

    def _show_slave_selected(self, sl, dev):
        self.props_hint.setVisible(False)
        self.props_form_widget.setVisible(True)

        self.type_label.setText(f"TYPE: Modbus Slave  (device: {dev.name})")
        self.props_name_lbl.setVisible(False)
        self.props_name.setVisible(False)

        self.props_modbus_lbl.setVisible(True)
        self.props_modbus.setVisible(True)
        self._updating = True
        self.props_modbus.setValue(sl.modbus_id)
        self._updating = False
        self.props_modbus.setEnabled(True)

        reg_count = len(sl.registers)
        self.props_help.setText(
            f"This slave has {reg_count} register(s).\n"
            "Edit the Modbus ID above to match the device setting.\n"
            "Tip: IDs must be unique (1-247) across all slaves."
        )

        self.add_slave_btn.setEnabled(True)
        self.rename_btn.setEnabled(False)
        self.del_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self, select_kind=None, select_obj=None):
        """Rebuild the tree. Optionally force-select a specific item.

        If select_kind/select_obj not given, current selection is preserved.
        """
        self._updating = True

        # Preserve current selection unless caller specifies one
        if select_kind is None and select_obj is None:
            items = self.tree.selectedItems()
            if items:
                data = items[0].data(0, Qt.ItemDataRole.UserRole)
                if data:
                    select_kind, select_obj = data

        self.tree.clear()
        has_devices = bool(self.project.devices)
        self.tree.setVisible(has_devices)
        self.empty_label.setVisible(not has_devices)

        restore_item = None
        for dev in self.project.devices:
            dev_item = QTreeWidgetItem([dev.name, ""])
            dev_item.setData(0, Qt.ItemDataRole.UserRole, ("device", dev))
            if select_kind == "device" and select_obj is dev:
                restore_item = dev_item
            for sl in dev.slaves:
                sl_item = QTreeWidgetItem([f"Slave {sl.modbus_id}", str(sl.modbus_id)])
                sl_item.setData(0, Qt.ItemDataRole.UserRole, ("slave", sl))
                dev_item.addChild(sl_item)
                if select_kind == "slave" and select_obj is sl:
                    restore_item = sl_item
            self.tree.addTopLevelItem(dev_item)
        self.tree.expandAll()

        self._updating = False

        if restore_item is not None:
            self.tree.setCurrentItem(restore_item)
            self.tree.scrollToItem(restore_item)
        else:
            self._show_nothing_selected()

    # ------------------------------------------------------------------
    # Selection changed
    # ------------------------------------------------------------------

    def _on_selection_changed(self):
        if self._updating:
            return
        items = self.tree.selectedItems()
        if not items:
            self._show_nothing_selected()
            return

        data = items[0].data(0, Qt.ItemDataRole.UserRole)
        if data is None:
            self._show_nothing_selected()
            return

        kind, obj = data
        if kind == "device":
            self._show_device_selected(obj)
        else:
            dev = None
            for d in self.project.devices:
                if obj in d.slaves:
                    dev = d
                    break
            if dev is None:
                self._show_nothing_selected()
                return
            self._show_slave_selected(obj, dev)

    # ------------------------------------------------------------------
    # Spinbox handler
    # ------------------------------------------------------------------

    def _on_modbus_id_changed(self, value: int):
        if self._updating:
            return
        items = self.tree.selectedItems()
        if not items:
            return
        data = items[0].data(0, Qt.ItemDataRole.UserRole)
        if data and data[0] == "slave":
            sl = data[1]
            all_ids = [s.modbus_id for s in self.project.all_slaves() if s is not sl]
            if value in all_ids:
                QMessageBox.warning(
                    self, "Duplicate Slave ID",
                    f"Slave ID {value} is already used by another slave.\n"
                    "Each slave must have a unique Modbus address."
                )
                self._updating = True
                self.props_modbus.setValue(sl.modbus_id)
                self._updating = False
                return
            sl.modbus_id = value
            for r in sl.registers:
                r.slave_id = value
            items[0].setText(0, f"Slave {value}")
            items[0].setText(1, str(value))
            # Refresh help text
            dev = None
            for d in self.project.devices:
                if sl in d.slaves:
                    dev = d
                    break
            if dev:
                self._show_slave_selected(sl, dev)
            self.mark_changed()

    # ------------------------------------------------------------------
    # Add / Rename / Delete
    # ------------------------------------------------------------------

    def _add_device(self):
        name, ok = QInputDialog.getText(
            self, "Add Device",
            "Enter a name for this device:\n"
            "(e.g., HeatPump_1, VFD_Compressor, Chiller)\n\n"
            "Use a name that describes the physical equipment.",
        )
        if not ok or not name.strip():
            return
        dev = Device(name=name.strip(), slaves=[])
        self.project.devices.append(dev)
        self.refresh(select_kind="device", select_obj=dev)
        self.mark_changed()

    def _add_slave(self):
        items = self.tree.selectedItems()
        if not items:
            return
        data = items[0].data(0, Qt.ItemDataRole.UserRole)
        if data and data[0] == "slave":
            parent = items[0].parent()
            if parent:
                data = parent.data(0, Qt.ItemDataRole.UserRole)
        if not data or data[0] != "device":
            return
        dev = data[1]
        used = {s.modbus_id for s in self.project.all_slaves()}
        new_id = next((i for i in range(1, 248) if i not in used), 1)
        sl = Slave(modbus_id=new_id, registers=[])
        dev.slaves.append(sl)
        self.refresh(select_kind="slave", select_obj=sl)
        self.mark_changed()

    def _rename_item(self):
        items = self.tree.selectedItems()
        if not items:
            return
        data = items[0].data(0, Qt.ItemDataRole.UserRole)
        if data and data[0] == "device":
            dev = data[1]
            name, ok = QInputDialog.getText(
                self, "Rename Device", "New device name:", text=dev.name
            )
            if ok and name.strip():
                dev.name = name.strip()
                self.refresh(select_kind="device", select_obj=dev)
                self.mark_changed()
        elif data and data[0] == "slave":
            QMessageBox.information(
                self, "Rename Slave",
                "Slaves are identified by their Modbus ID, not a name.\n\n"
                "To change the Modbus address: use the 'Modbus Slave ID' spinbox on the right."
            )

    def _delete_item(self):
        items = self.tree.selectedItems()
        if not items:
            return
        data = items[0].data(0, Qt.ItemDataRole.UserRole)
        if data is None:
            return
        kind, obj = data
        doomed_regs: set[int] = set()

        if kind == "device":
            total_regs = sum(len(s.registers) for s in obj.slaves)
            msg = (
                f"Delete device '{obj.name}'?\n"
                f"This will also delete {len(obj.slaves)} slave(s) and {total_regs} register(s)."
                if obj.slaves else
                f"Delete device '{obj.name}'?"
            )
            if obj.slaves and QMessageBox.question(
                self, "Delete Device", msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            ) != QMessageBox.StandardButton.Yes:
                return
            for sl in obj.slaves:
                for r in sl.registers:
                    doomed_regs.add(id(r))
            self.project.devices.remove(obj)

        else:
            dev = None
            for d in self.project.devices:
                if obj in d.slaves:
                    dev = d
                    break
            if dev is None:
                return
            msg = (
                f"Delete Slave {obj.modbus_id} (under '{dev.name}')?\n"
                f"This will also delete {len(obj.registers)} register(s)."
                if obj.registers else
                f"Delete Slave {obj.modbus_id} (under '{dev.name}')?"
            )
            if obj.registers and QMessageBox.question(
                self, "Delete Slave", msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            ) != QMessageBox.StandardButton.Yes:
                return
            for r in obj.registers:
                doomed_regs.add(id(r))
            dev.slaves.remove(obj)

        if doomed_regs:
            for reg in self.project.all_registers():
                if reg.link_b_register is not None and id(reg.link_b_register) in doomed_regs:
                    reg.link_b_register = None
            for cg in self.project.cloud_groups:
                if cg.source_type == "modbus":
                    cg.registers = [
                        (None if r is not None and id(r) in doomed_regs else r)
                        for r in cg.registers
                    ]

        self.refresh()
        self.mark_changed()
