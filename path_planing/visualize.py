import matplotlib.pyplot as plt
import mplcursors
import pyvista as pv
import numpy as np
from mpl_toolkits.mplot3d import Axes3D

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


# 基于 pyvista 的可视化方法，对 vtk 文件兼容性更好
def visualization_pyvista(vessel_net, path=None):
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

