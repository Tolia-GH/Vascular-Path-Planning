import sys
from PyQt5 import QtWidgets
from pyvistaqt import QtInteractor
import pyvista as pv

from path_planing.visualize import split_polydata_lines
from preprocess.BSplineSmoother import smooth_centerline_polydata_bspline


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, centerline_path, vessels_path):
        super().__init__()

        self.setWindowTitle("Centerline Viewer")
        self.resize(1000, 800)

        # ========= 主Widget =========
        self.main_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.main_widget)

        # ========= 布局 =========
        self.layout = QtWidgets.QVBoxLayout()

        # ========= 渲染窗口 =========
        self.plotter = QtInteractor(self.main_widget)

        # 添加到布局
        self.layout.addWidget(self.plotter)


        self.main_widget.setLayout(self.layout)

        # ========= 渲染模型 =========
        centerline = pv.read(centerline_path)
        vessels = pv.read(vessels_path)

        self.plotter.add_text("Right click to pick a point", font_size=10, name="info")
        # self.plotter.add_mesh(centerline, color='black', line_width=2, render_points_as_spheres=True, pickable=False)
        self.plotter.add_mesh(vessels, color='red', opacity=0.3, pickable=False)

        splited_centerlines = split_polydata_lines(centerline.lines)
        smoothed_centerlines = smooth_centerline_polydata_bspline(centerline)

        self.plotter.add_mesh(smoothed_centerlines, color='black', line_width=2, render_points_as_spheres=True, pickable=False)
        self.plotter.add_mesh(centerline.points, color='red', line_width=1, render_points_as_spheres=True, pickable=True)

        # 回调函数（点击时触发）
        def on_pick(point, picker):
            if point is None:
                return

            # 删除旧文本
            self.plotter.remove_actor("info")

            # 添加新文本
            self.plotter.add_text(
                f"x: {point[0]:.3f}, y: {point[1]:.3f}, z: {point[2]:.3f}", font_size=10, name="info"
            )

            # print(point)

        # 启用点拾取
        self.plotter.enable_point_picking(
            callback=on_pick,
            use_picker=True,
            show_message=False,
            show_point=True,
            picker='point'
        )

        self.plotter.reset_camera()


if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)

    window = MainWindow("../source/vtk/Centerline_curves_merged.vtk", "../source/vtk/blood_vessels.vtk")
    window.show()

    sys.exit(app.exec_())