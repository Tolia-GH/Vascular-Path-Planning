import matplotlib.pyplot as plt
import mplcursors
import pyvista as pv
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
import os
import sys

from pyvistaqt import QtInteractor
from PyQt5 import QtWidgets, QtCore

def visualization(vessel_net, path=None):
    """
    可视化三维血管网络和路径
    vessel_net: 加权邻接表，表示血管网络
    path: 可选，表示A*算法计算的路径（一个由节点组成的列表）
    """
    # 创建一个3D图形
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # 用于存储所有节点的坐标
    nodes = list(vessel_net.keys())

    # 存储节点的散点图
    scatters = []


    # 绘制节点
    for node in nodes:
        scatter = ax.scatter(node[0], node[1], node[2], color='k', marker='.', s=30)  # 绘制节点
        scatters.append(scatter)

    # 绘制边（血管段）
    for node, neighbors in vessel_net.items():
        for neighbor, weight in neighbors:
            ax.plot(
                [node[0], neighbor[0]],
                [node[1], neighbor[1]],
                [node[2], neighbor[2]],
                color='k', linewidth=1)  # 绘制连接的边（绿色）

        # 如果路径存在，绘制路径
    if path:
        # 提取路径中的节点坐标
        path_nodes = [vessel_net[node] for node in path]
        x_path = [node[0] for node in path]
        y_path = [node[1] for node in path]
        z_path = [node[2] for node in path]
        ax.plot(x_path, y_path, z_path,
                color='r', linewidth=3)  # 绘制路径（红色）

        # 标记起点
        start = path[0]
        ax.scatter(
            start[0], start[1], start[2],
            color='b', s=60, marker='.', label='起点'
        )
        ax.text(
            start[0], start[1], start[2],
            'S', fontsize=12, verticalalignment='bottom'
        )

        # 标记终点
        end = path[-1]
        ax.scatter(
            end[0], end[1], end[2],
            color='b', s=60, marker='*', label='终点'
        )
        ax.text(
            end[0], end[1], end[2],
            'E', fontsize=12, verticalalignment='bottom'
        )

    # 设置坐标轴标签ppython
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')

    # 使用 mplcursors 添加交互功能
    cursor = mplcursors.cursor(scatters, hover=True)

    # 鼠标悬停显示坐标
    cursor.connect(
        "add",
        lambda sel: sel.annotation.set_text(f'({sel.artist._offsets3d[0][sel.index]}, '
                                            f'{sel.artist._offsets3d[1][sel.index]}, '
                                            f'{sel.artist._offsets3d[2][sel.index]})')
    )

    # 显示图形
    plt.show()


def visualization_pyvista(vessel_net, path=None):
    """
    可视化三维血管网络和路径（基于pyvista，对vtk兼容性更好）
    :param vessel_net: 加权邻接表，表示血管网络
    :param path: 可选，表示A*算法计算的路径（一个由节点组成的列表）
    """
    plotter = pv.Plotter()

    # 所有节点的坐标列表
    nodes = np.array(list(vessel_net.keys()))

    # 将节点作为点云添加
    point_cloud = pv.PolyData(nodes)
    plotter.add_mesh(point_cloud, color='black', point_size=10, render_points_as_spheres=True)

    # 绘制边
    for node, neighbors in vessel_net.items():
        for neighbor, weight in neighbors:
            line = pv.Line(node, neighbor)
            plotter.add_mesh(line, color='black', line_width=1)

    # 绘制路径（如果存在）
    if path:
        # 根据路径绘制平滑样条曲线
        # path_points = np.array(path)
        # path_line = pv.Spline(path_points, len(path_points) * 10)
        # plotter.add_mesh(path_line, color='red', line_width=3)

        # 根据路径绘制折线
        path_points = np.array(path)
        path_line = pv.PolyData()
        path_line.points = path_points
        cells = np.hstack([[len(path_points)], np.arange(len(path_points))])
        path_line.lines = cells
        plotter.add_mesh(path_line, color='red', line_width=3)

        # 起点
        plotter.add_points(np.array(path[0]), color='blue', point_size=15, render_points_as_spheres=True)

        # 终点
        plotter.add_points(np.array(path[-1]), color='green', point_size=15, render_points_as_spheres=True)

    plotter.show_axes()
    plotter.show_grid(
        xtitle='X',
        ytitle='Y',
        ztitle='Z',
        color='grey',
        grid='back',  # 显示哪些平面网格：可选 'front', 'back', 'all', 'none'
        location='outer',  # 坐标轴位置，可选 'outer'（默认）或 'all'
        bold=True,  # 粗体文字
        font_size=10,  # 坐标刻度字体大小
    )

    plotter.show()


def visualize_centerline(centerline_path):
    """
    中心线vtk文件的模型可视化
    :param centerline_path: vtk文件路径
    """
    centerline = pv.read(centerline_path)

    # print(centerline)

    # print(centerline.lines)
    # print(centerline.points)
    # print(centerline.cell)

    plotter = pv.Plotter()

    # 导入中心线段
    plotter.add_mesh(centerline, color='black', line_width=2, render_points_as_spheres=True)

    splited_centerlines = split_polydata_lines(centerline.lines)



    # for i in range(0,103):
    #     print(centerline.points[i])
    #     plotter.add_mesh(centerline.points[i], color='red', line_width=1, render_points_as_spheres=True)
    #
    # for i in range(103,512):
    #     print(centerline.points[i])
    #     plotter.add_mesh(centerline.points[i], color='green', line_width=1, render_points_as_spheres=True)

    plotter.add_mesh(centerline.points, color='blue', line_width=1, render_points_as_spheres=True, pickable=True)

    # 回调函数（点击时触发）
    def callback(point, picker):
        if point is None:
            return

        print(point)


    # 启用点拾取
    plotter.enable_point_picking(
        callback=callback,
        use_picker=True,
        show_message=True,
        show_point=True,
        picker='point'
    )

    plotter.show()

def split_polydata_lines(lines):
    """
    将中心线vtk的PolyData.lines的一维数组根据压缩结构划分为多维线段数组
    :param lines:
    :return: splited_lines: Array数组，每个元素为一个列出线段上的所有点索引的数组
    """
    splited_lines = []
    line_length = lines[0]
    left_edge = 1
    right_edge = left_edge + line_length - 1
    line = []
    for i in range(1, len(lines)):

        if left_edge <= i <= right_edge:
            line.append(lines[i])

        if i == len(lines) - 1:
            splited_lines.append(line)
            break

        if i == right_edge:

            splited_lines.append(line)
            line_length = lines[right_edge+1]
            left_edge = right_edge + 2
            right_edge = left_edge + line_length - 1
            line = []

    return splited_lines

def build_polyline_from_points(points: np.ndarray) -> pv.PolyData:
    poly = pv.PolyData()
    poly.points = np.asarray(points)
    n = poly.n_points
    poly.lines = np.hstack([[n], np.arange(n, dtype=np.int64)])
    return poly


def build_splitted_centerline(centerline: pv.PolyData):
    splitted_centerline = split_polydata_lines(centerline.lines)
    segments = []
    for ids in splitted_centerline:
        ids_arr = np.asarray(ids, dtype=np.int64)
        segment_points = centerline.points[ids_arr]
        segments.append(build_polyline_from_points(segment_points))
    return splitted_centerline, segments


def visualize_centerline_qt(centerline_path: str):

    class CenterlineViewer(QtWidgets.QMainWindow):
        def __init__(self, vtk_path: str):
            super().__init__()
            self._selected_index = None
            self._actors = []

            self.setWindowTitle("Centerline Viewer")

            splitter = QtWidgets.QSplitter()
            orientation = getattr(QtCore.Qt, "Orientation", QtCore.Qt)
            splitter.setOrientation(orientation.Horizontal)

            self.plotter = QtInteractor(splitter)
            self.segment_list = QtWidgets.QListWidget(splitter)

            splitter.setStretchFactor(0, 4)
            splitter.setStretchFactor(1, 1)
            self.setCentralWidget(splitter)

            vtk_path = os.path.abspath(vtk_path)
            centerline = pv.read(vtk_path)
            self.splitted_centerline, self._segments = build_splitted_centerline(centerline)

            self.plotter.set_background("white")
            self.plotter.add_axes()
            self._actors = [
                self.plotter.add_mesh(seg, color="black", line_width=2)
                for seg in self._segments
            ]
            self.plotter.reset_camera()

            for i, ids in enumerate(self.splitted_centerline):
                self.segment_list.addItem(f"segment_{i} (points={len(ids)})")

            self.segment_list.currentRowChanged.connect(self._on_row_changed)
            if self.segment_list.count() > 0:
                self.segment_list.setCurrentRow(0)

        def _set_actor_color(self, actor, rgb):
            actor.GetProperty().SetColor(float(rgb[0]), float(rgb[1]), float(rgb[2]))

        def _on_row_changed(self, row: int):
            if row < 0 or row >= len(self._actors):
                return

            if self._selected_index is not None and 0 <= self._selected_index < len(self._actors):
                self._set_actor_color(self._actors[self._selected_index], (0.0, 0.0, 0.0))

            self._set_actor_color(self._actors[row], (1.0, 0.0, 0.0))
            self._selected_index = row
            self.plotter.render()

        def closeEvent(self, event):
            try:
                self.plotter.close()
            finally:
                event.accept()

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    viewer = CenterlineViewer(centerline_path)
    viewer.resize(1200, 800)
    viewer.show()
    return app.exec()

