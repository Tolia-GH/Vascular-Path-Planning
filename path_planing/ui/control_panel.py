# 路径规划控制面板，包含选点、规划、清除操作及状态显示。

from __future__ import annotations

from PyQt5 import QtCore, QtWidgets


class ControlPanel(QtWidgets.QGroupBox):
    # 信号：请求切换至“选择起点”模式。
    select_start_requested = QtCore.pyqtSignal()
    # 信号：请求切换至“选择终点”模式。
    select_goal_requested = QtCore.pyqtSignal()
    # 信号：请求执行路径规划。
    plan_requested = QtCore.pyqtSignal()
    # 信号：请求清除当前路径和选点状态。
    clear_requested = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__("控制", parent)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 14, 6, 6)
        layout.setSpacing(6)

        # 模式标签
        self._mode_label = QtWidgets.QLabel("模式：空闲")
        self._mode_label.setStyleSheet("font-weight: bold; color: #0055aa;")
        layout.addWidget(self._mode_label)

        # 点击坐标
        self._pick_coords_line = QtWidgets.QLineEdit(self)
        self._pick_coords_line.setReadOnly(True)
        self._pick_coords_line.setPlaceholderText("点击坐标 (x, y, z)")
        layout.addWidget(QtWidgets.QLabel("点击坐标:"))
        layout.addWidget(self._pick_coords_line)

        # 吸附节点
        self._snap_node_line = QtWidgets.QLineEdit(self)
        self._snap_node_line.setReadOnly(True)
        self._snap_node_line.setPlaceholderText("吸附图节点")
        layout.addWidget(QtWidgets.QLabel("吸附节点:"))
        layout.addWidget(self._snap_node_line)

        # 吸附距离
        self._snap_dist_line = QtWidgets.QLineEdit(self)
        self._snap_dist_line.setReadOnly(True)
        self._snap_dist_line.setPlaceholderText("-- mm")
        layout.addWidget(QtWidgets.QLabel("吸附距离:"))
        layout.addWidget(self._snap_dist_line)

        # 起点
        self._start_line = QtWidgets.QLineEdit(self)
        self._start_line.setReadOnly(True)
        self._start_line.setPlaceholderText("未选择")
        layout.addWidget(QtWidgets.QLabel("起点:"))
        layout.addWidget(self._start_line)

        # 终点
        self._goal_line = QtWidgets.QLineEdit(self)
        self._goal_line.setReadOnly(True)
        self._goal_line.setPlaceholderText("未选择")
        layout.addWidget(QtWidgets.QLabel("终点:"))
        layout.addWidget(self._goal_line)

        # 按钮行
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setSpacing(4)

        self._start_btn = QtWidgets.QPushButton("选择起点", self)
        self._start_btn.setCheckable(True)
        self._start_btn.clicked.connect(self._on_start_clicked)
        btn_layout.addWidget(self._start_btn)

        self._goal_btn = QtWidgets.QPushButton("选择终点", self)
        self._goal_btn.setCheckable(True)
        self._goal_btn.clicked.connect(self._on_goal_clicked)
        btn_layout.addWidget(self._goal_btn)

        layout.addLayout(btn_layout)

        self._plan_btn = QtWidgets.QPushButton("规划路径", self)
        self._plan_btn.setEnabled(False)
        self._plan_btn.clicked.connect(self.plan_requested.emit)
        layout.addWidget(self._plan_btn)

        self._clear_btn = QtWidgets.QPushButton("清除路径", self)
        self._clear_btn.setEnabled(False)
        self._clear_btn.clicked.connect(self.clear_requested.emit)
        layout.addWidget(self._clear_btn)

        layout.addStretch()

        # 内部状态：当前模式与选点数据
        self._mode: str = "idle"  # idle / start / goal
        self._picked_coords: tuple[float, float, float] | None = None
        self._snapped_node: tuple[float, float, float] | None = None
        self._snap_distance_mm: float | None = None
        self._start_node: tuple[float, float, float] | None = None
        self._goal_node: tuple[float, float, float] | None = None

    # ---- 模式控制 ----

    @property
    def mode(self) -> str:
        return self._mode

    def set_mode_idle(self) -> None:
        self._mode = "idle"
        self._mode_label.setText("模式：空闲")
        self._start_btn.setChecked(False)
        self._goal_btn.setChecked(False)
        self._update_buttons()

    def set_mode_start(self) -> None:
        self._mode = "start"
        self._mode_label.setText("模式：⏺ 选择起点 — 请点击3D模型")
        self._start_btn.setChecked(True)
        self._goal_btn.setChecked(False)

    def set_mode_goal(self) -> None:
        self._mode = "goal"
        self._mode_label.setText("模式：⏺ 选择终点 — 请点击3D模型")
        self._goal_btn.setChecked(True)
        self._start_btn.setChecked(False)

    # ---- 选点数据设置 ----

    def set_pick_result(
        self,
        coords: tuple[float, float, float],
        snapped_node: tuple[float, float, float],
        snap_distance_mm: float,
    ) -> None:
        self._picked_coords = coords
        self._snapped_node = snapped_node
        self._snap_distance_mm = snap_distance_mm

        self._pick_coords_line.setText(
            f"{coords[0]:.3f}, {coords[1]:.3f}, {coords[2]:.3f}"
        )
        self._snap_node_line.setText(
            f"{snapped_node[0]:.3f}, {snapped_node[1]:.3f}, {snapped_node[2]:.3f}"
        )
        self._snap_dist_line.setText(f"{snap_distance_mm:.3f}")

        if self._mode == "start":
            self._start_node = snapped_node
            self._start_line.setText(
                f"{snapped_node[0]:.3f}, {snapped_node[1]:.3f}, {snapped_node[2]:.3f}"
            )
            self.set_mode_idle()
        elif self._mode == "goal":
            self._goal_node = snapped_node
            self._goal_line.setText(
                f"{snapped_node[0]:.3f}, {snapped_node[1]:.3f}, {snapped_node[2]:.3f}"
            )
            self.set_mode_idle()

        self._update_buttons()

    # ---- 规划数据访问 ----

    @property
    def start_node(self) -> tuple[float, float, float] | None:
        return self._start_node

    @property
    def goal_node(self) -> tuple[float, float, float] | None:
        return self._goal_node

    @property
    def is_ready_to_plan(self) -> bool:
        return self._start_node is not None and self._goal_node is not None

    def mark_planned(self) -> None:
        # 规划成功后启用“清除路径”。
        self._clear_btn.setEnabled(True)
        self._plan_btn.setEnabled(False)

    # ---- 清除 ----

    def clear_all(self) -> None:
        self._picked_coords = None
        self._snapped_node = None
        self._snap_distance_mm = None
        self._start_node = None
        self._goal_node = None

        self._pick_coords_line.clear()
        self._snap_node_line.clear()
        self._snap_dist_line.clear()
        self._start_line.clear()
        self._goal_line.clear()

        self.set_mode_idle()
        self._update_buttons()
        self._clear_btn.setEnabled(False)

    # ---- 内部辅助 ----

    def _update_buttons(self) -> None:
        self._plan_btn.setEnabled(self.is_ready_to_plan)

    def _on_start_clicked(self) -> None:
        if self._mode == "start":
            self.set_mode_idle()
            return
        self.set_mode_start()
        self.select_start_requested.emit()

    def _on_goal_clicked(self) -> None:
        if self._mode == "goal":
            self.set_mode_idle()
            return
        self.set_mode_goal()
        self.select_goal_requested.emit()