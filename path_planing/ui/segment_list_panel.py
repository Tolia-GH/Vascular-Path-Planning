# 中心线段列表面板，支持点击高亮联动。

from __future__ import annotations

from PyQt5 import QtCore, QtWidgets
from path_planing.render.centerline_renderer import CenterlineSegment


class SegmentListPanel(QtWidgets.QGroupBox):
    # 对外发送选中段索引；None 表示取消高亮。
    segment_selected = QtCore.pyqtSignal(object)  # int | None

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__("中心线段", parent)

        self._segments: list[CenterlineSegment] = []

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 14, 6, 6)
        layout.setSpacing(2)

        self._list_widget = QtWidgets.QListWidget(self)
        self._list_widget.currentRowChanged.connect(self._on_selection_changed)
        layout.addWidget(self._list_widget)

        # 初始添加“无高亮”项，索引 0 对应取消选中
        self._list_widget.addItem("无高亮")

    def set_segments(self, segments: list[CenterlineSegment]) -> None:
        # 根据加载后的中心线段刷新列表。
        self._segments = list(segments)
        self._list_widget.blockSignals(True)
        self._list_widget.clear()
        self._list_widget.addItem("无高亮")
        for seg in self._segments:
            self._list_widget.addItem(f"segment_{seg.index}  ({seg.point_count} pts)")
        self._list_widget.setCurrentRow(0)
        self._list_widget.blockSignals(False)

    @property
    def current_segment_index(self) -> int | None:
        row = self._list_widget.currentRow()
        if row <= 0:
            return None
        return row - 1  # 减去“无高亮”行

    def clear(self) -> None:
        self._list_widget.blockSignals(True)
        self._list_widget.clear()
        self._list_widget.addItem("无高亮")
        self._list_widget.setCurrentRow(0)
        self._list_widget.blockSignals(False)
        self._segments = []

    def _on_selection_changed(self, current_row: int) -> None:
        if current_row <= 0:
            self.segment_selected.emit(None)
        else:
            self.segment_selected.emit(current_row - 1)