# 主窗口 — 组合 3D 视图、控制面板、段列表面板、路径信息面板，完成规划闭环。

from __future__ import annotations

import time
from pathlib import Path

from PyQt5 import QtCore, QtWidgets

from path_planing.engine import GraphLoader, Node3D, PathAnalyzer, PathPlanner
from path_planing.render import CenterlineSegment
from path_planing.ui.control_panel import ControlPanel
from path_planing.ui.path_info_panel import PathInfoPanel
from path_planing.ui.segment_list_panel import SegmentListPanel
from path_planing.ui.viewer_3d import Viewer3D
from path_planing.utils.kd_tree import KDTreeSnapper

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GRAPH_PATH = PROJECT_ROOT / "source" / "graphs" / "centerline_vessel_net.json"
DEFAULT_VESSEL_PATH = PROJECT_ROOT / "source" / "vtk" / "blood_vessels.vtk"
DEFAULT_CENTERLINE_PATH = PROJECT_ROOT / "source" / "vtk" / "Centerline_curves_merged.vtk"


class MainWindow(QtWidgets.QMainWindow):
    def __init__(
        self,
        vessel_path: str | Path = DEFAULT_VESSEL_PATH,
        centerline_path: str | Path = DEFAULT_CENTERLINE_PATH,
        graph_path: str | Path = DEFAULT_GRAPH_PATH,
        load_default_data: bool = True,
        viewer_off_screen: bool | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        # ---- 路径配置 ----
        self.vessel_path = Path(vessel_path)
        self.centerline_path = Path(centerline_path)
        self.graph_path = Path(graph_path)

        # ---- 引擎层 ----
        self.graph_loader = GraphLoader()
        self.planner = PathPlanner()
        self.analyzer = PathAnalyzer()
        self.kd_tree = KDTreeSnapper()
        self._pick_mode: str | None = None

        # ---- 视图 ----
        self.viewer_3d = Viewer3D(self, off_screen=viewer_off_screen)

        # ---- 右侧面板 ----
        self.control_panel = ControlPanel(self)
        self.path_info_panel = PathInfoPanel(self)
        self.segment_list_panel = SegmentListPanel(self)

        self.setWindowTitle("血管路径规划 3D 演示")
        self.resize(1400, 900)
        self.setMinimumSize(1024, 768)

        self._build_menu_bar()
        self._build_top_info_bar()
        self._build_central_splitter()
        self._build_status_bar()
        self._connect_signals()

        if load_default_data:
            self.load_default_scene()

    # ============================
    #  UI 构建
    # ============================

    def _build_menu_bar(self) -> None:
        file_menu = self.menuBar().addMenu("文件")
        exit_action = file_menu.addAction("退出")
        exit_action.triggered.connect(self.close)

        view_menu = self.menuBar().addMenu("视图")
        view_menu.addAction("重置相机", self.viewer_3d.reset_camera)
        view_menu.addAction("俯视图", self.viewer_3d.view_top)
        view_menu.addAction("正视图", self.viewer_3d.view_front)
        view_menu.addAction("侧视图", self.viewer_3d.view_side)

        help_menu = self.menuBar().addMenu("帮助")
        help_menu.addAction("关于", self._show_about)

    def _build_top_info_bar(self) -> None:
        self.top_info_bar = QtWidgets.QFrame(self)
        self.top_info_bar.setFrameShape(QtWidgets.QFrame.StyledPanel)

        layout = QtWidgets.QHBoxLayout(self.top_info_bar)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(16)

        self.title_label = QtWidgets.QLabel("血管路径规划 3D 演示")
        self.title_label.setStyleSheet("font-weight: 600;")
        self.data_label = QtWidgets.QLabel("数据: 未加载")
        self.mode_label = QtWidgets.QLabel("模式: 空闲")

        layout.addWidget(self.title_label)
        layout.addStretch(1)
        layout.addWidget(self.data_label)
        layout.addWidget(self.mode_label)

    def _build_central_splitter(self) -> None:
        central = QtWidgets.QWidget(self)
        outer_layout = QtWidgets.QVBoxLayout(central)
        outer_layout.setContentsMargins(6, 6, 6, 6)
        outer_layout.setSpacing(6)
        outer_layout.addWidget(self.top_info_bar)

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, central)
        self.splitter.addWidget(self.viewer_3d)

        # 右侧面板区
        right_scroll = QtWidgets.QScrollArea(self)
        right_scroll.setWidgetResizable(True)
        right_scroll.setMinimumWidth(340)

        right_panel = QtWidgets.QWidget(right_scroll)
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(8)

        right_layout.addWidget(self.control_panel)
        right_layout.addWidget(self.path_info_panel)
        right_layout.addWidget(self.segment_list_panel, stretch=1)

        right_scroll.setWidget(right_panel)
        self.splitter.addWidget(right_scroll)
        self.splitter.setStretchFactor(0, 7)
        self.splitter.setStretchFactor(1, 3)
        self.splitter.setSizes([980, 420])

        outer_layout.addWidget(self.splitter, stretch=1)
        self.setCentralWidget(central)

    def _build_status_bar(self) -> None:
        self.coord_label = QtWidgets.QLabel("坐标: --")
        self.selection_label = QtWidgets.QLabel("选中: --")
        self.statusBar().addPermanentWidget(self.coord_label)
        self.statusBar().addPermanentWidget(self.selection_label)
        self.statusBar().showMessage("就绪")

    # ============================
    #  信号连线
    # ============================

    def _connect_signals(self) -> None:
        # 3D 点选 → 吸附加模式分发
        self.viewer_3d.point_picked.connect(self._on_point_picked)
        self.viewer_3d.pick_missed.connect(self._on_pick_missed)

        # 控制面板 → 选点模式 / 规划 / 清除
        self.control_panel.select_start_requested.connect(self._on_select_start_requested)
        self.control_panel.select_goal_requested.connect(self._on_select_goal_requested)
        self.control_panel.plan_requested.connect(self._on_plan_requested)
        self.control_panel.clear_requested.connect(self._on_clear_requested)

        # 段列表 → 3D 高亮
        self.segment_list_panel.segment_selected.connect(self.viewer_3d.highlight_segment)

    # ============================
    #  数据加载
    # ============================

    def load_default_scene(self) -> None:
        try:
            # 加载图数据（引擎层）
            self.graph_loader.load(self.graph_path)
            self.planner.set_graph(self.graph_loader.graph)
            self.kd_tree.build(self.graph_loader.nodes)

            # 加载 3D 渲染数据
            self.viewer_3d.load_static_scene(
                vessel_path=self.vessel_path,
                centerline_path=self.centerline_path,
            )

            # 刷新段列表
            segments = self.viewer_3d.centerline_renderer.segments
            self.segment_list_panel.set_segments(segments)

            self._refresh_scene_labels()
            self.statusBar().showMessage(
                f"数据加载完成 — 节点 {self.graph_loader.node_count}，"
                f"边 {self.graph_loader.edge_count}"
            )
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "数据加载失败", str(exc))
            self.statusBar().showMessage("数据加载失败")

    def _refresh_scene_labels(self) -> None:
        vessel_mesh = self.viewer_3d.vessel_renderer.mesh
        vessel_points = vessel_mesh.n_points if vessel_mesh is not None else 0
        segment_count = self.viewer_3d.centerline_renderer.segment_count
        self.data_label.setText(
            f"血管点数: {vessel_points} | 中心线段: {segment_count}"
        )
        self.mode_label.setText("模式: 空闲")

    # ============================
    #  选点逻辑
    # ============================

    def _on_select_start_requested(self) -> None:
        self._pick_mode = "start"
        self.viewer_3d.enable_picking(True)
        self.mode_label.setText("模式: 选择起点 — 点击3D模型")
        self.statusBar().showMessage("请在3D模型上点击选择起点")

    def _on_select_goal_requested(self) -> None:
        self._pick_mode = "goal"
        self.viewer_3d.enable_picking(True)
        self.mode_label.setText("模式: 选择终点 — 点击3D模型")
        self.statusBar().showMessage("请在3D模型上点击选择终点")

    def _on_point_picked(self, coords: tuple) -> None:
        if self._pick_mode is None:
            return

        # KDTree 吸附到最近图节点
        try:
            snapped_node, snap_dist = self.kd_tree.find_nearest(coords)
        except RuntimeError:
            self.statusBar().showMessage("KDTree 未就绪")
            return

        # 将点选结果写入控制面板
        self.control_panel.set_pick_result(
            coords=coords,
            snapped_node=snapped_node,
            snap_distance_mm=snap_dist,
        )

        # 在 3D 视图中绘制选点标记球（起点=蓝色，终点=绿色）
        self.viewer_3d.show_pick_marker(snapped_node, self._pick_mode)

        # 更新状态栏
        self.coord_label.setText(
            f"坐标: {snapped_node[0]:.2f}, {snapped_node[1]:.2f}, {snapped_node[2]:.2f}"
        )
        self.selection_label.setText(
            f"吸附距离: {snap_dist:.2f} mm"
        )
        self.statusBar().showMessage(
            f"已选择 {self._pick_mode} — 吸附距离 {snap_dist:.2f} mm"
        )

        # 关闭点选模式
        self.viewer_3d.enable_picking(False)
        self._pick_mode = None
        self.mode_label.setText("模式: 空闲")

    def _on_pick_missed(self, message: str) -> None:
        if self._pick_mode is None:
            return

        self.statusBar().showMessage(message)

    # ============================
    #  规划执行
    # ============================

    def _on_plan_requested(self) -> None:
        start = self.control_panel.start_node
        goal = self.control_panel.goal_node

        if start is None or goal is None:
            QtWidgets.QMessageBox.warning(self, "缺少端点", "请先选择起点和终点。")
            return

        self.statusBar().showMessage("规划中…")
        self.mode_label.setText("模式: 规划中…")
        QtCore.QCoreApplication.processEvents()

        try:
            t0 = time.perf_counter()
            path = self.planner.plan(start, goal)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            if path is None or len(path) < 2:
                QtWidgets.QMessageBox.information(
                    self, "无路径", "无法在图中找到从起点到终点的连通路径。"
                )
                self.statusBar().showMessage("规划失败 — 无连通路径")
                self.mode_label.setText("模式: 空闲")
                return

            # 分析路径
            result = self.analyzer.analyze(path, total_cost=0.0)

            # 渲染路径；起终点 marker 由 PathRenderer 内部根据首尾节点自动放置。
            self.viewer_3d.show_path(
                path,
                feasibility=result.feasibility,
            )

            # 更新信息面板
            self.path_info_panel.update_from_summary(result.summary, elapsed_ms=elapsed_ms)

            # 更新控制面板状态
            self.control_panel.mark_planned()

            self.mode_label.setText("模式: 路径完成")
            self.statusBar().showMessage(
                f"路径长度 {result.total_length_mm:.1f} mm, "
                f"节点 {result.node_count}, "
                f"耗时 {elapsed_ms:.1f} ms, "
                f"可行性 {result.feasibility}"
            )
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "规划失败", str(exc))
            self.statusBar().showMessage(f"规划失败: {exc}")
            self.mode_label.setText("模式: 空闲")

    # ============================
    #  清除逻辑
    # ============================

    def _on_clear_requested(self) -> None:
        self.viewer_3d.clear_path()
        self.viewer_3d.clear_pick_markers()
        self.path_info_panel.clear()
        self.control_panel.clear_all()
        self.coord_label.setText("坐标: --")
        self.selection_label.setText("选中: --")
        self.mode_label.setText("模式: 空闲")
        self.statusBar().showMessage("已清除路径和选点")
        self.viewer_3d.enable_picking(False)
        self._pick_mode = None

    # ============================
    #  辅助
    # ============================

    def _show_about(self) -> None:
        QtWidgets.QMessageBox.information(
            self,
            "关于",
            "血管路径规划 3D 演示\nPython + PyQt5 + PyVista",
        )

    def closeEvent(self, event) -> None:
        self.viewer_3d.enable_picking(False)
        self.viewer_3d.close()
        event.accept()
