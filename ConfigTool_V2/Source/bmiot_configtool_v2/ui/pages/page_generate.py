"""Page 9 — Generate JSON.

Runs validation, shows summary counts, lets user pick output directory,
then generates Modbus_Config.json + ParamMap_Config.json and shows previews.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel,
    QGroupBox, QTableWidget, QTableWidgetItem, QTabWidget,
    QListWidget, QListWidgetItem, QFileDialog, QLineEdit,
    QHeaderView, QWidget, QSizePolicy, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QTextCursor

from .base_page import BasePage
from ...engine.generator import generate
from ...engine.validator import validate_project, validate_output
from ...engine.exporter import write_json


class GeneratePage(BasePage):
    def __init__(self, main_window):
        super().__init__(
            main_window,
            "Step 9: Generate JSON Files",
            "Review the project summary, validate your configuration, and generate the "
            "Modbus_Config.json and ParamMap_Config.json files for your gateway.",
        )
        self._last_modbus: dict | None = None
        self._last_parammap: dict | None = None
        self._output_dir: Path | None = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(8)

        for w in self._make_header():
            root.addWidget(w)

        root.addWidget(self._make_info_box(
            "This step validates your entire configuration and generates the two JSON files.\n"
            "1. Review the summary to make sure counts look right.\n"
            "2. Click 'Run Validation' to check for errors before generating.\n"
            "3. Choose an output directory, then click 'Generate JSON Files'."
        ))

        # ── Top row: summary + validation ──────────────────────────
        top = QHBoxLayout()

        # Summary table
        sum_grp = QGroupBox("Project Summary")
        sum_layout = QVBoxLayout(sum_grp)
        self.summary_table = QTableWidget(8, 2)
        self.summary_table.setHorizontalHeaderLabels(["Metric", "Value"])
        hdr = self.summary_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.summary_table.verticalHeader().setVisible(False)
        self.summary_table.setEditTriggers(self.summary_table.EditTrigger.NoEditTriggers)
        self.summary_table.setMaximumHeight(200)
        self.summary_table.setMinimumHeight(180)
        sum_layout.addWidget(self.summary_table)
        top.addWidget(sum_grp, 1)

        # Validation panel
        val_grp = QGroupBox("Validation")
        val_layout = QVBoxLayout(val_grp)
        self.val_list = QListWidget()
        self.val_list.setAlternatingRowColors(True)
        self.val_list.setMaximumHeight(150)
        self.val_list.setMinimumHeight(100)
        val_layout.addWidget(self.val_list)
        val_btn = QPushButton("Run Validation")
        val_btn.clicked.connect(self._run_validation)
        val_layout.addWidget(val_btn)
        top.addWidget(val_grp, 1)

        root.addLayout(top)

        # ── Generate button ─────────────────────────────────────────
        gen_btn = QPushButton("⚡  Generate JSON Files")
        gen_btn.setObjectName("btn_success")
        gen_btn.setMinimumHeight(40)
        gen_btn.clicked.connect(self._generate)
        root.addWidget(gen_btn)

        # ── JSON Preview tabs ───────────────────────────────────────
        preview_label = QLabel("JSON Preview  (generated output shown here — scroll to inspect before saving)")
        preview_label.setObjectName("page_subtitle")
        root.addWidget(preview_label)

        self.tabs = QTabWidget()

        self.modbus_view = QTextEdit()
        self.modbus_view.setObjectName("json_preview")
        self.modbus_view.setReadOnly(True)
        self.modbus_view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.modbus_view.setPlaceholderText(
            "Modbus_Config.json will appear here after you click 'Generate JSON Files'."
        )

        self.parammap_view = QTextEdit()
        self.parammap_view.setObjectName("json_preview")
        self.parammap_view.setReadOnly(True)
        self.parammap_view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.parammap_view.setPlaceholderText(
            "ParamMap_Config.json will appear here after you click 'Generate JSON Files'."
        )

        self.tabs.addTab(self.modbus_view, "Modbus_Config.json")
        self.tabs.addTab(self.parammap_view, "ParamMap_Config.json")
        self.tabs.setMinimumHeight(340)
        root.addWidget(self.tabs, 4)

        # ── Save row ────────────────────────────────────────────────
        save_row = QHBoxLayout()
        save_row.addWidget(QLabel("Save to folder:"))
        self.dir_edit = QLineEdit()
        self.dir_edit.setReadOnly(True)
        self.dir_edit.setPlaceholderText("(click Browse to choose output folder)")
        save_row.addWidget(self.dir_edit, 1)
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse_dir)
        save_row.addWidget(browse_btn)
        self.save_btn = QPushButton("💾  Save JSON Files")
        self.save_btn.setObjectName("btn_primary")
        self.save_btn.setMinimumHeight(34)
        self.save_btn.setEnabled(False)
        self.save_btn.setToolTip("Generate the JSON first, then save to a folder")
        self.save_btn.clicked.connect(self._save_files)
        save_row.addWidget(self.save_btn)
        root.addLayout(save_row)

    # ------------------------------------------------------------------

    def refresh(self):
        self._update_summary()
        self.val_list.clear()
        if self._last_modbus:
            self._show_previews(self._last_modbus, self._last_parammap)

    def _update_summary(self):
        p = self.project
        regs = p.all_registers()
        slaves = p.all_slaves()
        devices = p.devices
        cloud_groups = p.cloud_groups

        link_b_regs = set()
        for r in regs:
            if r.link_b_register is not None:
                link_b_regs.add(id(r.link_b_register))

        write_regs = [r for r in regs if r.fc in (5, 6)]
        nos = len(slaves)
        nop = len(regs)
        nlb_modbus = (len(write_regs) + len(link_b_regs) +
                      sum(1 for r in regs if r.fc not in (5, 6)
                          and id(r) not in link_b_regs and r.needs_lbi_slot))
        nlb_nvs = len(p.nvs_slots)
        nlb = nlb_modbus + nlb_nvs

        total_slots = sum(len(cg.keys) * len(cg.equipment_names) for cg in cloud_groups)

        rows = [
            ("Devices (NRT groups)", str(len(devices))),
            ("Modbus Slaves (NOS)", str(nos)),
            ("Total Registers (NOP)", str(nop)),
            ("Cloud Groups (JKA entries)", str(len(cloud_groups))),
            ("NVS Slots", str(len(p.nvs_slots))),
            ("Total JKA slots (NMD hint)", str(total_slots)),
            ("LBI Slots (NLB)", str(nlb)),
            ("Write Registers (B6 entries)", str(len(write_regs))),
        ]

        self.summary_table.setRowCount(len(rows))
        for i, (metric, value) in enumerate(rows):
            self.summary_table.setItem(i, 0, QTableWidgetItem(metric))
            val_item = QTableWidgetItem(value)
            val_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.summary_table.setItem(i, 1, val_item)

    def _run_validation(self):
        result = validate_project(self.project)
        self.val_list.clear()
        if not result.errors and not result.warnings:
            item = QListWidgetItem("✓  All pre-generation checks passed")
            item.setForeground(QColor("#27ae60"))
            self.val_list.addItem(item)
        else:
            for err in result.errors:
                item = QListWidgetItem(f"✗  {err}")
                item.setForeground(QColor("#e74c3c"))
                self.val_list.addItem(item)
            for warn in result.warnings:
                item = QListWidgetItem(f"⚠  {warn}")
                item.setForeground(QColor("#e67e22"))
                self.val_list.addItem(item)

    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select Output Folder",
                                              str(Path.home()))
        if d:
            self._output_dir = Path(d)
            self.dir_edit.setText(str(self._output_dir))

    def _generate(self):
        # 1. Pre-validation
        pre = validate_project(self.project)
        self.val_list.clear()
        if pre.errors:
            for err in pre.errors:
                item = QListWidgetItem(f"✗  {err}")
                item.setForeground(QColor("#e74c3c"))
                self.val_list.addItem(item)
            item = QListWidgetItem("Generation aborted — fix errors first.")
            item.setForeground(QColor("#e74c3c"))
            self.val_list.addItem(item)
            return

        # 2. Generate
        try:
            modbus, parammap = generate(self.project)
        except Exception as exc:
            item = QListWidgetItem(f"✗  Generation error: {exc}")
            item.setForeground(QColor("#e74c3c"))
            self.val_list.addItem(item)
            return

        # 3. Post-gen validation
        post = validate_output(modbus, parammap)
        for err in post.errors:
            item = QListWidgetItem(f"✗  [Post-gen] {err}")
            item.setForeground(QColor("#e74c3c"))
            self.val_list.addItem(item)
        for warn in post.warnings:
            item = QListWidgetItem(f"⚠  [Post-gen] {warn}")
            item.setForeground(QColor("#e67e22"))
            self.val_list.addItem(item)

        # 4. Always show preview immediately — user can verify before saving
        self._last_modbus = modbus
        self._last_parammap = parammap
        self._show_previews(modbus, parammap)
        self.save_btn.setEnabled(not post.errors)

        if post.errors:
            item = QListWidgetItem("Preview shown — fix errors before saving.")
            item.setForeground(QColor("#e67e22"))
            self.val_list.addItem(item)
            return

        item = QListWidgetItem("✓  Generation successful — review the preview below, then click 'Save JSON Files'.")
        item.setForeground(QColor("#27ae60"))
        self.val_list.addItem(item)
        self._main_window.statusBar().showMessage(
            "JSON generated — review the preview, then click 'Save JSON Files'.", 8000
        )

    def _save_files(self):
        if self._last_modbus is None:
            return
        if self._output_dir is None:
            d = QFileDialog.getExistingDirectory(self, "Select Output Folder",
                                                  str(Path.home()))
            if not d:
                return
            self._output_dir = Path(d)
            self.dir_edit.setText(str(self._output_dir))

        mb_path = self._output_dir / "Modbus_Config.json"
        pm_path = self._output_dir / "ParamMap_Config.json"

        if mb_path.exists() or pm_path.exists():
            answer = QMessageBox.question(
                self, "Overwrite Files?",
                f"Files already exist in:\n{self._output_dir}\n\n"
                "  • Modbus_Config.json\n  • ParamMap_Config.json\n\nOverwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        write_json(self._last_modbus, mb_path)
        write_json(self._last_parammap, pm_path)

        self.val_list.clear()
        for path in (mb_path, pm_path):
            item = QListWidgetItem(f"✓  Saved:  {path}")
            item.setForeground(QColor("#27ae60"))
            self.val_list.addItem(item)
        self._main_window.statusBar().showMessage(
            f"Files saved to {self._output_dir}", 8000
        )

    def _show_previews(self, modbus: dict, parammap: dict):
        self.modbus_view.setPlainText(
            json.dumps(modbus, indent=2, ensure_ascii=False)
        )
        self.parammap_view.setPlainText(
            json.dumps(parammap, indent=2, ensure_ascii=False)
        )
        # Scroll both to top
        self.modbus_view.moveCursor(QTextCursor.MoveOperation.Start)
        self.parammap_view.moveCursor(QTextCursor.MoveOperation.Start)
