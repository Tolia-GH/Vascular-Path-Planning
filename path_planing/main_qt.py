import os
import sys
from typing import Optional

import numpy as np
import pyvista as pv
from PyQt5 import QtCore, QtWidgets
from pyvistaqt import QtInteractor

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from centerline_graph import AStarPathPlanner, CenterlineGraph, PathPlanningResult
from preprocess.BSplineSmoother import smooth_centerline_polydata_bspline


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, centerline_path: Optional[str] = None, vessels_path: Optional[str] = None):
        super().__init__()

        self.setWindowTitle("Vascular Path Planning - Qt")
        self.resize(1380, 920)

        self.main_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.main_widget)

        self.layout = QtWidgets.QVBoxLayout()
        self.plotter = QtInteractor(self.main_widget)
        self.layout.addWidget(self.plotter)
        self.main_widget.setLayout(self.layout)

        self._centerline_poly: Optional[pv.PolyData] = None
        self._vessels_poly: Optional[pv.PolyData] = None
        self._smoothed_centerline_poly: Optional[pv.PolyData] = None
        self._centerline_path: Optional[str] = None
        self._vessels_path: Optional[str] = None

        self._graph: Optional[CenterlineGraph] = None
        self._planner: Optional[AStarPathPlanner] = None
        self._selection_mode: Optional[str] = None
        self._start_node_id: Optional[int] = None
        self._end_node_id: Optional[int] = None
        self._last_picked_node_id: Optional[int] = None
        self._path_result: Optional[PathPlanningResult] = None
        self._path_polyline: Optional[pv.PolyData] = None

        self._vessels_actor = None
        self._vessels_wireframe_actor = None
        self._vessels_points_actor = None
        self._centerline_actor = None
        self._smoothed_actor = None
        self._graph_points_actor = None
        self._start_marker_actor = None
        self._end_marker_actor = None
        self._path_actor = None

        self._build_dock_panel()

        self.plotter.set_background("white")
        self.plotter.add_axes()
        self.statusBar().showMessage("已就绪，加载中心线后可进行起终点选择。")

        self.plotter.enable_point_picking(
            callback=self._on_pick,
            use_picker=True,
            show_message=False,
            show_point=False,
            picker="point",
        )
        self._update_info_overlay()

        if centerline_path:
            self.load_centerline(centerline_path, reset_camera=False)
        if vessels_path:
            self.load_vessels(vessels_path, reset_camera=False)

        self.apply_smoothing(reset_camera=False)
        self.refresh_scene(reset_camera=True)

    def _build_dock_panel(self) -> None:
        dock = QtWidgets.QDockWidget("控制面板", self)
        dock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        dock.setFeatures(QtWidgets.QDockWidget.DockWidgetMovable | QtWidgets.QDockWidget.DockWidgetFloatable)

        panel = QtWidgets.QWidget()
        root = QtWidgets.QVBoxLayout(panel)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(panel)

        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        box_data = QtWidgets.QGroupBox("数据加载")
        data_layout = QtWidgets.QVBoxLayout(box_data)
        self.btn_load_vessels = QtWidgets.QPushButton("上传血管模型")
        self.btn_load_centerline = QtWidgets.QPushButton("上传中心线模型")
        data_layout.addWidget(self.btn_load_vessels)
        data_layout.addWidget(self.btn_load_centerline)
        root.addWidget(box_data)

        box_plan = QtWidgets.QGroupBox("路径规划")
        plan_layout = QtWidgets.QVBoxLayout(box_plan)
        self.btn_select_start = QtWidgets.QPushButton("选择起点")
        self.btn_select_end = QtWidgets.QPushButton("选择终点")
        self.btn_plan = QtWidgets.QPushButton("开始规划")
        self.lbl_start = QtWidgets.QLabel("起点: 未选择")
        self.lbl_end = QtWidgets.QLabel("终点: 未选择")
        self.lbl_pick_tip = QtWidgets.QLabel("拾取方式: 右键点击场景中的中心线节点")
        self.lbl_pick_tip.setWordWrap(True)
        plan_layout.addWidget(self.btn_select_start)
        plan_layout.addWidget(self.btn_select_end)
        plan_layout.addWidget(self.btn_plan)
        plan_layout.addWidget(self.lbl_start)
        plan_layout.addWidget(self.lbl_end)
        plan_layout.addWidget(self.lbl_pick_tip)
        root.addWidget(box_plan)

        box_vis = QtWidgets.QGroupBox("显示控制")
        vis_layout = QtWidgets.QVBoxLayout(box_vis)
        self.chk_show_vessels = QtWidgets.QCheckBox("血管模型")
        self.chk_show_vessels_wireframe = QtWidgets.QCheckBox("血管模型三维网格")
        self.chk_show_vessels_points = QtWidgets.QCheckBox("血管模型点")
        self.chk_show_centerline = QtWidgets.QCheckBox("中心线")
        self.chk_show_smoothed = QtWidgets.QCheckBox("平滑中心线")
        self.chk_show_control_points = QtWidgets.QCheckBox("可选中心线节点")
        self.chk_show_path = QtWidgets.QCheckBox("显示规划路径")
        self.chk_show_vessels.setChecked(True)
        self.chk_show_vessels_wireframe.setChecked(False)
        self.chk_show_vessels_points.setChecked(False)
        self.chk_show_centerline.setChecked(True)
        self.chk_show_smoothed.setChecked(False)
        self.chk_show_control_points.setChecked(True)
        self.chk_show_path.setChecked(True)
        vis_layout.addWidget(self.chk_show_vessels)
        vis_layout.addWidget(self.chk_show_vessels_wireframe)
        vis_layout.addWidget(self.chk_show_vessels_points)
        vis_layout.addWidget(self.chk_show_centerline)
        vis_layout.addWidget(self.chk_show_smoothed)
        vis_layout.addWidget(self.chk_show_control_points)
        vis_layout.addWidget(self.chk_show_path)
        self.slider_vessel_opacity = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_vessel_opacity.setRange(0, 100)
        self.slider_vessel_opacity.setValue(30)
        self.lbl_vessel_opacity = QtWidgets.QLabel("0.30")
        vessel_opacity_layout = QtWidgets.QHBoxLayout()
        vessel_opacity_layout.addWidget(self.slider_vessel_opacity, 1)
        vessel_opacity_layout.addWidget(self.lbl_vessel_opacity)
        vessel_opacity_widget = QtWidgets.QWidget()
        vessel_opacity_widget.setLayout(vessel_opacity_layout)
        vis_layout.addWidget(QtWidgets.QLabel("血管透明度"))
        vis_layout.addWidget(vessel_opacity_widget)
        root.addWidget(box_vis)

        box_result = QtWidgets.QGroupBox("路径信息")
        result_layout = QtWidgets.QFormLayout(box_result)
        self.lbl_path_length = QtWidgets.QLabel("-")
        self.lbl_path_nodes = QtWidgets.QLabel("-")
        self.lbl_path_time = QtWidgets.QLabel("-")
        self.lbl_path_status = QtWidgets.QLabel("等待规划")
        self.lbl_path_status.setWordWrap(True)
        result_layout.addRow("路径总长度", self.lbl_path_length)
        result_layout.addRow("控制节点总数", self.lbl_path_nodes)
        result_layout.addRow("规划耗时", self.lbl_path_time)
        result_layout.addRow("状态", self.lbl_path_status)
        root.addWidget(box_result)

        box_smooth = QtWidgets.QGroupBox("中心线平滑")
        smooth_layout = QtWidgets.QFormLayout(box_smooth)
        self.spin_s_value = QtWidgets.QDoubleSpinBox()
        self.spin_s_value.setDecimals(8)
        self.spin_s_value.setRange(1e-8, 1e3)
        self.spin_s_value.setValue(1e-4)
        self.spin_s_value.setSingleStep(1e-5)
        smooth_layout.addRow("smoothing_factor", self.spin_s_value)

        self.spin_num_samples = QtWidgets.QSpinBox()
        self.spin_num_samples.setRange(20, 5000)
        self.spin_num_samples.setValue(300)
        smooth_layout.addRow("num_samples", self.spin_num_samples)

        self.spin_degree = QtWidgets.QSpinBox()
        self.spin_degree.setRange(1, 5)
        self.spin_degree.setValue(3)
        smooth_layout.addRow("degree", self.spin_degree)

        self.cmb_method = QtWidgets.QComboBox()
        self.cmb_method.addItems(["constrained", "splprep"])
        smooth_layout.addRow("method", self.cmb_method)

        self.chk_enforce_endpoints = QtWidgets.QCheckBox("固定首末端点")
        self.chk_enforce_endpoints.setChecked(True)
        smooth_layout.addRow("enforce_endpoints", self.chk_enforce_endpoints)

        self.spin_n_control = QtWidgets.QSpinBox()
        self.spin_n_control.setRange(0, 500)
        self.spin_n_control.setValue(0)
        self.spin_n_control.setToolTip("0 表示自动")
        smooth_layout.addRow("n_control_points", self.spin_n_control)

        self.spin_tangent_weight = QtWidgets.QDoubleSpinBox()
        self.spin_tangent_weight.setRange(-1.0, 100000.0)
        self.spin_tangent_weight.setDecimals(4)
        self.spin_tangent_weight.setValue(-1.0)
        self.spin_tangent_weight.setToolTip("-1 表示自动")
        smooth_layout.addRow("tangent_weight", self.spin_tangent_weight)

        self.spin_curvature_weight = QtWidgets.QDoubleSpinBox()
        self.spin_curvature_weight.setRange(-1.0, 100000.0)
        self.spin_curvature_weight.setDecimals(4)
        self.spin_curvature_weight.setValue(-1.0)
        self.spin_curvature_weight.setToolTip("-1 表示自动")
        smooth_layout.addRow("curvature_weight", self.spin_curvature_weight)

        self.btn_apply_smooth = QtWidgets.QPushButton("应用平滑")
        smooth_layout.addRow(self.btn_apply_smooth)
        root.addWidget(box_smooth)

        box_debug = QtWidgets.QGroupBox("拓扑信息")
        debug_layout = QtWidgets.QFormLayout(box_debug)
        self.lbl_nodes = QtWidgets.QLabel("0")
        self.lbl_edges = QtWidgets.QLabel("0")
        self.lbl_components = QtWidgets.QLabel("0")
        self.lbl_point = QtWidgets.QLabel("-")
        self.lbl_point.setWordWrap(True)
        debug_layout.addRow("节点数", self.lbl_nodes)
        debug_layout.addRow("边数", self.lbl_edges)
        debug_layout.addRow("连通分量数", self.lbl_components)
        debug_layout.addRow("最近拾取节点", self.lbl_point)
        root.addWidget(box_debug)
        root.addStretch(1)

        dock.setWidget(scroll)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock)

        self.btn_load_vessels.clicked.connect(self._on_upload_vessels)
        self.btn_load_centerline.clicked.connect(self._on_upload_centerline)
        self.btn_select_start.clicked.connect(lambda: self._set_selection_mode("start"))
        self.btn_select_end.clicked.connect(lambda: self._set_selection_mode("end"))
        self.btn_plan.clicked.connect(self._plan_path)
        self.chk_show_vessels.toggled.connect(lambda _: self.refresh_scene(reset_camera=False))
        self.chk_show_vessels_wireframe.toggled.connect(lambda _: self.refresh_scene(reset_camera=False))
        self.chk_show_vessels_points.toggled.connect(lambda _: self.refresh_scene(reset_camera=False))
        self.chk_show_centerline.toggled.connect(lambda _: self.refresh_scene(reset_camera=False))
        self.chk_show_smoothed.toggled.connect(lambda _: self.refresh_scene(reset_camera=False))
        self.chk_show_control_points.toggled.connect(lambda _: self.refresh_scene(reset_camera=False))
        self.chk_show_path.toggled.connect(lambda _: self.refresh_scene(reset_camera=False))
        self.slider_vessel_opacity.valueChanged.connect(self._on_vessel_opacity_changed)
        self.btn_apply_smooth.clicked.connect(lambda: self.apply_smoothing(reset_camera=False))

        self._on_vessel_opacity_changed(self.slider_vessel_opacity.value())
        self._set_result_status("等待规划", error=False)

    def _on_vessel_opacity_changed(self, val: int) -> None:
        opacity = max(0.0, min(1.0, val / 100.0))
        self.lbl_vessel_opacity.setText(f"{opacity:.2f}")
        self.refresh_scene(reset_camera=False)

    def _current_smoothing_params(self) -> dict:
        s_val = float(self.spin_s_value.value())
        n_control = self.spin_n_control.value()
        t_weight = self.spin_tangent_weight.value()
        c_weight = self.spin_curvature_weight.value()
        return {
            "smoothing_factor": s_val,
            "degree": int(self.spin_degree.value()),
            "num_samples": int(self.spin_num_samples.value()),
            "enforce_endpoints": bool(self.chk_enforce_endpoints.isChecked()),
            "method": str(self.cmb_method.currentText()),
            "n_control_points": None if n_control <= 0 else int(n_control),
            "tangent_weight": None if t_weight < 0 else float(t_weight),
            "curvature_weight": None if c_weight < 0 else float(c_weight),
        }

    def _read_polydata_file(self, path: str) -> pv.PolyData:
        data = pv.read(path)
        if not isinstance(data, pv.PolyData) and hasattr(data, "extract_geometry"):
            data = data.extract_geometry()
        if not isinstance(data, pv.PolyData):
            raise TypeError("读取结果不是 PolyData，无法显示。")
        return data

    def load_centerline(self, path: str, reset_camera: bool = True) -> None:
        poly = self._read_polydata_file(path)
        if poly.n_points <= 0:
            raise ValueError("中心线模型不包含有效点。")
        self._centerline_poly = poly
        self._centerline_path = path
        self._rebuild_graph()
        self.apply_smoothing(reset_camera=False)
        self.refresh_scene(reset_camera=reset_camera)

    def load_vessels(self, path: str, reset_camera: bool = True) -> None:
        poly = self._read_polydata_file(path)
        if poly.n_points <= 0:
            raise ValueError("血管模型不包含有效点。")
        self._vessels_poly = poly
        self._vessels_path = path
        self.refresh_scene(reset_camera=reset_camera)

    def _rebuild_graph(self) -> None:
        if self._centerline_poly is None:
            self._graph = None
            self._planner = None
            return
        self._graph = CenterlineGraph.from_polydata(self._centerline_poly, merge_tolerance=1e-3)
        self._planner = AStarPathPlanner(self._graph)
        self._start_node_id = None
        self._end_node_id = None
        self._last_picked_node_id = None
        self._clear_path_result()
        self._update_selected_labels()
        self._update_debug_info()
        self._update_status_bar()

    def _on_upload_centerline(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "选择中心线模型",
            self._centerline_path or os.path.abspath(os.path.join("..", "source", "vtk")),
            "VTK/VTU/VTP Files (*.vtk *.vtp *.vtu);;All Files (*)",
        )
        if not path:
            return
        try:
            self.load_centerline(path, reset_camera=True)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "加载失败", f"中心线加载失败：{exc}")

    def _on_upload_vessels(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "选择血管模型",
            self._vessels_path or os.path.abspath(os.path.join("..", "source", "vtk")),
            "VTK/VTU/VTP Files (*.vtk *.vtp *.vtu);;All Files (*)",
        )
        if not path:
            return
        try:
            self.load_vessels(path, reset_camera=True)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "加载失败", f"血管模型加载失败：{exc}")

    def apply_smoothing(self, reset_camera: bool = False) -> None:
        if self._centerline_poly is None:
            self._smoothed_centerline_poly = None
            self.refresh_scene(reset_camera=reset_camera)
            return
        try:
            self._smoothed_centerline_poly = smooth_centerline_polydata_bspline(
                self._centerline_poly,
                **self._current_smoothing_params(),
            )
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "平滑失败", f"中心线平滑失败：{exc}")
            return
        self.refresh_scene(reset_camera=reset_camera)

    def _remove_actor(self, actor) -> None:
        if actor is not None:
            self.plotter.remove_actor(actor, reset_camera=False)

    def _build_polyline(self, coordinates) -> pv.PolyData:
        points = np.asarray(coordinates, dtype=float)
        polyline = pv.PolyData()
        polyline.points = points
        polyline.lines = np.hstack([[len(points)], np.arange(len(points), dtype=np.int64)])
        return polyline

    def _build_marker(self, node_id: Optional[int]) -> Optional[pv.PolyData]:
        if self._graph is None or node_id is None:
            return None
        center = self._graph.get_node(node_id).coord
        return pv.Sphere(radius=1.5, center=center)

    def refresh_scene(self, reset_camera: bool = False) -> None:
        self._remove_actor(self._vessels_actor)
        self._remove_actor(self._vessels_wireframe_actor)
        self._remove_actor(self._vessels_points_actor)
        self._remove_actor(self._centerline_actor)
        self._remove_actor(self._smoothed_actor)
        self._remove_actor(self._graph_points_actor)
        self._remove_actor(self._start_marker_actor)
        self._remove_actor(self._end_marker_actor)
        self._remove_actor(self._path_actor)

        self._vessels_actor = None
        self._vessels_wireframe_actor = None
        self._vessels_points_actor = None
        self._centerline_actor = None
        self._smoothed_actor = None
        self._graph_points_actor = None
        self._start_marker_actor = None
        self._end_marker_actor = None
        self._path_actor = None

        if self._vessels_poly is not None and self.chk_show_vessels.isChecked():
            self._vessels_actor = self.plotter.add_mesh(
                self._vessels_poly,
                color="red",
                opacity=max(0.0, min(1.0, self.slider_vessel_opacity.value() / 100.0)),
                pickable=False,
                reset_camera=False,
            )

        if self._vessels_poly is not None and self.chk_show_vessels_wireframe.isChecked():
            self._vessels_wireframe_actor = self.plotter.add_mesh(
                self._vessels_poly,
                style="wireframe",
                line_width=1,
                color="black",
                pickable=False,
                reset_camera=False,
            )

        if self._vessels_poly is not None and self.chk_show_vessels_points.isChecked():
            self._vessels_points_actor = self.plotter.add_mesh(
                self._vessels_poly.points,
                color="red",
                point_size=4,
                render_points_as_spheres=True,
                pickable=False,
                reset_camera=False,
            )

        if self._centerline_poly is not None and self.chk_show_centerline.isChecked():
            self._centerline_actor = self.plotter.add_mesh(
                self._centerline_poly,
                color="black",
                line_width=2,
                render_lines_as_tubes=True,
                pickable=False,
                reset_camera=False,
            )

        if self._smoothed_centerline_poly is not None and self.chk_show_smoothed.isChecked():
            self._smoothed_actor = self.plotter.add_mesh(
                self._smoothed_centerline_poly,
                color="blue",
                line_width=2,
                render_lines_as_tubes=True,
                pickable=False,
                reset_camera=False,
            )

        if self._graph is not None and self.chk_show_control_points.isChecked():
            self._graph_points_actor = self.plotter.add_mesh(
                self._graph.coordinates,
                color="darkred",
                point_size=4,
                render_points_as_spheres=True,
                pickable=True,
                reset_camera=False,
            )

        start_marker = self._build_marker(self._start_node_id)
        if start_marker is not None:
            self._start_marker_actor = self.plotter.add_mesh(
                start_marker,
                color="red",
                smooth_shading=True,
                pickable=False,
                reset_camera=False,
            )

        end_marker = self._build_marker(self._end_node_id)
        if end_marker is not None:
            self._end_marker_actor = self.plotter.add_mesh(
                end_marker,
                color="blue",
                smooth_shading=True,
                pickable=False,
                reset_camera=False,
            )

        if self._path_polyline is not None and self.chk_show_path.isChecked():
            path_tube = self._path_polyline.tube(radius=1)
            self._path_actor = self.plotter.add_mesh(
                path_tube,
                color="blue",
                opacity=1.0,
                pickable=False,
                reset_camera=False,
            )

        self._update_debug_info()
        self._update_info_overlay()
        if reset_camera:
            self.plotter.reset_camera()
        self.plotter.render()

    def _set_selection_mode(self, mode: str) -> None:
        if self._graph is None:
            QtWidgets.QMessageBox.warning(self, "无法选择", "请先加载有效的中心线模型。")
            return
        self._selection_mode = mode
        role_name = "起点" if mode == "start" else "终点"
        self._update_status_bar(f"请在场景中右键点击中心线节点，设置{role_name}。")
        self._update_info_overlay()

    def _set_result_status(self, text: str, error: bool) -> None:
        color = "#c62828" if error else "#1b5e20"
        self.lbl_path_status.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.lbl_path_status.setText(text)

    def _clear_path_result(self) -> None:
        self._path_result = None
        self._path_polyline = None
        self.lbl_path_length.setText("-")
        self.lbl_path_nodes.setText("-")
        self.lbl_path_time.setText("-")
        self._set_result_status("等待规划", error=False)

    def _update_result_panel(self, result: PathPlanningResult) -> None:
        self._path_result = result
        if not result.reachable:
            self._path_polyline = None
            self.lbl_path_length.setText("-")
            self.lbl_path_nodes.setText("-")
            self.lbl_path_time.setText(f"{result.elapsed_ms:.3f} ms")
            self._set_result_status(result.error_message or "规划失败", error=True)
            return

        self.lbl_path_length.setText(f"{result.total_length:.3f}")
        self.lbl_path_nodes.setText(str(result.control_node_count))
        self.lbl_path_time.setText(f"{result.elapsed_ms:.3f} ms")
        self._set_result_status("规划成功", error=False)
        self._path_polyline = self._build_polyline(result.path_coordinates)

    def _plan_path(self) -> None:
        if self._planner is None or self._graph is None:
            QtWidgets.QMessageBox.warning(self, "无法规划", "请先加载并解析中心线模型。")
            return
        if self._start_node_id is None or self._end_node_id is None:
            QtWidgets.QMessageBox.warning(self, "无法规划", "请先完成起点和终点选择。")
            return

        result = self._planner.plan(self._start_node_id, self._end_node_id)
        self._update_result_panel(result)
        self.refresh_scene(reset_camera=False)
        if result.reachable:
            self._update_status_bar(
                f"规划完成: 长度 {result.total_length:.3f}, 节点 {result.control_node_count}, 耗时 {result.elapsed_ms:.3f} ms"
            )
        else:
            self._update_status_bar(result.error_message or "规划失败，请重新选择。")

    def _update_selected_labels(self) -> None:
        if self._graph is None or self._start_node_id is None:
            self.lbl_start.setText("起点: 未选择")
        else:
            coord = self._graph.get_node(self._start_node_id).coord
            self.lbl_start.setText(
                f"起点: ID={self._start_node_id} ({coord[0]:.3f}, {coord[1]:.3f}, {coord[2]:.3f})"
            )

        if self._graph is None or self._end_node_id is None:
            self.lbl_end.setText("终点: 未选择")
        else:
            coord = self._graph.get_node(self._end_node_id).coord
            self.lbl_end.setText(
                f"终点: ID={self._end_node_id} ({coord[0]:.3f}, {coord[1]:.3f}, {coord[2]:.3f})"
            )

    def _format_node_status(self, prefix: str, node_id: Optional[int]) -> str:
        if self._graph is None or node_id is None:
            return f"{prefix}: 未选择"
        coord = self._graph.get_node(node_id).coord
        return f"{prefix}: ID={node_id} ({coord[0]:.3f}, {coord[1]:.3f}, {coord[2]:.3f})"

    def _update_status_bar(self, suffix: Optional[str] = None) -> None:
        current_info = self._format_node_status("起点", self._start_node_id)
        current_info += " | "
        current_info += self._format_node_status("终点", self._end_node_id)
        if suffix:
            current_info += f" | {suffix}"
        self.statusBar().showMessage(current_info)

    def _update_debug_info(self) -> None:
        if self._graph is None:
            self.lbl_nodes.setText("0")
            self.lbl_edges.setText("0")
            self.lbl_components.setText("0")
            if self._last_picked_node_id is None:
                self.lbl_point.setText("-")
            return

        self.lbl_nodes.setText(str(self._graph.node_count))
        self.lbl_edges.setText(str(self._graph.edge_count))
        self.lbl_components.setText(str(self._graph.component_count))
        if self._last_picked_node_id is None:
            self.lbl_point.setText("-")
            return
        coord = self._graph.get_node(self._last_picked_node_id).coord
        self.lbl_point.setText(
            f"ID={self._last_picked_node_id} ({coord[0]:.3f}, {coord[1]:.3f}, {coord[2]:.3f})"
        )

    def _update_info_overlay(self) -> None:
        lines = ["右键点击中心线节点查看或选择最近有效节点"]
        if self._selection_mode == "start":
            lines.append("当前模式: 选择起点")
        elif self._selection_mode == "end":
            lines.append("当前模式: 选择终点")
        else:
            lines.append("当前模式: 浏览")
        self.plotter.remove_actor("info")
        self.plotter.add_text("\n".join(lines), font_size=10, name="info")

    def _on_pick(self, point, picker) -> None:
        if point is None or self._graph is None:
            return

        node_id, distance = self._graph.nearest_node(tuple(point))
        self._last_picked_node_id = node_id
        coord = self._graph.get_node(node_id).coord
        self.lbl_point.setText(f"ID={node_id} ({coord[0]:.3f}, {coord[1]:.3f}, {coord[2]:.3f})")

        if self._selection_mode == "start":
            self._start_node_id = node_id
            self._selection_mode = None
            self._clear_path_result()
        elif self._selection_mode == "end":
            self._end_node_id = node_id
            self._selection_mode = None
            self._clear_path_result()

        self._update_selected_labels()
        self._update_status_bar(
            f"最近节点 ID={node_id}, 坐标=({coord[0]:.3f}, {coord[1]:.3f}, {coord[2]:.3f}), 拾取偏差={distance:.3f}"
        )
        self._update_info_overlay()
        self.refresh_scene(reset_camera=False)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    default_centerline = "../source/vtk/Centerline_curves_merged.vtk"
    default_vessels = "../source/vtk/blood vessels.vtk"
    if not os.path.exists(default_vessels):
        default_vessels = "../source/vtk/blood_vessels.vtk"

    window = MainWindow(default_centerline, default_vessels if os.path.exists(default_vessels) else None)
    window.show()

    sys.exit(app.exec_())
