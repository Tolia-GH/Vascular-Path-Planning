# 路径规划结果信息展示面板。

from __future__ import annotations

from PyQt5 import QtWidgets


class PathInfoPanel(QtWidgets.QGroupBox):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__("路径信息", parent)

        layout = QtWidgets.QFormLayout(self)
        layout.setContentsMargins(6, 14, 6, 6)
        layout.setSpacing(4)

        self._length_value = QtWidgets.QLabel("--")
        layout.addRow("长度 (mm):", self._length_value)

        self._nodes_value = QtWidgets.QLabel("--")
        layout.addRow("节点数:", self._nodes_value)

        self._curv_max_value = QtWidgets.QLabel("--")
        layout.addRow("最大曲率 (1/mm):", self._curv_max_value)

        self._curv_mean_value = QtWidgets.QLabel("--")
        layout.addRow("平均曲率 (1/mm):", self._curv_mean_value)

        self._radius_value = QtWidgets.QLabel("--")
        layout.addRow("最小转弯半径 (mm):", self._radius_value)

        self._feasibility_value = QtWidgets.QLabel("--")
        self._feasibility_value.setStyleSheet("font-weight: bold;")
        layout.addRow("可行性:", self._feasibility_value)

        self._elapsed_value = QtWidgets.QLabel("--")
        layout.addRow("规划耗时 (ms):", self._elapsed_value)

    def update_from_summary(
        self,
        summary: dict,
        elapsed_ms: float | None = None,
    ) -> None:
        # summary 来自 PathAnalyzer / PlanResult.summary。

        length = summary.get("length_mm", "--")
        self._length_value.setText(f"{length:.2f}" if isinstance(length, (int, float)) else str(length))

        nodes = summary.get("node_count", "--")
        self._nodes_value.setText(str(nodes))

        curv_max = summary.get("curvature_max_per_mm", "--")
        self._curv_max_value.setText(
            f"{curv_max:.6f}" if isinstance(curv_max, (int, float)) else str(curv_max)
        )

        curv_mean = summary.get("curvature_mean_per_mm", "--")
        self._curv_mean_value.setText(
            f"{curv_mean:.6f}" if isinstance(curv_mean, (int, float)) else str(curv_mean)
        )

        radius = summary.get("min_radius_mm", "--")
        if radius is None:
            self._radius_value.setText("N/A")
        elif isinstance(radius, (int, float)):
            self._radius_value.setText(f"{radius:.2f}")
        else:
            self._radius_value.setText(str(radius))

        feasibility = summary.get("feasibility", "--")
        self._feasibility_value.setText(str(feasibility))
        # 根据可行性等级设置颜色
        color_map = {
            "green": "#00aa44",
            "yellow": "#ddaa00",
            "orange": "#ee7700",
            "red": "#cc0000",
        }
        color = color_map.get(str(feasibility), "#333333")
        self._feasibility_value.setStyleSheet(f"font-weight: bold; color: {color};")

        if elapsed_ms is not None:
            self._elapsed_value.setText(f"{elapsed_ms:.2f}")
        else:
            self._elapsed_value.setText("--")

    def clear(self) -> None:
        self._length_value.setText("--")
        self._nodes_value.setText("--")
        self._curv_max_value.setText("--")
        self._curv_mean_value.setText("--")
        self._radius_value.setText("--")
        self._feasibility_value.setText("--")
        self._feasibility_value.setStyleSheet("font-weight: bold; color: #333333;")
        self._elapsed_value.setText("--")