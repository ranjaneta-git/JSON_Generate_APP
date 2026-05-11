"""Base class shared by all UI pages."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
from PySide6.QtCore import Qt


class BasePage(QWidget):
    """Every page inherits this.  Provides title, subtitle, and project access."""

    def __init__(self, main_window, title: str, subtitle: str = ""):
        super().__init__()
        self._main_window = main_window
        self._title = title
        self._subtitle = subtitle

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @property
    def project(self):
        return self._main_window.project

    def mark_changed(self):
        """Call after any modification to the project model."""
        self._main_window.on_project_changed()

    def go_to_page(self, idx: int):
        """Navigate to another page by index (0-based)."""
        self._main_window._switch_page(idx)

    # ------------------------------------------------------------------
    # Helpers for subclasses to build consistent headers
    # ------------------------------------------------------------------

    def _make_header(self) -> list[QWidget]:
        """Return [title_label, subtitle_label, separator] widgets."""
        title_lbl = QLabel(self._title)
        title_lbl.setObjectName("page_title")

        widgets: list[QWidget] = [title_lbl]

        if self._subtitle:
            sub_lbl = QLabel(self._subtitle)
            sub_lbl.setObjectName("page_subtitle")
            sub_lbl.setWordWrap(True)
            widgets.append(sub_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        widgets.append(sep)

        return widgets

    @staticmethod
    def _make_info_box(text: str) -> QFrame:
        """Light-blue information box."""
        frame = QFrame()
        frame.setObjectName("info_box")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(10, 8, 10, 8)
        lbl = QLabel(text)
        lbl.setObjectName("info_text")
        lbl.setWordWrap(True)
        lay.addWidget(lbl)
        return frame

    @staticmethod
    def _make_workflow_hint(text: str) -> QFrame:
        """Yellow workflow hint box."""
        frame = QFrame()
        frame.setObjectName("workflow_hint")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(10, 8, 10, 8)
        lbl = QLabel(text)
        lbl.setObjectName("workflow_hint_text")
        lbl.setWordWrap(True)
        lay.addWidget(lbl)
        return frame

    @staticmethod
    def _make_empty_state(title: str, hint: str) -> QWidget:
        """Big centered empty-state placeholder."""
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t = QLabel(title)
        t.setObjectName("empty_state_title")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h = QLabel(hint)
        h.setObjectName("empty_state_hint")
        h.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h.setWordWrap(True)
        lay.addWidget(t)
        lay.addWidget(h)
        return container

    def _make_next_button(self, label: str, page_idx: int) -> QPushButton:
        """Create a 'Next Step →' button that navigates to given page."""
        btn = QPushButton(label)
        btn.setObjectName("btn_next")
        btn.clicked.connect(lambda: self.go_to_page(page_idx))
        return btn

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Called when this page becomes visible or the project changes.
        Subclasses must override to reload data from project into UI."""
        pass
