import os
import sys
from typing import Optional

from PyQt5 import QtCore, QtWidgets
from pyvistaqt import QtInteractor
import pyvista as pv

from preprocess.BSplineSmoother import smooth_centerline_polydata_bspline


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, centerline_path: Optional[str] = None, vessels_path: Optional[str] = None):
        super().__init__()

        self.setWindowTitle("Vascular Path Planning - Qt")
        self.resize(1280, 900)

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

        # 显示对象初始化
        self._vessels_actor = None
        self._vessels_wireframe_actor = None
        self._vessels_points_actor = None
        self._centerline_actor = None
        self._smoothed_actor = None
        self._picked_points_actor = None

        self._build_dock_panel()

        self.plotter.set_background("white")
        self.plotter.add_axes()

        # 允许选点
        self.plotter.add_text("右键拾取点查看坐标", font_size=10, name="info")
        self.plotter.enable_point_picking(
            callback=self._on_pick,
            use_picker=True,
            show_message=False,
            show_point=True,
            picker="point",
        )

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
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # 数据加载
        box_data = QtWidgets.QGroupBox("数据加载")
        data_layout = QtWidgets.QVBoxLayout(box_data)
        self.btn_load_vessels = QtWidgets.QPushButton("上传血管模型")
        self.btn_load_centerline = QtWidgets.QPushButton("上传中心线模型")
        data_layout.addWidget(self.btn_load_vessels)
        data_layout.addWidget(self.btn_load_centerline)
        root.addWidget(box_data)

        # 对象显示控制
        box_vis = QtWidgets.QGroupBox("显示控制")
        vis_layout = QtWidgets.QVBoxLayout(box_vis)
        self.chk_show_vessels = QtWidgets.QCheckBox("血管模型")
        self.chk_show_vessels_wireframe = QtWidgets.QCheckBox("血管模型三维网格")
        self.chk_show_vessels_points = QtWidgets.QCheckBox("血管模型点")
        self.chk_show_centerline = QtWidgets.QCheckBox("中心线")
        self.chk_show_smoothed = QtWidgets.QCheckBox("平滑中心线")
        self.chk_show_control_points = QtWidgets.QCheckBox("控制点")
        self.chk_show_vessels.setChecked(True)
        self.chk_show_vessels_wireframe.setChecked(True)
        self.chk_show_vessels_points.setChecked(True)
        self.chk_show_centerline.setChecked(True)
        self.chk_show_smoothed.setChecked(True)
        self.chk_show_control_points.setChecked(True)
        vis_layout.addWidget(self.chk_show_vessels)
        vis_layout.addWidget(self.chk_show_vessels_wireframe)
        vis_layout.addWidget(self.chk_show_vessels_points)
        vis_layout.addWidget(self.chk_show_centerline)
        vis_layout.addWidget(self.chk_show_smoothed)
        vis_layout.addWidget(self.chk_show_control_points)
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

        # 中心线平滑参数设置
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

        # 调试信息
        box_debug = QtWidgets.QGroupBox("调试信息")
        debug_layout = QtWidgets.QFormLayout(box_debug)
        self.lbl_nodes = QtWidgets.QLabel("0")
        self.lbl_edges = QtWidgets.QLabel("0")
        self.lbl_point = QtWidgets.QLabel("-")
        debug_layout.addRow("节点数", self.lbl_nodes)
        debug_layout.addRow("边数", self.lbl_edges)
        debug_layout.addRow("选中点坐标", self.lbl_point)
        root.addWidget(box_debug)
        root.addStretch(1)

        dock.setWidget(panel)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock)

        # 组件绑定事件刷新
        self.btn_load_vessels.clicked.connect(self._on_upload_vessels)
        self.btn_load_centerline.clicked.connect(self._on_upload_centerline)
        self.chk_show_vessels.toggled.connect(lambda _: self.refresh_scene(reset_camera=False))
        self.chk_show_vessels_wireframe.toggled.connect(lambda _: self.refresh_scene(reset_camera=False))
        self.chk_show_vessels_points.toggled.connect(lambda _: self.refresh_scene(reset_camera=False))
        self.chk_show_centerline.toggled.connect(lambda _: self.refresh_scene(reset_camera=False))
        self.chk_show_smoothed.toggled.connect(lambda _: self.refresh_scene(reset_camera=False))
        self.chk_show_control_points.toggled.connect(lambda _: self.refresh_scene(reset_camera=False))
        self.slider_vessel_opacity.valueChanged.connect(self._on_vessel_opacity_changed)
        self.btn_apply_smooth.clicked.connect(lambda: self.apply_smoothing(reset_camera=False))

        self._on_vessel_opacity_changed(self.slider_vessel_opacity.value())

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
        if not isinstance(data, pv.PolyData):
            if hasattr(data, "extract_geometry"):
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
        self.apply_smoothing(reset_camera=False)
        self.refresh_scene(reset_camera=reset_camera)

    def load_vessels(self, path: str, reset_camera: bool = True) -> None:
        poly = self._read_polydata_file(path)
        if poly.n_points <= 0:
            raise ValueError("血管模型不包含有效点。")
        self._vessels_poly = poly
        self._vessels_path = path
        self.refresh_scene(reset_camera=reset_camera)

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
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "加载失败", f"中心线加载失败：{e}")

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
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "加载失败", f"血管模型加载失败：{e}")

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
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "平滑失败", f"中心线平滑失败：{e}")
            return
        self.refresh_scene(reset_camera=reset_camera)

    def _remove_actor(self, actor) -> None:
        if actor is not None:
            self.plotter.remove_actor(actor, reset_camera=False)

    def refresh_scene(self, reset_camera: bool = False) -> None:
        self._remove_actor(self._vessels_actor)
        self._remove_actor(self._vessels_wireframe_actor)
        self._remove_actor(self._vessels_points_actor)
        self._remove_actor(self._centerline_actor)
        self._remove_actor(self._smoothed_actor)
        self._remove_actor(self._picked_points_actor)

        self._vessels_actor = None
        self._vessels_wireframe_actor = None
        self._vessels_points_actor = None
        self._centerline_actor = None
        self._smoothed_actor = None
        self._picked_points_actor = None

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
                color="black",
                pickable=False,
                reset_camera=False,
            )

        if self._vessels_poly is not None and self.chk_show_vessels_points.isChecked():
            self._vessels_points_actor = self.plotter.add_mesh(
                self._vessels_poly.points,
                color="red",
                render_points_as_spheres=True,
                pickable=True,
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

        if self._centerline_poly is not None and self.chk_show_control_points.isChecked():
            self._picked_points_actor = self.plotter.add_mesh(
                self._centerline_poly.points,
                color="red",
                point_size=6,
                render_points_as_spheres=True,
                pickable=True,
                reset_camera=False,
            )

        self._update_debug_info()
        if reset_camera:
            self.plotter.reset_camera()
        self.plotter.render()

    def _update_debug_info(self) -> None:
        if self._centerline_poly is None:
            self.lbl_nodes.setText("0")
            self.lbl_edges.setText("0")
            return
        self.lbl_nodes.setText(str(int(self._centerline_poly.n_points)))
        self.lbl_edges.setText(str(int(self._centerline_poly.n_lines)))

    def _on_pick(self, point, picker) -> None:
        if point is None:
            return
        self.plotter.remove_actor("info")
        self.plotter.add_text(f"x: {point[0]:.3f}, y: {point[1]:.3f}, z: {point[2]:.3f}", font_size=10, name="info")
        self.lbl_point.setText(f"({point[0]:.3f}, {point[1]:.3f}, {point[2]:.3f})")

if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)

    default_centerline = "../source/vtk/Centerline_curves_merged.vtk"
    default_vessels = "../source/vtk/blood vessels.vtk"
    if not os.path.exists(default_vessels):
        default_vessels = "../source/vtk/blood_vessels.vtk"

    window = MainWindow(default_centerline, default_vessels if os.path.exists(default_vessels) else None)
    window.show()

    sys.exit(app.exec_())
