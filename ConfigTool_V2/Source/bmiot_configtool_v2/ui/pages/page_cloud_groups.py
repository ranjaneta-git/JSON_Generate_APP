"""Page 6 — Cloud Groups (JKA Editor).

Each Cloud Group becomes one JKA entry in ParamMap_Config.json.
The firmware builds the MQTT JSON payload by walking JKA entries and consuming
M_data[] values sequentially:
    for each equipment_name → for each key → M_data[ptr++]
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
    QListWidgetItem, QLabel, QGroupBox, QFormLayout,
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QSplitter, QWidget, QHeaderView, QAbstractItemView, QMessageBox,
)
from PySide6.QtCore import Qt

from .base_page import BasePage
from ...engine.models import CloudGroup


class CloudGroupsPage(BasePage):
    def __init__(self, main_window):
        super().__init__(
            main_window,
            "Step 6: Cloud Groups (MQTT Telemetry)",
            "Define how register values are grouped and sent to the cloud via MQTT. "
            "Each group becomes a JSON object in the telemetry payload.",
        )
        self._updating = False
        self._current_idx = -1
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        for w in self._make_header():
            layout.addWidget(w)

        layout.addWidget(self._make_info_box(
            "Each cloud group maps equipment readings to an MQTT telemetry topic.\n"
            "• Cluster Name: a label for this group (e.g., HP_Status, VFD_Data)\n"
            "• Keys: measurement types as comma-separated values (e.g., St  or  DegC,Hz,Amps)\n"
            "• Equipment Names: comma-separated device labels (e.g., HP_Run,Circ_Run)\n"
            "• Then assign a register to each (Equipment × Key) slot below.\n\n"
            "Rule: All Modbus groups must come before NVS groups."
        ))

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Left panel: group list ──────────────────────────────────
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 4, 0)
        ll.addWidget(QLabel("Cloud Groups:"))
        self.group_list = QListWidget()
        self.group_list.currentRowChanged.connect(self._on_group_selected)
        ll.addWidget(self.group_list)

        btn1 = QHBoxLayout()
        add_mb = QPushButton("+ Modbus Group")
        add_mb.setObjectName("btn_primary")
        add_mb.clicked.connect(lambda: self._add_group("modbus"))
        add_nvs = QPushButton("+ NVS Group")
        add_nvs.clicked.connect(lambda: self._add_group("nvs"))
        btn1.addWidget(add_mb)
        btn1.addWidget(add_nvs)
        ll.addLayout(btn1)

        btn2 = QHBoxLayout()
        del_btn = QPushButton("Delete")
        del_btn.setObjectName("btn_danger")
        del_btn.clicked.connect(self._delete_group)
        up_btn = QPushButton("↑ Up")
        up_btn.clicked.connect(self._move_up)
        dn_btn = QPushButton("↓ Down")
        dn_btn.clicked.connect(self._move_down)
        btn2.addWidget(del_btn)
        btn2.addWidget(up_btn)
        btn2.addWidget(dn_btn)
        ll.addLayout(btn2)

        splitter.addWidget(left)

        # ── Right panel: group editor ───────────────────────────────
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(4, 0, 0, 0)

        self.edit_box = QGroupBox("Group Details")
        form = QFormLayout(self.edit_box)
        form.setSpacing(8)
        form.setContentsMargins(10, 14, 10, 10)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. HP_Status")
        self.name_edit.textChanged.connect(self._on_field_changed)
        form.addRow("Cluster Name:", self.name_edit)

        self.src_combo = QComboBox()
        self.src_combo.addItem("Modbus  (maps to Modbus registers)", "modbus")
        self.src_combo.addItem("NVS  (maps to NVS/RAM slots)", "nvs")
        self.src_combo.currentIndexChanged.connect(self._on_field_changed)
        form.addRow("Source Type:", self.src_combo)

        keys_hint = QLabel("Comma-separated, e.g.  St   or   DegC,Hz")
        keys_hint.setObjectName("page_subtitle")
        form.addRow(keys_hint)
        self.keys_edit = QLineEdit()
        self.keys_edit.setPlaceholderText("St")
        self.keys_edit.textChanged.connect(self._on_keys_names_changed)
        form.addRow("Keys:", self.keys_edit)

        names_hint = QLabel("Comma-separated, e.g.  HP_Run,Circ_Run")
        names_hint.setObjectName("page_subtitle")
        form.addRow(names_hint)
        self.eq_edit = QLineEdit()
        self.eq_edit.setPlaceholderText("HP_Run")
        self.eq_edit.textChanged.connect(self._on_keys_names_changed)
        form.addRow("Equipment Names:", self.eq_edit)

        rl.addWidget(self.edit_box)

        # Assignment table
        assign_lbl = QLabel("Slot Assignments  (Equipment Name  →  Key  →  Register / NVS Slot):")
        rl.addWidget(assign_lbl)

        self.slot_table = QTableWidget(0, 3)
        self.slot_table.setHorizontalHeaderLabels(
            ["Equipment Name", "Key", "Assigned Register / NVS Slot"]
        )
        hdr = self.slot_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.slot_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.slot_table.setAlternatingRowColors(True)
        rl.addWidget(self.slot_table)

        splitter.addWidget(right)
        splitter.setSizes([240, 700])
        layout.addWidget(splitter)

        # Next step
        bottom = QHBoxLayout()
        bottom.addStretch()
        bottom.addWidget(self._make_next_button("Next: NVS Setpoints  →", 6))
        layout.addLayout(bottom)

        self._set_edit_enabled(False)

    def _set_edit_enabled(self, en: bool):
        self.edit_box.setEnabled(en)
        self.slot_table.setEnabled(en)

    # ------------------------------------------------------------------

    def refresh(self):
        saved_idx = self._current_idx
        self._updating = True
        self.group_list.clear()
        for cg in self.project.cloud_groups:
            tag = "[Modbus]" if cg.source_type == "modbus" else "[NVS]"
            self.group_list.addItem(f"{tag} {cg.cluster_name}")

        # Restore selection
        if 0 <= saved_idx < self.group_list.count():
            self.group_list.setCurrentRow(saved_idx)
        elif self.group_list.count() > 0:
            self.group_list.setCurrentRow(0)
        else:
            self._current_idx = -1
            self._set_edit_enabled(False)

        self._updating = False

    def _on_group_selected(self, idx: int):
        self._current_idx = idx
        if idx < 0 or idx >= len(self.project.cloud_groups):
            self._set_edit_enabled(False)
            return
        self._set_edit_enabled(True)
        self._load_group(self.project.cloud_groups[idx])

    def _load_group(self, cg: CloudGroup):
        self._updating = True
        self.name_edit.setText(cg.cluster_name)
        src_idx = 0 if cg.source_type == "modbus" else 1
        self.src_combo.setCurrentIndex(src_idx)
        self.keys_edit.setText(",".join(cg.keys))
        self.eq_edit.setText(",".join(cg.equipment_names))
        self._updating = False
        self._rebuild_slot_table(cg)

    def _on_field_changed(self):
        if self._updating:
            return
        idx = self._current_idx
        if idx < 0 or idx >= len(self.project.cloud_groups):
            return
        cg = self.project.cloud_groups[idx]
        cg.cluster_name = self.name_edit.text().strip() or "Group"
        new_src = self.src_combo.currentData()

        # If source type changed, clear stale assignments and validate ordering
        if new_src != cg.source_type:
            old_src = cg.source_type
            cg.source_type = new_src

            # Clear the opposite assignment list
            if new_src == "modbus":
                cg.nvs_slots.clear()
            else:
                cg.registers.clear()

            # Validate Modbus-before-NVS ordering
            cgs = self.project.cloud_groups
            if new_src == "nvs":
                # Check if any Modbus group comes after this one
                for i in range(idx + 1, len(cgs)):
                    if cgs[i].source_type == "modbus":
                        # Move this group to just before the NVS section
                        cg.source_type = old_src  # revert
                        self._updating = True
                        self.src_combo.setCurrentIndex(0 if old_src == "modbus" else 1)
                        self._updating = False
                        QMessageBox.warning(
                            self, "Order Constraint",
                            "Cannot change to NVS — all Modbus groups must come before NVS groups.\n"
                            "Move this group after all Modbus groups first, or delete conflicting groups."
                        )
                        return
            elif new_src == "modbus":
                # Check if any NVS group comes before this one
                for i in range(0, idx):
                    if cgs[i].source_type == "nvs":
                        cg.source_type = old_src  # revert
                        self._updating = True
                        self.src_combo.setCurrentIndex(0 if old_src == "modbus" else 1)
                        self._updating = False
                        QMessageBox.warning(
                            self, "Order Constraint",
                            "Cannot change to Modbus — all Modbus groups must come before NVS groups.\n"
                            "Move this group before any NVS groups first."
                        )
                        return

            # Rebuild the slot table with the new source type's options
            self._rebuild_slot_table(cg)
        else:
            cg.source_type = new_src

        # Update list label
        tag = "[Modbus]" if cg.source_type == "modbus" else "[NVS]"
        self.group_list.item(idx).setText(f"{tag} {cg.cluster_name}")
        self.mark_changed()

    def _on_keys_names_changed(self):
        if self._updating:
            return
        idx = self._current_idx
        if idx < 0 or idx >= len(self.project.cloud_groups):
            return
        cg = self.project.cloud_groups[idx]
        old_keys = cg.keys
        old_names = cg.equipment_names
        old_regs = list(cg.registers)
        old_nvs = list(cg.nvs_slots)

        new_keys = [k.strip() for k in self.keys_edit.text().split(",") if k.strip()]
        new_names = [n.strip() for n in self.eq_edit.text().split(",") if n.strip()]
        new_slot_count = len(new_keys) * len(new_names)

        # Preserve as many existing assignments as possible (by slot index)
        if cg.source_type == "modbus":
            new_regs = [old_regs[i] if i < len(old_regs) else None
                        for i in range(new_slot_count)]
            cg.registers = new_regs  # type: ignore[assignment]
        else:
            new_nvs = [old_nvs[i] if i < len(old_nvs) else None
                       for i in range(new_slot_count)]
            cg.nvs_slots = new_nvs  # type: ignore[assignment]

        cg.keys = new_keys
        cg.equipment_names = new_names

        self._rebuild_slot_table(cg)
        self.mark_changed()

    def _rebuild_slot_table(self, cg: CloudGroup):
        self._updating = True
        self.slot_table.setRowCount(0)

        keys = cg.keys
        names = cg.equipment_names
        if not keys or not names:
            self._updating = False
            return

        all_regs = self.project.all_registers()
        all_nvs = self.project.nvs_slots

        slot_idx = 0
        for name in names:
            for key in keys:
                row = self.slot_table.rowCount()
                self.slot_table.insertRow(row)
                self.slot_table.setItem(row, 0, QTableWidgetItem(name))
                self.slot_table.setItem(row, 1, QTableWidgetItem(key))

                combo = QComboBox()
                combo.addItem("— Not assigned —", None)

                if cg.source_type == "modbus":
                    for reg in all_regs:
                        lbl = f"{reg.name}  [S{reg.slave_id} FC{reg.fc} @{reg.address}]"
                        combo.addItem(lbl, reg)
                    # Set current
                    assignments = getattr(cg, "registers", [])
                    current = assignments[slot_idx] if slot_idx < len(assignments) else None
                    if current is not None:
                        for i in range(combo.count()):
                            if combo.itemData(i) is current:
                                combo.setCurrentIndex(i)
                                break
                else:
                    for nvs in all_nvs:
                        combo.addItem(f"{nvs.key_name}  [NVS]", nvs)
                    assignments = getattr(cg, "nvs_slots", [])
                    current = assignments[slot_idx] if slot_idx < len(assignments) else None
                    if current is not None:
                        for i in range(combo.count()):
                            if combo.itemData(i) is current:
                                combo.setCurrentIndex(i)
                                break

                # Capture slot_idx for the lambda
                combo.currentIndexChanged.connect(
                    lambda _, si=slot_idx, cb=combo, c=cg: self._on_slot_assigned(c, si, cb)
                )
                self.slot_table.setCellWidget(row, 2, combo)
                slot_idx += 1

        self._updating = False

    def _on_slot_assigned(self, cg: CloudGroup, slot_idx: int, combo: QComboBox):
        if self._updating:
            return
        val = combo.currentData()
        if cg.source_type == "modbus":
            # Ensure list is long enough
            while len(cg.registers) <= slot_idx:
                cg.registers.append(None)  # type: ignore[arg-type]
            cg.registers[slot_idx] = val  # type: ignore[index]
        else:
            while len(cg.nvs_slots) <= slot_idx:
                cg.nvs_slots.append(None)  # type: ignore[arg-type]
            cg.nvs_slots[slot_idx] = val  # type: ignore[index]
        self.mark_changed()

    # ------------------------------------------------------------------

    def _add_group(self, source_type: str):
        name = f"Group_{len(self.project.cloud_groups) + 1}"
        cg = CloudGroup(cluster_name=name, keys=["St"], equipment_names=["Eq1"],
                        source_type=source_type)
        # Maintain Modbus-before-NVS ordering
        if source_type == "modbus":
            # Insert before first NVS group
            insert_idx = len(self.project.cloud_groups)
            for i, g in enumerate(self.project.cloud_groups):
                if g.source_type == "nvs":
                    insert_idx = i
                    break
            self.project.cloud_groups.insert(insert_idx, cg)
            self._current_idx = insert_idx
        else:
            self.project.cloud_groups.append(cg)
            self._current_idx = len(self.project.cloud_groups) - 1
        self.refresh()
        self.mark_changed()

    def _delete_group(self):
        idx = self._current_idx
        if idx < 0 or idx >= len(self.project.cloud_groups):
            return
        self.project.cloud_groups.pop(idx)
        self._current_idx = max(0, idx - 1)
        self.refresh()
        self.mark_changed()

    def _move_up(self):
        idx = self._current_idx
        if idx <= 0 or idx >= len(self.project.cloud_groups):
            return
        cgs = self.project.cloud_groups
        # Don't allow NVS to move above Modbus
        if cgs[idx - 1].source_type == "modbus" and cgs[idx].source_type == "nvs":
            QMessageBox.warning(self, "Order Constraint",
                "NVS groups must come after all Modbus groups.")
            return
        cgs[idx - 1], cgs[idx] = cgs[idx], cgs[idx - 1]
        self._current_idx = idx - 1
        self.refresh()
        self.mark_changed()

    def _move_down(self):
        idx = self._current_idx
        cgs = self.project.cloud_groups
        if idx < 0 or idx >= len(cgs) - 1:
            return
        if cgs[idx].source_type == "modbus" and cgs[idx + 1].source_type == "nvs":
            QMessageBox.warning(self, "Order Constraint",
                "NVS groups must come after all Modbus groups.")
            return
        cgs[idx], cgs[idx + 1] = cgs[idx + 1], cgs[idx]
        self._current_idx = idx + 1
        self.refresh()
        self.mark_changed()
